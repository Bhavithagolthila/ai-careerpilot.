from unittest.mock import patch
from app.config import settings
from app.services.advice import generate_advice, rule_based_advice
from tests.conftest import RESUME_LINES, login_headers, make_pdf_lines

REG = {"name": "Asha", "email": "rl@example.com", "password": "password123"}


def bad_login(client, n=1, email=REG["email"]):
    return [client.post("/auth/login", data={"username": email, "password": "wrongpass1"}).status_code for _ in range(n)]


def test_login_blocked_after_too_many_failures(client):
    client.post("/auth/register", json=REG)
    codes = bad_login(client, settings.login_max_attempts)
    assert set(codes) == {401}
    res = client.post("/auth/login", data={"username": REG["email"], "password": "wrongpass1"})
    assert res.status_code == 429 and "Retry-After" in res.headers
    # even the correct password is refused while blocked
    assert client.post("/auth/login", data={"username": REG["email"], "password": REG["password"]}).status_code == 429


def test_successful_login_resets_counter(client):
    client.post("/auth/register", json=REG)
    bad_login(client, settings.login_max_attempts - 1)
    assert client.post("/auth/login", data={"username": REG["email"], "password": REG["password"]}).status_code == 200
    assert set(bad_login(client, settings.login_max_attempts - 1)) == {401}


def test_limit_is_per_email(client):
    client.post("/auth/register", json=REG)
    bad_login(client, settings.login_max_attempts)
    assert bad_login(client, 1, email="other@example.com") == [401]


def test_jobs_pagination(client, headers):
    data = client.get("/jobs?limit=3", headers=headers).json()
    assert data["total"] == 10 and len(data["jobs"]) == 3
    assert len(client.get("/jobs?limit=3&skip=9", headers=headers).json()["jobs"]) == 1
    assert client.get("/jobs?limit=0", headers=headers).status_code == 422
    assert client.get("/jobs?limit=101", headers=headers).status_code == 422


def _job_id(client, headers):
    return client.get("/jobs", headers=headers).json()["jobs"][0]["id"]


def test_advice_requires_resume(client, headers):
    assert client.post(f"/jobs/{_job_id(client, headers)}/advice", headers=headers).status_code == 409


def test_advice_rule_based_and_ownership_safe(client, headers):
    client.post("/resume", headers=headers, files={"file": ("r.pdf", make_pdf_lines(RESUME_LINES), "application/pdf")})
    res = client.post(f"/jobs/{_job_id(client, headers)}/advice", headers=headers)
    assert res.status_code == 200 and res.json()["source"] == "rules" and res.json()["tips"]
    assert client.post("/jobs/not-an-id/advice", headers=headers).status_code == 404
    assert client.post("/jobs/abc/advice").status_code == 401


JOB = {"title": "X", "experience": "Fresher", "skills": ["Python", "Docker"]}
MATCH = {"percent": 50.0, "matching": ["Python"], "missing": ["Docker"]}


def test_llm_used_when_key_set(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    with patch("app.services.advice.httpx.post") as post:
        post.return_value.json.return_value = {"content": [{"text": "- Learn Docker\n- Build a project"}]}
        out = generate_advice(JOB, MATCH, ["Python"])
    assert out == {"source": "ai", "tips": ["Learn Docker", "Build a project"]}


def test_llm_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    with patch("app.services.advice.httpx.post", side_effect=RuntimeError("down")):
        out = generate_advice(JOB, MATCH, ["Python"])
    assert out["source"] == "rules" and out["tips"]


def test_rule_advice_when_nothing_missing():
    tips = rule_based_advice(JOB, {"percent": 100.0, "matching": ["Python", "Docker"], "missing": []})
    assert len(tips) == 1
