import pytest
from app.services.matching import calculate_match
from tests.conftest import RESUME_LINES, make_pdf_lines


@pytest.mark.parametrize("resume,job,percent", [
    (["Python", "SQL"], ["Python", "SQL"], 100.0),
    (["Python"], ["Python", "SQL"], 50.0),
    ([], ["Python", "SQL"], 0.0),
    (["python"], ["Python"], 100.0),            # case-insensitive
    (["Python", "Java"], ["Python"], 100.0),    # extra skills never hurt
    (["Python"], [], 0.0),                      # job with no skills
])
def test_match_percent(resume, job, percent):
    assert calculate_match(resume, job)["percent"] == percent


def test_matching_and_missing_lists():
    r = calculate_match(["Python"], ["Python", "Docker"])
    assert r["matching"] == ["Python"] and r["missing"] == ["Docker"]


def test_jobs_endpoint_shows_match_and_filters(client, headers):
    client.post("/resume", headers=headers, files={"file": ("cv.pdf", make_pdf_lines(RESUME_LINES), "application/pdf")})
    data = client.get("/jobs", headers=headers).json()
    assert data["has_resume"] and "match" in data["jobs"][0]
    percents = [j["match"]["percent"] for j in data["jobs"]]
    assert percents == sorted(percents, reverse=True)
    assert all(j["role"] == "Data" for j in client.get("/jobs?role=Data", headers=headers).json()["jobs"])
    assert all("mangaluru" in j["location"].lower() for j in client.get("/jobs?location=mangal", headers=headers).json()["jobs"])
    assert all(j["experience"] == "Fresher" for j in client.get("/jobs?experience=Fresher", headers=headers).json()["jobs"])


def test_jobs_without_resume_has_no_match(client, headers):
    data = client.get("/jobs", headers=headers).json()
    assert not data["has_resume"] and "match" not in data["jobs"][0]


def test_job_detail_not_found(client, headers):
    assert client.get("/jobs/notanid", headers=headers).status_code == 404
