import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from app.config import settings

log = logging.getLogger("careerpilot.db")
client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
_ready = False


def ensure_setup(db) -> None:
    """One-time setup: unique indexes + sample jobs. Safe to call repeatedly; it only works once."""
    global _ready
    if _ready:
        return
    from app.routers.jobs import seed_jobs  # imported here to avoid a circular import
    db.users.create_index("email", unique=True)
    db.resumes.create_index("user_id", unique=True)
    seed_jobs(db)
    _ready = True
    log.info("Database setup complete")


def get_db():
    """FastAPI dependency. Tests replace this with an in-memory database.

    If MongoDB was not running when the server started, setup is retried here, so starting MongoDB
    later just works without restarting the backend."""
    db = client[settings.db_name]
    if not _ready:
        try:
            ensure_setup(db)
        except PyMongoError:
            pass  # the request itself will report the database problem
    return db
