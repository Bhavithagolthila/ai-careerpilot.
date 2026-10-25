"""Career advice for one job: optional LLM, with a rule-based fallback that always works.

Privacy: only skill names and the job's title/skills are sent to the LLM. The resume text is
never stored by this app, so it is never sent.
"""
import logging

import httpx

from app.config import settings

log = logging.getLogger("careerpilot.advice")
API_URL = "https://api.anthropic.com/v1/messages"


def rule_based_advice(job: dict, match: dict) -> list[str]:
    pct, missing = match["percent"], match["missing"]
    if not missing:
        return [f"You already list every skill for {job['title']}. Tailor your resume to this role and prepare project stories for each skill."]
    tips = [f"You match {pct}% of {job['title']} ({len(match['matching'])} of {len(job['skills'])} skills)."]
    tips.append("Focus first on: " + ", ".join(missing[:3]) + ".")
    tips.append("Build one small project that uses " + (missing[0] if len(missing) == 1 else f"{missing[0]} and {missing[1]}")
                + ", put it on GitHub and add it to your Projects section.")
    if pct >= 70:
        tips.append("You are close. Apply now and learn the remaining skills while you apply.")
    elif pct < 40:
        tips.append("This is a stretch role today. Consider a more entry-level role while you learn these skills.")
    return tips


def _llm_advice(job: dict, match: dict, resume_skills: list[str]) -> list[str]:
    prompt = (
        f"Job: {job['title']} ({job['experience']}). Required skills: {', '.join(job['skills'])}.\n"
        f"Candidate skills: {', '.join(resume_skills) or 'none detected'}.\n"
        f"Missing: {', '.join(match['missing']) or 'none'}.\n"
        "Give 3 to 5 short, concrete, practical tips (one line each) to improve this candidate's chances. "
        "Output one tip per line, no numbering, no preamble.")
    res = httpx.post(
        API_URL, timeout=20,
        headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"},
        json={"model": settings.anthropic_model, "max_tokens": 400,
              "messages": [{"role": "user", "content": prompt}]})
    res.raise_for_status()
    text = "".join(b.get("text", "") for b in res.json().get("content", []))
    tips = [ln.strip("-•* \t") for ln in text.splitlines() if ln.strip()]
    if not tips:
        raise ValueError("empty LLM response")
    return tips[:5]


def generate_advice(job: dict, match: dict, resume_skills: list[str]) -> dict:
    if settings.anthropic_api_key:
        try:
            return {"source": "ai", "tips": _llm_advice(job, match, resume_skills)}
        except Exception as e:  # never let an AI outage break the feature
            log.warning("LLM advice failed, using rules: %s", type(e).__name__)
    return {"source": "rules", "tips": rule_based_advice(job, match)}
