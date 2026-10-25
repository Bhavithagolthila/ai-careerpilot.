"""Upload validation: every kind of wrong file must get a clear message and must NOT be saved."""
import pytest
from app.services.resume_validation import (
    POSSIBLE, UNRELATED, VALID, UploadRejected, check_file, classify_resume_text, extract_pdf_text)
from tests.conftest import (
    BILL_LINES, LIMITED_RESUME_LINES, RANDOM_LINES, RESUME_LINES, make_pdf_lines, make_pdf_raw)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
DOCX = b"PK\x03\x04" + b"\x00" * 200
OLD_DOC = b"\xd0\xcf\x11\xe0" + b"\x00" * 200


def text_of(lines):
    return extract_pdf_text(make_pdf_lines(lines))[0]


# ---- Stage A (pure functions) ----
@pytest.mark.parametrize("data,status", [(b"", 400), (PNG, 415), (JPEG, 415), (DOCX, 415), (OLD_DOC, 415),
                                         (b"plain text renamed to pdf", 415), (b"%PDF-" + b"0" * (2 * 1024 * 1024), 413)])
def test_check_file_rejections(data, status):
    with pytest.raises(UploadRejected) as e:
        check_file(data)
    assert e.value.status_code == status


def test_check_file_accepts_pdf_signature():
    check_file(make_pdf_lines(RESUME_LINES))


def test_corrupted_pdf_is_unreadable_not_a_crash():
    with pytest.raises(UploadRejected) as e:
        extract_pdf_text(b"%PDF-1.4 garbage garbage")
    assert e.value.status_code == 422 and "valid PDF" in e.value.message


def test_pdf_with_no_text_is_insufficient():
    with pytest.raises(UploadRejected) as e:
        extract_pdf_text(make_pdf_raw(b"BT ET"))
    assert "too little readable text" in e.value.message


# ---- Stage B (classification) ----
def test_full_resume_is_valid():
    assert classify_resume_text(text_of(RESUME_LINES)).status == VALID


def test_fresher_resume_without_experience_section_is_valid():
    a = classify_resume_text(text_of(LIMITED_RESUME_LINES))
    assert a.status == VALID and "experience" not in a.signals["sections_found"]


def test_electricity_bill_is_unrelated():
    a = classify_resume_text(text_of(BILL_LINES))
    assert a.status == UNRELATED and "does not appear to be a resume" in a.message


def test_random_text_is_unrelated():
    assert classify_resume_text(text_of(RANDOM_LINES)).status == UNRELATED


def test_one_keyword_is_not_enough():
    lines = RANDOM_LINES + ["Skills", "Education"]
    assert classify_resume_text(text_of(lines)).status != VALID


def test_weak_evidence_is_reported_as_possible():
    # two headings (3 points) but no contact details, dates or skills: some evidence, not enough to be sure
    lines = ["Summary", "Someone writing about their career goals in general terms",
             "Education", "Studied several subjects at a university and enjoyed most of them"] + RANDOM_LINES
    assert classify_resume_text(text_of(lines)).status == POSSIBLE


def test_signals_contain_counts_not_document_text():
    sig = classify_resume_text(text_of(RESUME_LINES)).signals
    assert "asha" not in str(sig).lower()


# ---- Through the API: rejected uploads must not be stored ----
def post(client, headers, content, name="cv.pdf"):
    return client.post("/resume", headers=headers, files={"file": (name, content, "application/pdf")})


@pytest.mark.parametrize("content,status", [
    (PNG, 415), (JPEG, 415), (DOCX, 415), (make_pdf_lines(BILL_LINES), 422), (make_pdf_lines(RANDOM_LINES), 422),
    (b"just text", 415), (b"", 400), (b"%PDF-1.4 garbage", 422)])
def test_bad_uploads_rejected_and_not_saved(client, headers, content, status):
    res = post(client, headers, content)
    assert res.status_code == status and res.json()["detail"]
    assert client.get("/resume", headers=headers).status_code == 404


def test_limited_resume_accepted(client, headers):
    res = post(client, headers, make_pdf_lines(LIMITED_RESUME_LINES))
    assert res.status_code == 200 and "Python" in res.json()["skills"]


def test_path_traversal_filename_is_neutralised(client, headers):
    res = post(client, headers, make_pdf_lines(RESUME_LINES), name="../../etc/passwd<script>.pdf")
    assert res.status_code == 200
    name = res.json()["filename"]
    assert "/" not in name and "<" not in name and ".." not in name.replace("...", "")
