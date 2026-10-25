# Resume entry (edit to match what you really built)
**AI CareerPilot, Resume Analysis & Job Matching Platform** | React, FastAPI, MongoDB, JWT, Pytest
- Built a full-stack web app where users upload PDF resumes, get skills extracted by a rule-based dictionary (with alias normalisation and manual correction), and see match scores against sample jobs.
- Added optional LLM-written career advice (skills only, never resume text) with a rule-based fallback.
- Designed REST APIs with FastAPI: JWT authentication, bcrypt password hashing, per-user data isolation, and validated file uploads (type, size, corrupted/empty PDFs).
- Implemented a transparent skill-gap formula (matching vs missing skills) and an application tracker with status, notes, search, filter and sort.
- Wrote 94 automated Pytest tests (auth, rate limiting, skill extraction accuracy, protected routes, invalid input, file validation, matching, ownership) run on every push with GitHub Actions.
- Built a responsive, accessible React UI with loading, empty, success and error states.

# Interview questions (answer in your own words)
1. **Why FastAPI?** Fast, automatic validation with Pydantic, and automatic Swagger docs at /docs.
2. **Why MongoDB?** Flexible documents suit jobs/resumes with list fields like skills; no migrations while the schema evolves. (Trade-off: no joins, so I store job title/company inside each application.)
3. **How does React talk to FastAPI?** Axios sends REST requests; an interceptor adds the JWT in the Authorization header; FastAPI returns JSON; CORS allows the frontend origin.
4. **How is the password stored?** Hashed with bcrypt (salted, slow on purpose). Plain passwords are never stored or returned.
5. **How does JWT auth work?** Login returns a signed token with the user id and expiry. Each request sends it; a FastAPI dependency verifies it and loads the user, otherwise 401.
6. **Where do you store the token and what's the risk?** localStorage: simple but exposed to XSS. httpOnly cookies are safer but need CSRF protection.
7. **How do you stop user A editing user B's data?** Every query includes `user_id` of the logged-in user, so other users' records return 404.
8. **How does skill extraction work?** pypdf extracts text; regex word-boundary matching against a skill dictionary (so "Java" doesn't match "JavaScript"). It is not AI.
9. **Explain the match formula and its limits.** Matched ÷ required × 100. Ignores skill weight, experience and synonyms.
10. **What did you test?** Auth, protected routes, invalid inputs, bad files, matching combinations, and ownership. Tests use mongomock so no real DB is touched.
11. **Which status codes do you use?** 201 created, 204 deleted, 400/422 bad input, 401 unauthenticated, 404 not found, 409 duplicate, 413 file too large.
12. **How did you stop brute-force logins?** An in-memory limiter blocks an IP+email after 5 failed attempts in 15 minutes (HTTP 429 + Retry-After). Limitation: it lives in one process, so multiple servers would need Redis.
13. **Why does Excel in 'excel in teamwork' not count as a skill?** Each term can carry a 'not followed by' rule, and the single letter C only counts inside a skills list. It is still keyword matching, so I added a manual skill editor.
14. **How is the AI part designed?** Skill extraction is rule-based. Job-page advice calls an LLM only if an API key is set, sends only skill names (never resume text), and falls back to rule-based tips if the call fails.
15. **What would you improve?** httpOnly cookies, refresh tokens, OCR, weighted skills, real job feed, frontend tests, CI/CD.
