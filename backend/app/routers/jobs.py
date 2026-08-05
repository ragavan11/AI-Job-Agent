from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import Settings, get_settings
from app.database import get_db
from app.job_sources.aggregator import fetch_all
from app.matching import score_job
from app.models import Job, JobScore, Profile
from app.schemas import RefreshResult, ScoredJobOut

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_auth)])

PROFILE_ID = 1


@router.post("/refresh", response_model=RefreshResult)
async def refresh_jobs(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Fetches real, live postings from every configured source, upserts
    them, and scores every new one against the current profile. This is
    the endpoint the scheduler calls automatically every
    AUTO_REFRESH_MINUTES, and that the dashboard's "Refresh" button calls
    on demand."""
    profile = db.get(Profile, PROFILE_ID)
    if not profile:
        raise HTTPException(400, "Set up your profile before refreshing jobs (PUT /profile)")

    normalized_jobs, errors, by_source = await fetch_all()

    new_count = 0
    scored_count = 0
    for nj in normalized_jobs:
        existing = db.execute(
            select(Job).where(Job.source == nj.source, Job.source_job_id == nj.source_job_id)
        ).scalar_one_or_none()

        if existing is None:
            job = Job(
                source=nj.source,
                source_job_id=nj.source_job_id,
                title=nj.title,
                company=nj.company,
                location=nj.location,
                remote=nj.remote,
                description=nj.description,
                tags=nj.tags,
                salary_min=nj.salary_min,
                salary_max=nj.salary_max,
                salary_currency=nj.salary_currency,
                apply_url=nj.apply_url,
                posted_at=nj.posted_at,
            )
            db.add(job)
            db.flush()  # assigns job.id without committing yet
            new_count += 1
        else:
            job = existing
            # Refresh mutable fields (a posting can be edited after publish)
            job.description = nj.description
            job.tags = nj.tags
            job.salary_min = nj.salary_min
            job.salary_max = nj.salary_max

        result = score_job(
            settings,
            profile_skills=profile.skills,
            profile_experience_years=profile.experience_years,
            profile_preferred_locations=profile.preferred_locations,
            profile_remote_ok=profile.remote_ok,
            profile_min_salary=profile.min_salary,
            job_tags=job.tags,
            job_location=job.location,
            job_remote=job.remote,
            job_salary_min=job.salary_min,
            job_salary_max=job.salary_max,
            job_description=job.description,
        )
        db.add(
            JobScore(
                job_id=job.id,
                profile_id=PROFILE_ID,
                skill_match_pct=result.skill_match_pct,
                location_match_pct=result.location_match_pct,
                salary_match_pct=result.salary_match_pct,
                experience_match_pct=result.experience_match_pct,
                overall_score=result.overall_score,
                matched_skills=result.matched_skills,
                missing_skills=result.missing_skills,
            )
        )
        scored_count += 1

    db.commit()
    return RefreshResult(
        fetched=len(normalized_jobs), new=new_count, scored=scored_count, by_source=by_source, errors=errors
    )


@router.get("", response_model=list[ScoredJobOut])
def list_scored_jobs(
    min_score: float = Query(default=0.0, ge=0, le=100),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Ranked list — each job's *latest* score only, highest first.

    SQLite has no DISTINCT ON, so rather than write a dialect-specific
    query (and break the day you swap in Postgres per the README), this
    pulls all scores and keeps the newest per job in Python. Fine at this
    scale — hundreds of rows, refreshed hourly, not a hot path."""
    all_scores = db.execute(select(JobScore).order_by(JobScore.computed_at.desc())).scalars().all()
    latest_by_job: dict[int, JobScore] = {}
    for s in all_scores:
        latest_by_job.setdefault(s.job_id, s)

    rows = []
    for job_id, score in latest_by_job.items():
        if score.overall_score < min_score:
            continue
        job = db.get(Job, job_id)
        if job:
            rows.append((job, score))

    rows.sort(key=lambda pair: pair[1].overall_score, reverse=True)
    return [ScoredJobOut(job=job, score=score) for job, score in rows[:limit]]


@router.get("/{job_id}", response_model=ScoredJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    score = (
        db.execute(select(JobScore).where(JobScore.job_id == job_id).order_by(JobScore.computed_at.desc()))
        .scalars()
        .first()
    )
    if not score:
        raise HTTPException(404, "Job exists but hasn't been scored yet — POST /jobs/refresh")
    return ScoredJobOut(job=job, score=score)
