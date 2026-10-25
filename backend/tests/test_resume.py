from tests.conftest import RESUME_LINES, make_pdf, make_pdf_lines


def upload(client, headers, content, name="cv.pdf", mime="application/pdf"):
    return client.post("/resume", headers=headers, files={"file": (name, content, mime)})


def test_extracts_skills(client, headers):
    res = upload(client, headers, make_pdf_lines(RESUME_LINES))
    assert res.status_code == 200
    body = res.json()
    for s in ("Python", "FastAPI", "PostgreSQL", "React", "GitHub", "Pytest"):
        assert s in body["skills"]
    assert "Java" not in body["skills"] and "MongoDB" not in body["skills"]
    assert body["validation"]["status"] == "valid"


def test_rejects_wrong_content_regardless_of_extension(client, headers):
    assert upload(client, headers, b"hello", "cv.txt").status_code == 415


def test_rejects_fake_pdf(client, headers):
    res = upload(client, headers, b"this is not a pdf")
    assert res.status_code == 415 and "not a real PDF" in res.json()["detail"]


def test_rejects_empty_file(client, headers):
    assert upload(client, headers, b"").status_code == 400


def test_rejects_oversized_file(client, headers):
    assert upload(client, headers, b"%PDF-" + b"0" * (2 * 1024 * 1024 + 10)).status_code == 413


def test_rejects_corrupted_pdf(client, headers):
    assert upload(client, headers, b"%PDF-1.4 garbage garbage").status_code == 422


def test_rejects_pdf_without_text(client, headers):
    res = upload(client, headers, make_pdf(""))
    assert res.status_code == 422 and "too little readable text" in res.json()["detail"]


def test_get_resume_before_and_after(client, headers):
    assert client.get("/resume", headers=headers).status_code == 404
    upload(client, headers, make_pdf_lines(RESUME_LINES))
    assert "Python" in client.get("/resume", headers=headers).json()["skills"]
