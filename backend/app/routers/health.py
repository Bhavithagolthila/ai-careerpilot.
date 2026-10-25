from fastapi import APIRouter, Depends
from app.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db=Depends(get_db)):
    try:
        db.command("ping")
        database = "connected"
    except Exception:
        database = "unreachable"
    return {"status": "ok", "database": database}
