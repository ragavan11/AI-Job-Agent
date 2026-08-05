import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import get_db, init_db
from app.routers import applications, cover_letters, jobs, profile, resumes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("job_agent")

settings = get_settings()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.enable_scheduler:
        scheduler.add_job(_scheduled_refresh, "interval", minutes=settings.auto_refresh_minutes, id="job_refresh")
        scheduler.start()
        logger.info("Scheduler started: refreshing every %s minutes", settings.auto_refresh_minutes)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Personal Job Agent",
    description="Phase 1: profile, real job aggregation, matching, AI resume/cover-letter generation.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # the Next.js dev/prod server only — not a public API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(cover_letters.router)
app.include_router(applications.router)


@app.get("/health")
def health():
    return {"status": "ok"}


async def _scheduled_refresh():
    """Runs jobs.refresh_jobs on a timer. Wrapped in try/except because an
    APScheduler job that raises silently stops rescheduling itself — one
    bad refresh should log and wait for the next tick, not kill the loop."""
    from app.routers.jobs import refresh_jobs

    db_gen = get_db()
    db = next(db_gen)
    try:
        result = await refresh_jobs(db=db, settings=settings)
        logger.info("Scheduled refresh: %s new, %s errors", result.new, len(result.errors))
    except Exception:
        logger.exception("Scheduled refresh failed")
    finally:
        db.close()
