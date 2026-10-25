import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database import get_db
from app.deps import get_current_user
from app.services.resume import SKILL_NAMES, extract_skills, normalize_skill
from app.services.resume_validation import (
    MAX_BYTES, UNRELATED, UploadRejected, check_file, classify_resume_text, extract_pdf_text)

router = APIRouter(prefix="/resume", tags=["Resume"])
log = logging.getLogger("careerpilot.resume")


def safe_display_name(name: str | None) -> str:
    """Filename is only a display label (the file itself is never saved). Strip paths/control chars."""
    base = os.path.basename((name or "resume.pdf").replace("\\", "/"))
    return re.sub(r"[^\w .()-]", "_", base)[:100] or "resume.pdf"


def out(doc):
    detected = doc.get("detected_skills", doc["skills"])
    return {"filename": doc["filename"], "skills": doc["skills"], "detected_skills": detected,
            "skills_edited": sorted(doc["skills"]) != sorted(detected), "available_skills": SKILL_NAMES,
            "characters": doc["characters"],
            "analyzed_at": doc["analyzed_at"].isoformat(),
            "validation": doc.get("validation", {"status": "unknown", "message": ""})}


@router.post("")
def upload_resume(file: UploadFile = File(...), user=Depends(get_current_user), db=Depends(get_db)):
    """Validate (Stage A file checks, Stage B resume-content checks) and analyze a PDF resume.

    Responses: 200 valid or possible resume (see `validation.status`); 400 empty; 413 too large;
    415 unsupported file type; 422 unreadable / too few words / not a resume.
    """
    try:
        data = file.file.read(MAX_BYTES + 1)
        check_file(data)
        text, pages = extract_pdf_text(data)
        assessment = classify_resume_text(text)
    except UploadRejected as e:
        log.info("resume rejected code=%s", e.code)  # never log file contents
        raise HTTPException(e.status_code, e.message)
    if assessment.status == UNRELATED:
        log.info("resume rejected code=%s score=%s", UNRELATED, assessment.score)
        raise HTTPException(422, assessment.message)
    skills = extract_skills(text)
    doc = {"user_id": user["_id"], "filename": safe_display_name(file.filename), "skills": skills, "detected_skills": skills,
           "characters": len(text), "pages": pages, "analyzed_at": datetime.now(timezone.utc),
           "validation": {"status": assessment.status, "message": assessment.message,
                          "sections_found": assessment.signals["sections_found"]}}
    db.resumes.update_one({"user_id": user["_id"]}, {"$set": doc}, upsert=True)
    log.info("resume accepted status=%s pages=%s", assessment.status, pages)
    return out(doc)


@router.get("")
def get_resume(user=Depends(get_current_user), db=Depends(get_db)):
    doc = db.resumes.find_one({"user_id": user["_id"]})
    if not doc:
        raise HTTPException(404, "No resume uploaded yet")
    return out(doc)


class SkillsIn(BaseModel):
    skills: list[str] = Field(max_length=len(SKILL_NAMES))


@router.put("/skills")
def correct_skills(data: SkillsIn, user=Depends(get_current_user), db=Depends(get_db)):
    """Let the user fix the detected skills. Only skills from the known list are accepted, so they
    always line up with the skills jobs ask for. Equivalent spellings are normalised (reactjs -> React)."""
    doc = db.resumes.find_one({"user_id": user["_id"]})
    if not doc:
        raise HTTPException(404, "No resume uploaded yet")
    cleaned = sorted({normalize_skill(s) for s in data.skills if s.strip()})
    unknown = [s for s in cleaned if s not in SKILL_NAMES]
    if unknown:
        raise HTTPException(422, "Unknown skill(s): " + ", ".join(unknown[:5]))
    db.resumes.update_one({"user_id": user["_id"]}, {"$set": {"skills": cleaned}})
    return out(db.resumes.find_one({"user_id": user["_id"]}))
