"""Resume upload validation pipeline.

Stage A (file validation):  is this a safe, readable PDF within our limits?
Stage B (content validation): does the extracted text plausibly look like a resume?

What this can and cannot do: it checks FORMAT and resume-LIKE STRUCTURE only. It cannot tell
whether a resume is authentic or truthful. Classification is a transparent point score
(see classify_resume_text) so every decision can be explained and tested.

Privacy: nothing is written to disk (the upload is processed in memory) and only counts of
signals are returned/logged, never document text.
"""
import io
import re
from dataclasses import dataclass, field

from pypdf import PdfReader

from app.services.resume import extract_skills

MAX_BYTES = 2 * 1024 * 1024
MAX_PAGES = 10
MAX_TEXT_CHARS = 100_000
MIN_WORDS = 40

# Outcome codes (the API returns these so the frontend can react to them).
VALID = "valid"
POSSIBLE = "possible"
UNRELATED = "unrelated"
UNSUPPORTED = "unsupported_format"
UNREADABLE = "unreadable"
INSUFFICIENT = "insufficient_text"
TOO_LARGE = "too_large"
EMPTY = "empty"
TOO_MANY_PAGES = "too_many_pages"


class UploadRejected(Exception):
    """Raised when an upload must be refused. Carries an HTTP status and a user-facing message."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code, self.code, self.message = status_code, code, message


# ---------------------------------------------------------------- Stage A: file validation
_IMAGE_SIGNATURES = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8")
_MSG_UNSUPPORTED = "This file type is not supported. Please upload your resume as a PDF."


def check_file(data: bytes) -> None:
    """Check size and real file signature (never the filename or the client's MIME type)."""
    if not data:
        raise UploadRejected(400, EMPTY, "The file is empty. Please upload your resume as a PDF.")
    if len(data) > MAX_BYTES:
        raise UploadRejected(413, TOO_LARGE, f"File is too large (max {MAX_BYTES // (1024 * 1024)} MB).")
    if b"%PDF-" in data[:1024]:
        return
    if data.startswith(_IMAGE_SIGNATURES) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        raise UploadRejected(415, UNSUPPORTED, "Images are not supported. Please upload your resume as a PDF.")
    if data.startswith(b"PK\x03\x04") or data.startswith(b"\xd0\xcf\x11\xe0"):
        raise UploadRejected(415, UNSUPPORTED, "Word documents are not supported yet. Please export your resume as a PDF.")
    raise UploadRejected(415, UNSUPPORTED, "This file is not a real PDF, whatever its name says. " + _MSG_UNSUPPORTED)


def extract_pdf_text(data: bytes) -> tuple[str, int]:
    """Return (text, page_count). Raises UploadRejected for unreadable/encrypted/too long/empty PDFs."""
    unreadable = UploadRejected(422, UNREADABLE, "We could not read this file. Please upload a valid PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise UploadRejected(422, UNREADABLE, "This PDF is password protected. Please upload an unprotected PDF.")
        pages = len(reader.pages)
        if pages > MAX_PAGES:
            raise UploadRejected(422, TOO_MANY_PAGES, f"This PDF has {pages} pages. Resumes of up to {MAX_PAGES} pages are supported.")
        parts, total = [], 0
        for page in reader.pages:
            chunk = page.extract_text() or ""
            parts.append(chunk)
            total += len(chunk)
            if total > MAX_TEXT_CHARS:  # cap work on huge/abusive documents
                break
    except UploadRejected:
        raise
    except Exception:  # pypdf raises many different errors on malformed input
        raise unreadable from None
    text = "\n".join(parts)[:MAX_TEXT_CHARS]
    if len(text.split()) < MIN_WORDS:
        raise UploadRejected(
            422, INSUFFICIENT,
            "The document contains too little readable text. Try a clearer or text-based PDF "
            "(scanned or image-only PDFs are not supported yet).")
    return text, pages


# ---------------------------------------------------------------- Stage B: content validation
_HEADINGS = {
    "education": r"^(education|academic (background|qualifications?)|qualifications?)\b",
    "experience": r"^((work|professional) )?(experience|employment( history)?)\b|^internships?\b",
    "skills": r"^((technical|key|core) )?skills\b|^technologies\b",
    "projects": r"^((academic|personal|key) )?projects?\b",
    "summary": r"^((professional|career) )?(summary|objective|profile)\b|^about me\b",
    "extras": r"^(certifications?|achievements?|awards?|publications?)\b",
}
_HEADING_RX = {k: re.compile(v) for k, v in _HEADINGS.items()}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?\d{5}[\s-]?\d{5}(?!\d)|(?<!\d)\d{3}[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
_PROFILE_URL = re.compile(r"(linkedin\.com|github\.com)", re.I)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# Words typical of bills/invoices/receipts: strong evidence the document is something else.
_NON_RESUME = re.compile(
    r"\b(kwh|units consumed|amount due|total payable|meter reading|invoice|due date|bill (?:no|number|date)|"
    r"consumer (?:no|number)|account (?:no|number)|gstin|tariff|subtotal|receipt)\b", re.I)


@dataclass
class Assessment:
    status: str
    score: float
    message: str
    signals: dict = field(default_factory=dict)


def classify_resume_text(text: str) -> Assessment:
    """Score resume-like evidence. Documented point system (max about 9.5):

    +1.5 per distinct resume section heading (education, experience, skills, projects, summary,
         certifications), counting at most 4 sections
    +1   per contact signal (email, phone, LinkedIn/GitHub link), counting at most 2
    +1   two or more year-like dates      +1   three or more known skills      +0.5  150+ words

    VALID    score >= 5 and at least 2 section headings   (fresher resumes without a
             work-experience section can still pass)
    POSSIBLE score >= 3   (some evidence, not enough to be sure; accepted with a warning)
    UNRELATED otherwise, or bill/invoice-style wording with fewer than 3 resume headings.
    A single keyword such as "skills" can never be enough on its own.
    """
    lines = [ln.strip().lower() for ln in text.splitlines()]
    headings = sorted(k for k, rx in _HEADING_RX.items() if any(rx.match(ln) for ln in lines))
    contact = sum(bool(x) for x in (_EMAIL.search(text), _PHONE.search(text), _PROFILE_URL.search(text)))
    years = len(_YEAR.findall(text))
    skills = len(extract_skills(text))
    words = len(text.split())
    non_resume = len({m.lower() for m in _NON_RESUME.findall(text)})

    score = (1.5 * min(len(headings), 4) + min(contact, 2) + (1 if years >= 2 else 0)
             + (1 if skills >= 3 else 0) + (0.5 if words >= 150 else 0))
    signals = {"sections_found": headings, "contact_signals": contact, "year_mentions": years,
               "known_skills": skills, "words": words, "non_resume_terms": non_resume, "score": score}

    if non_resume >= 2 and len(headings) < 3:
        return Assessment(UNRELATED, score, "This document does not appear to be a resume (it looks more like a bill or invoice). "
                          "Please upload your resume in a supported format.", signals)
    if score >= 5 and len(headings) >= 2:
        return Assessment(VALID, score, "This looks like a resume.", signals)
    if score >= 3:
        return Assessment(POSSIBLE, score, "This might be a resume, but we found limited evidence "
                          "(for example few standard sections such as Education, Projects or Skills). "
                          "Results may be incomplete. Check the extracted skills.", signals)
    return Assessment(UNRELATED, score, "This document does not appear to be a resume. "
                      "Please upload your resume in a supported format.", signals)
