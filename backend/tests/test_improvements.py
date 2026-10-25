"""Tests for skill extraction accuracy, skill corrections, saved jobs, demo labels and error handling."""
import pytest
from pymongo.errors import ServerSelectionTimeoutError

from app.config import Settings
from app.database import get_db
from app.main import app
from app.security import create_access_token, decode_token
from app.services.matching import calculate_match
from app.services.resume import extract_skills, normalize_skill
from tests.conftest import RESUME_LINES, make_pdf_lines


# ---- skill extraction: fewer false positives / negatives, equivalent names
@pytest.mark.parametrize("text,expected", [
    ("Built apps with ReactJS and Node JS", {"React", "Node.js"}),
    ("Used mongo db and Postgres daily", {"MongoDB", "PostgreSQL"}),
    ("Designed RESTful APIs", {"REST API"}),
    ("Languages: C, C++, Python", {"C", "C++", "Python"}),
    ("C/C++ and Java", {"C", "C++", "Java"}),
    ("Advanced Excel, Power BI", {"Excel", "Power BI"}),
])
def test_extracts_equivalent_spellings(text, expected):
    assert expected <= set(extract_skills(text))


@pytest.mark.parametrize("text,not_expected", [
    ("I excel in teamwork and communication", "Excel"),
    ("I excel at solving problems", "Excel"),
    ("Able to react to feedback quickly", "React"),
    ("JavaScript developer", "Java"),                # Java must not match JavaScript
    ("Used GitHub for code reviews", "Git"),          # Git must not match GitHub
    ("Worked with NoSQL stores", "SQL"),
    ("Grade C in school", "C"),                       # a lone C outside a skills list is not a skill
])
def test_avoids_false_positives(text, not_expected):
    assert not_expected not in extract_skills(text)


def test_normalize_skill():
    assert normalize_skill("  reactjs ") == "React"
    assert normalize_skill("NODE JS") == "Node.js"
    assert normalize_skill("Underwater Basket Weaving") == "Underwater Basket Weaving"


# ---- matching
def test_match_treats_equivalent_names_as_same_skill():
    assert calculate_match(["ReactJS"], ["React"])["percent"] == 100.0


def test_match_counts_duplicate_job_skills_once():
    r = calculate_match(["Python"], ["Python", "python", "SQL"])
    assert r["percent"] == 50.0 and r["missing"] == ["SQL"]


# ---- skill corrections
def _upload(client, headers):
    return client.post("/resume", headers=headers, files={"file": ("cv.pdf", make_pdf_lines(RESUME_LINES), "application/pdf")})


def test_user_can_correct_skills_and_matching_uses_them(client, headers):
    first = _upload(client, headers).json()
    assert not first["skills_edited"] and "Docker" in first["available_skills"]
    res = client.put("/resume/skills", headers=headers, json={"skills": ["reactjs", "Docker", "Docker"]})
    assert res.status_code == 200 and res.json()["skills"] == ["Docker", "React"]
    assert res.json()["skills_edited"] and "Python" in res.json()["detected_skills"]
    assert client.get("/resume", headers=headers).json()["skills"] == ["Docker", "React"]
    # reset to what was detected
    res = client.put("/resume/skills", headers=headers, json={"skills": first["detected_skills"]})
    assert not res.json()["skills_edited"]


def test_skill_correction_validation(client, headers):
    assert client.put("/resume/skills", headers=headers, json={"skills": ["Python"]}).status_code == 404  # no resume yet
    _upload(client, headers)
    assert client.put("/resume/skills", headers=headers, json={"skills": ["Not A Skill"]}).status_code == 422
    assert client.put("/resume/skills", headers=headers, json={"skills": "Python"}).status_code == 422
    assert client.put("/resume/skills", json={"skills": []}).status_code == 401


def test_skill_correction_is_per_user(client, headers):
    _upload(client, headers)
    other = login_other(client)
    assert client.get("/resume", headers=other).status_code == 404
    assert client.put("/resume/skills", headers=other, json={"skills": ["Python"]}).status_code == 404


def login_other(client):
    from tests.conftest import login_headers
    return login_headers(client, email="b@example.com")


# ---- demo labels + saved flag
def test_seeded_jobs_are_labelled_demo(client, headers):
    jobs = client.get("/jobs", headers=headers).json()["jobs"]
    assert jobs and all(j["is_demo"] for j in jobs)


def test_saved_flag_and_save_does_not_claim_applied(client, headers):
    job = client.get("/jobs", headers=headers).json()["jobs"][0]
    assert job["saved"] is False
    res = client.post("/applications", headers=headers, json={"job_id": job["id"]})
    assert res.status_code == 201 and res.json()["status"] == "Saved" and res.json()["applied_date"] is None
    assert client.get(f"/jobs/{job['id']}", headers=headers).json()["saved"] is True
    assert next(j for j in client.get("/jobs", headers=headers).json()["jobs"] if j["id"] == job["id"])["saved"]
    # another user has not saved it
    assert client.get(f"/jobs/{job['id']}", headers=login_other(client)).json()["saved"] is False


def test_moving_back_to_saved_clears_applied_date(client, headers):
    job = client.get("/jobs", headers=headers).json()["jobs"][0]
    app_id = client.post("/applications", headers=headers, json={"job_id": job["id"], "status": "Applied"}).json()["id"]
    assert client.get("/applications", headers=headers).json()[0]["applied_date"]
    res = client.patch(f"/applications/{app_id}", headers=headers, json={"status": "Saved"})
    assert res.json()["status"] == "Saved" and res.json()["applied_date"] is None


# ---- error handling and configuration
class BrokenDB:
    def __getattr__(self, name):
        raise ServerSelectionTimeoutError("mongo is down")


def test_database_outage_returns_clear_503(client):
    app.dependency_overrides[get_db] = lambda: BrokenDB()
    res = client.post("/auth/login", data={"username": "a@example.com", "password": "password123"})
    assert res.status_code == 503 and "database is unavailable" in res.json()["detail"]
    assert "Traceback" not in res.text


def test_token_without_sub_is_rejected(client, monkeypatch):
    import jwt
    from app.config import settings
    token = jwt.encode({"exp": 9999999999}, settings.jwt_secret, algorithm="HS256")
    assert decode_token(token) is None
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert decode_token(create_access_token("abc")) == "abc"


def test_cors_origins_in_dev_and_production():
    dev = Settings(frontend_origin="http://localhost:5173", environment="development").cors_origins
    assert "http://localhost:5173" in dev and "http://127.0.0.1:5173" in dev
    prod = Settings(frontend_origin="https://a.example.com, https://b.example.com", environment="production",
                    jwt_secret="x" * 40).cors_origins
    assert prod == ["https://a.example.com", "https://b.example.com"]


def test_production_requires_real_secret():
    with pytest.raises(ValueError):
        Settings(environment="production", jwt_secret="short")


def test_unknown_keys_in_env_are_ignored(monkeypatch):
    monkeypatch.setenv("SOME_RANDOM_THING", "1")
    Settings()  # must not raise


def test_cors_header_for_127_0_0_1(client):
    res = client.options("/auth/login", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"})
    assert res.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_setup_is_retried_when_mongo_starts_late(monkeypatch):
    import mongomock
    from app import database
    fake = mongomock.MongoClient()
    monkeypatch.setattr(database, "client", fake)
    monkeypatch.setattr(database, "_ready", False)
    db = database.get_db()                      # first request after "Mongo came up"
    assert db.jobs.count_documents({}) == 10
    assert any(i.get("unique") for i in db.users.index_information().values())
    assert database._ready is True
