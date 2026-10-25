import mongomock
import pytest
from fastapi.testclient import TestClient
from app.database import get_db
from app.main import app
from app.routers.jobs import seed_jobs


def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offs:
        out += f"{off:010d} 00000 n \n".encode()
    return out + f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF".encode()


def make_pdf_lines(lines: list[str]) -> bytes:
    """Multi-line text PDF (one text line per entry). Synthetic data only."""
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    body = "BT /F1 11 Tf 14 TL 50 750 Td " + " ".join(f"({esc(ln)}) Tj T*" for ln in lines) + " ET"
    return make_pdf_raw(body.encode())


def make_pdf_raw(stream: bytes) -> bytes:
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offs:
        out += f"{off:010d} 00000 n \n".encode()
    return out + f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF".encode()


# ---- Synthetic documents (no real personal data) ----
RESUME_LINES = [
    "Asha Example", "asha.example@example.com | 98765 43210 | github.com/asha-example",
    "Summary", "Computer science fresher who enjoys building small web applications and learning backend development.",
    "Education", "B.E. Computer Science and Design Engineering, Example Institute of Technology, 2022 - 2026",
    "Projects", "Bill Tracker: a FastAPI and React application that stores monthly usage in PostgreSQL and shows charts.",
    "Portfolio Site: a responsive website built with HTML, CSS and JavaScript and deployed with GitHub pages.",
    "Skills", "Python, FastAPI, SQL, PostgreSQL, React, JavaScript, Git, GitHub, Pytest",
]
LIMITED_RESUME_LINES = [  # fresher, no experience section, only some sections
    "Ravi Example", "ravi.example@example.com", "Education", "Diploma in Computer Engineering 2021 - 2024",
    "Skills", "Python, SQL, Git, HTML, CSS and basic Linux usage with a lot of practice in small exercises and "
    "classroom assignments over three years of study at the example institute of technology",
]
BILL_LINES = [
    "Example Electricity Supply Company", "Electricity Bill", "Consumer Number 0000000000 Bill Date 05 Sep 2025",
    "Meter reading previous 1200 current 1445 Units consumed 245 kWh", "Energy charges and fixed charges are listed below",
    "Subtotal 1700.00 Tax 120.00 Total payable 1820.00 Due date 20 Sep 2025",
    "Please pay the amount before the due date to avoid a late payment surcharge on your next invoice",
]
RANDOM_LINES = [
    "How to bake a simple loaf of bread at home", "Mix two cups of flour with one cup of warm water and a little salt.",
    "Let the dough rest for an hour in a warm place until it doubles in size and feels soft and elastic to the touch.",
    "Bake in a hot oven for thirty minutes until the crust is golden brown, then cool on a wire rack before slicing.",
    "Serve with butter, jam or soup. Leftover bread can be toasted the next day or turned into crumbs.",
]


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    from app.config import settings
    from app.ratelimit import login_limiter
    monkeypatch.setattr(settings, "jwt_secret", "test-secret-" + "x" * 32)  # 32+ chars, no JWT warnings
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    login_limiter.reset()
    yield
    login_limiter.reset()


@pytest.fixture
def client():
    db = mongomock.MongoClient()["test"]
    seed_jobs(db)
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def login_headers(client, email="a@example.com", password="password123"):
    client.post("/auth/register", json={"name": "Test User", "email": email, "password": password})
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def headers(client):
    return login_headers(client)
