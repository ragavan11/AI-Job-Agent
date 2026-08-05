from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.models import Application, ApplicationStatus, Job
from app.schemas import ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"], dependencies=[Depends(require_auth)])

PROFILE_ID = 1


@router.post("/{job_id}", response_model=ApplicationOut)
def save_job(job_id: int, db: Session = Depends(get_db)):
    """Marks a job as tracked ('saved'). This is deliberately separate
    from actually applying — Phase 3 wires this to the browser-automation
    review flow instead of anything auto-submitting on creation."""
    if not db.get(Job, job_id):
        raise HTTPException(404, "Job not found")
    existing = db.query(Application).filter(Application.job_id == job_id, Application.profile_id == PROFILE_ID).first()
    if existing:
        return existing
    application = Application(job_id=job_id, profile_id=PROFILE_ID, status=ApplicationStatus.saved)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return (
        db.query(Application)
        .filter(Application.profile_id == PROFILE_ID)
        .order_by(Application.updated_at.desc())
        .all()
    )


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(404, "Application not found")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("status") == ApplicationStatus.applied and application.applied_at is None:
        application.applied_at = datetime.now(timezone.utc)
    for key, value in updates.items():
        setattr(application, key, value)

    db.commit()
    db.refresh(application)
    return application


@router.get("/stats")
def application_stats(db: Session = Depends(get_db)):
    """Powers the dashboard's summary strip."""
    applications = db.query(Application).filter(Application.profile_id == PROFILE_ID).all()
    counts = {status.value: 0 for status in ApplicationStatus}
    for app_ in applications:
        counts[application_status_value(app_)] += 1
    total_applied = sum(counts[s] for s in ("applied", "interviewing", "offer", "rejected"))
    responded = counts["interviewing"] + counts["offer"] + counts["rejected"]
    response_rate = round(100 * responded / total_applied, 1) if total_applied else 0.0
    success_rate = round(100 * counts["offer"] / total_applied, 1) if total_applied else 0.0
    return {"counts": counts, "response_rate": response_rate, "success_rate": success_rate, "total": len(applications)}


def application_status_value(application: Application) -> str:
    status = application.status
    return status.value if hasattr(status, "value") else status
