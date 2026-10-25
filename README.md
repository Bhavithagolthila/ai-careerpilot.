# AI CareerPilot

A web app where you upload your resume (PDF), see the skills found in it, and see how well you match sample jobs. You can also save jobs and track them.

**Tech:** React + Vite · FastAPI (Python) · MongoDB · JWT login · Pytest

## What it does

1. **Sign up and log in.** Passwords are hashed with bcrypt, and login uses a JWT token.
2. **Upload a resume (PDF).** The app checks that the file is a real PDF and looks like a resume.
3. **See your skills.** Skills are found by matching words against a skill list. You can add or remove skills by hand.
4. **See job matches.** Each job shows a match percentage, the skills you have and the skills you are missing.
5. **Save jobs and track them.** Saving a job does not mean you applied. Status and notes are optional.
6. **Get tips.** Simple rule-based advice on which skills to learn next.

## Please note

- The 10 jobs are **sample jobs for demonstration**. They are not real vacancies.
- Skill detection is **keyword matching**, not AI.
- Match % = (job skills you have ÷ total job skills) × 100. It is **not** a chance of getting hired.

## How to run it (Windows)

**You need:** Python 3.10+, Node.js (LTS) and MongoDB running on your computer.

**Terminal 1: backend**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Open `backend\.env` and put a long random text after `JWT_SECRET=`. You can make one with:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Then start the server:
```powershell
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

**Terminal 2: frontend**
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```
Open http://localhost:5173

**Run the tests**
```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest
```

**To stop:** press Ctrl+C in each terminal.

## Common problems

| Problem | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and answer `Y` |
| "Cannot reach the server" | Start the backend (Terminal 1) |
| `/health` says `database: unreachable` | Start MongoDB |
| `Too many failed attempts` | Wait 15 minutes, or restart the backend |

## Project structure

```
backend/    FastAPI server (routers, services, tests)
frontend/   React app (pages, components)
docs/       Notes
```

## Limitations

- Only skills in the skill list are found. Scanned PDFs are not supported.
- Jobs are sample data, not a live job feed.
- The login token is stored in the browser's `localStorage`.
- No password reset or email verification.

## Optional: AI tips

If you add `ANTHROPIC_API_KEY` in `backend\.env`, the "Get tips" button uses an AI model. Only skill names are sent, never your resume text. Without a key it uses free rule-based tips.