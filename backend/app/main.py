import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from app.config import DEFAULT_DEV_SECRET, settings
from app.database import ensure_setup, get_db
from app.routers import applications, auth, health, jobs, resume

log = logging.getLogger("careerpilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == DEFAULT_DEV_SECRET:
        log.warning("Using the default development JWT_SECRET. Set JWT_SECRET in backend/.env.")
    try:  # unique indexes + sample jobs (retried on later requests if MongoDB is not up yet)
        ensure_setup(get_db())
    except Exception as e:
        log.error("Database setup failed: %s", e)
        if settings.environment.lower() == "production":
            raise  # fail fast: do not run production with a broken database
    yield


app = FastAPI(title="AI CareerPilot API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(PyMongoError)
async def database_unavailable(request, exc):
    """Any MongoDB failure becomes a clear 503 instead of a stack trace."""
    log.error("Database error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "The database is unavailable right now. Please try again shortly."})


for r in (health, auth, resume, jobs, applications):
    app.include_router(r.router)
