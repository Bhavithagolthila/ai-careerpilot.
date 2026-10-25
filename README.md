# AI CareerPilot

Upload your resume as a PDF, see the skills found in it, compare them with job requirements, save jobs, and optionally track your applications.

![CI](https://github.com/Bhavithagolthila/ai-careerpilot/actions/workflows/ci.yml/badge.svg)

**Live demo:** _add your link here after deploying_

**Stack:** React + Vite · FastAPI · MongoDB (PyMongo) · JWT + bcrypt · pypdf · Pytest

## Screenshots

| Resume and skills | Job match | Tracker |
|---|---|---|
| ![Resume](docs/screenshots/resume.png) | ![Job](docs/screenshots/job.png) | ![Tracker](docs/screenshots/tracker.png) |

## Features

- **Accounts:** register and login with bcrypt-hashed passwords and JWT tokens. Failed logins are rate limited (5 attempts per 15 minutes).
- **Resume upload:** PDF only, max 2 MB and 10 pages. The server checks the real file signature, not the file name. It rejects empty, corrupted, password-protected, scanned and non-resume files (such as bills). Files are processed in memory and never saved.
- **Skill detection:** keyword matching against a skill dictionary. It handles equivalent spellings (`ReactJS` = `React`) and avoids common false positives ("excel in teamwork" is not the Excel skill).
- **Skill correction:** you can tick or untick detected skills by hand, and reset to the detected list.
- **Job matching:** match percentage, matching skills and missing skills for each job, with filters (text, location, role, experience).
- **Saved jobs and tracking:** saving a job does not claim you applied. Status (Saved, Applied, Interview, Rejected, Offer) and notes are optional. Each user can only see and change their own records.
- **Skill-gap tips:** free rule-based tips, or AI-written tips if you add an optional API key.
- **Responsive UI** with loading, empty, success and error states.

## Honest notes

- The 10 jobs are **made-up sample data for demonstration**, labelled "Demo" in the app. There are no real vacancies, salaries or application links.
- Skill detection is **rule-based, not AI**. The optional AI part only writes advice from skill names; resume text is never sent anywhere.
- The match percentage is `(job skills found in your skills ÷ total job skills) × 100`, with every skill weighted equally. It compares keywords only. It is **not** a prediction of being hired.

## How it works

```
React (5173) --Axios/REST--> FastAPI (8000) --PyMongo--> MongoDB
                               ├─ routers/   auth, resume, jobs, applications, health
                               ├─ services/  resume.py (skills), resume_validation.py,
                               │             matching.py (formula), advice.py (tips)
                               └─ security.py / deps.py / ratelimit.py
```

Resume upload goes through two stages: (1) file checks (size, real type, pages, encryption, readable text), then (2) a documented point score for resume-like structure (section headings, contact details, dates, skills).

## Run it locally (Windows PowerShell)

**You need:** Python 3.10+, Node.js 18+ (LTS) and MongoDB Community Server running as a service on `localhost:27017`.

**Terminal 1: backend**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Open `backend\.env` and set `JWT_SECRET` to a long random value:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Then start the API:
```powershell
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs · health check: http://localhost:8000/health

**Terminal 2: frontend**
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```
Open http://localhost:5173

**Tests** (they use an in-memory fake MongoDB, so no real data is touched)
```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest
```
94 tests cover auth, rate limiting, protected routes, resume validation, skill extraction, matching, skill correction, saved jobs, ownership and database-outage handling.

**Troubleshooting**
| Problem | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y` |
| "Cannot reach the server" in the browser | The backend terminal is not running |
| `/health` shows `"database": "unreachable"` | Start MongoDB (`Start-Service MongoDB` as Administrator) |
| `Too many failed attempts` | Wait 15 minutes or restart the backend |
| Port already in use | `netstat -ano \| findstr :8000`, then `taskkill /PID <pid> /F` |

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | API and database status |
| POST | `/auth/register`, `/auth/login` | no | Create account / get JWT |
| GET | `/auth/me` | yes | Current user |
| POST, GET | `/resume` | yes | Upload PDF / get analysis |
| PUT | `/resume/skills` | yes | Correct your skill list |
| GET | `/jobs` | yes | Search jobs (filters, paging, match %) |
| GET | `/jobs/{id}` | yes | Job with matching and missing skills |
| POST | `/jobs/{id}/advice` | yes | Skill-gap tips |
| POST, GET | `/applications` | yes | Save a job / list saved jobs |
| PATCH, DELETE | `/applications/{id}` | yes | Update status or notes / remove |

## Security

- Passwords are hashed with bcrypt, and password hashes are never returned.
- Secrets live in `.env`, which is git-ignored. In production the app refuses to start with a weak `JWT_SECRET`.
- Every query for private data filters by the logged-in user's ID.
- Inputs are validated with Pydantic. Search text is escaped before it reaches a database regex.
- Database outages return a clear 503 error instead of a stack trace.

## Limitations and future work

- Skills outside the dictionary are not detected (use "Edit skills" for listed ones). There is no OCR, so scanned PDFs are rejected.
- The match score ignores skill importance, experience and context.
- The JWT is stored in `localStorage`. A production app should use httpOnly cookies and refresh tokens.
- Login rate limiting is in memory (one process). Multiple servers would need Redis. There is no email verification or password reset.
- Jobs are sample data. Next steps: a real job feed, weighted skills, frontend tests.

## Optional: AI tips

Without a key, "Get tips" works for free with rule-based advice. If you set `ANTHROPIC_API_KEY` in `backend/.env`, the same button asks an LLM. Only skill names and the job's title and skills are sent, and if the call fails the app falls back to rule-based tips. A key may cost money on your account.