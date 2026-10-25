import re
from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import get_db
from app.deps import get_current_user, oid
from app.services.advice import generate_advice
from app.services.matching import calculate_match

router = APIRouter(prefix="/jobs", tags=["Jobs"])

SEED = [
    ("Junior Python Developer", "Backend", "TechNova", "Bengaluru", "Fresher", ["Python", "SQL", "Git", "REST API"], "Build and maintain Python services and APIs."),
    ("FastAPI Backend Engineer", "Backend", "CloudNest", "Remote", "Junior", ["Python", "FastAPI", "MongoDB", "Docker", "REST API", "Pytest"], "Design REST APIs with FastAPI and MongoDB."),
    ("React Frontend Developer", "Frontend", "PixelWorks", "Mangaluru", "Fresher", ["JavaScript", "React", "HTML", "CSS", "Git"], "Build responsive React interfaces."),
    ("Full Stack Developer", "Full Stack", "StackLabs", "Hyderabad", "Junior", ["JavaScript", "React", "Node.js", "MongoDB", "REST API", "Git"], "Work on both frontend and backend features."),
    ("Data Analyst Trainee", "Data", "InsightIQ", "Pune", "Fresher", ["Python", "SQL", "Excel", "Pandas", "Power BI"], "Clean data and build dashboards."),
    ("Associate Software Engineer", "Backend", "InfoCore", "Mysuru", "Fresher", ["Java", "SQL", "OOP", "DSA", "Git"], "Develop enterprise applications in Java."),
    ("Django Developer", "Backend", "WebForge", "Chennai", "Junior", ["Python", "Django", "PostgreSQL", "REST API", "Git", "Docker"], "Build web apps and APIs with Django."),
    ("Machine Learning Intern", "Data", "NeuralPath", "Remote", "Fresher", ["Python", "NumPy", "Pandas", "Machine Learning", "Jupyter"], "Assist with ML experiments and data prep."),
    ("DevOps Associate", "DevOps", "OpsPilot", "Bengaluru", "Junior", ["Linux", "Docker", "AWS", "Git", "Python"], "Maintain CI/CD pipelines and cloud setups."),
    ("Software Developer", "Full Stack", "CodeBridge", "Mangaluru", "Mid", ["Python", "React", "PostgreSQL", "Docker", "AWS", "REST API", "Agile"], "Own features end to end in an agile team."),
]


def seed_jobs(db):
    if db.jobs.count_documents({}) == 0:
        keys = ("title", "role", "company", "location", "experience", "skills", "description")
        # is_demo: these are made-up sample jobs for demonstration, not real vacancies.
        db.jobs.insert_many([{**dict(zip(keys, j)), "is_demo": True} for j in SEED])


def serialize(job, resume_skills=None, saved_ids=frozenset()):
    data = {k: job[k] for k in ("title", "role", "company", "location", "experience", "skills", "description")}
    data["id"] = str(job["_id"])
    data["is_demo"] = job.get("is_demo", True)  # jobs without the flag are treated as demo data
    data["saved"] = data["id"] in saved_ids
    if resume_skills is not None:
        data["match"] = calculate_match(resume_skills, job["skills"])
    return data


def saved_job_ids(db, user) -> set[str]:
    return {a["job_id"] for a in db.applications.find({"user_id": user["_id"]}, {"job_id": 1})}


def resume_skills_of(db, user):
    r = db.resumes.find_one({"user_id": user["_id"]})
    return r["skills"] if r else None


@router.get("")
def list_jobs(q: str = "", location: str = "", role: str = "", experience: str = "",
              limit: int = Query(50, ge=1, le=100), skip: int = Query(0, ge=0),
              user=Depends(get_current_user), db=Depends(get_db)):
    rx = lambda s: {"$regex": re.escape(s), "$options": "i"}
    query = {}
    if q:
        query["$or"] = [{"title": rx(q)}, {"company": rx(q)}, {"description": rx(q)}]
    if location:
        query["location"] = rx(location)
    if role:
        query["role"] = role
    if experience:
        query["experience"] = experience
    skills = resume_skills_of(db, user)
    saved = saved_job_ids(db, user)
    jobs = [serialize(j, skills, saved) for j in db.jobs.find(query)]
    if skills is not None:  # sort by match first, then page (sorting needs every match score)
        jobs.sort(key=lambda j: j["match"]["percent"], reverse=True)
    return {"has_resume": skills is not None, "total": len(jobs), "limit": limit, "skip": skip,
            "jobs": jobs[skip:skip + limit]}


@router.get("/{job_id}")
def job_detail(job_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    job = db.jobs.find_one({"_id": oid(job_id)})
    if not job:
        raise HTTPException(404, "Job not found")
    return serialize(job, resume_skills_of(db, user), saved_job_ids(db, user))


@router.post("/{job_id}/advice")
def job_advice(job_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    """Tips to close the skill gap for one job. Uses an LLM if ANTHROPIC_API_KEY is set, else rules."""
    skills = resume_skills_of(db, user)
    if skills is None:
        raise HTTPException(409, "Upload your resume first")
    job = db.jobs.find_one({"_id": oid(job_id)})
    if not job:
        raise HTTPException(404, "Job not found")
    return generate_advice(job, calculate_match(skills, job["skills"]), skills)
