from app.services.resume import normalize_skill


def calculate_match(resume_skills: list[str], job_skills: list[str]) -> dict:
    """match % = (job skills you have / total job skills) * 100. Every skill counts equally.

    Equivalent spellings are treated as the same skill (ReactJS = React). Duplicates in the job's
    list are counted once. This is a keyword overlap, NOT a chance of being hired.
    """
    have = {normalize_skill(s).lower() for s in resume_skills}
    seen, required = set(), []
    for s in job_skills:
        key = normalize_skill(s).lower()
        if key and key not in seen:
            seen.add(key)
            required.append((s, key))
    matching = [s for s, key in required if key in have]
    missing = [s for s, key in required if key not in have]
    percent = round(100 * len(matching) / len(required), 1) if required else 0.0
    return {"percent": percent, "matching": matching, "missing": missing}
