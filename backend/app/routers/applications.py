import re
from datetime import date, datetime, timezone
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.database import get_db
from app.deps import get_current_user, oid

router = APIRouter(prefix="/applications", tags=["Applications"])
Status = Literal["Saved", "Applied", "Interview", "Rejected", "Offer"]


class AppCreate(BaseModel):
    job_id: str
    status: Status = "Saved"
    notes: str = Field("", max_length=1000)
    applied_date: Optional[date] = None


class AppUpdate(BaseModel):
    status: Optional[Status] = None
    notes: Optional[str] = Field(None, max_length=1000)
    applied_date: Optional[date] = None


def out(a):
    return {"id": str(a["_id"]), "job_id": a["job_id"], "job_title": a["job_title"], "company": a["company"],
            "status": a["status"], "notes": a["notes"], "applied_date": a.get("applied_date"),
            "created_at": a["created_at"].isoformat()}


@router.post("", status_code=201)
def create(data: AppCreate, user=Depends(get_current_user), db=Depends(get_db)):
    job = db.jobs.find_one({"_id": oid(data.job_id)})
    if not job:
        raise HTTPException(404, "Job not found")
    if db.applications.find_one({"user_id": user["_id"], "job_id": data.job_id}):
        raise HTTPException(409, "You already saved this job")
    doc = {"user_id": user["_id"], "job_id": data.job_id, "job_title": job["title"], "company": job["company"],
           "status": data.status, "notes": data.notes,
           "applied_date": data.applied_date.isoformat() if data.applied_date else (date.today().isoformat() if data.status == "Applied" else None),
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = db.applications.insert_one(doc).inserted_id
    return out(doc)


@router.get("")
def list_apps(status: str = "", q: str = "", sort: Literal["newest", "oldest", "company"] = "newest",
              user=Depends(get_current_user), db=Depends(get_db)):
    query = {"user_id": user["_id"]}
    if status:
        query["status"] = status
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"job_title": rx}, {"company": rx}, {"notes": rx}]
    field, direction = {"newest": ("created_at", -1), "oldest": ("created_at", 1), "company": ("company", 1)}[sort]
    return [out(a) for a in db.applications.find(query).sort(field, direction)]


@router.patch("/{app_id}")
def update(app_id: str, data: AppUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    query = {"_id": oid(app_id), "user_id": user["_id"]}  # users can only touch their own records
    existing = db.applications.find_one(query)
    if not existing:
        raise HTTPException(404, "Application not found")
    changes = {k: v for k, v in data.model_dump().items() if v is not None}
    if "applied_date" in changes:
        changes["applied_date"] = changes["applied_date"].isoformat()
    if changes.get("status") == "Applied" and not changes.get("applied_date") and not existing.get("applied_date"):
        changes["applied_date"] = date.today().isoformat()
    if changes.get("status") == "Saved" and "applied_date" not in changes:
        changes["applied_date"] = None  # moving back to Saved: you have not applied
    if changes:
        db.applications.update_one(query, {"$set": changes})
    return out(db.applications.find_one(query))


@router.delete("/{app_id}", status_code=204)
def delete(app_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    if db.applications.delete_one({"_id": oid(app_id), "user_id": user["_id"]}).deleted_count == 0:
        raise HTTPException(404, "Application not found")
