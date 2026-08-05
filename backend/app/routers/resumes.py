from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai_engine import LLMProvider, provider_dependency
from app.ai_engine.resume_engine import tailor_resume
from app.auth import require_auth
from app.database import get_db
from app.docx_export import resume_to_docx
from app.models import Job, Profile, Resume
from app.pdf_export import resume_to_pdf
from app.schemas import ResumeOut, TailorResumeRequest

router = APIRouter(prefix="/resumes", tags=["resumes"], dependencies=[Depends(require_auth)])

PROFILE_ID = 1


@router.get("", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db)):
    return db.query(Resume).filter(Resume.profile_id == PROFILE_ID).order_by(Resume.created_at.desc()).all()


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")
    return resume


@router.post("/tailor", response_model=ResumeOut)
async def tailor(
    payload: TailorResumeRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(provider_dependency),
):
    """Creates a NEW resume tailored to a specific job — never overwrites
    the base resume, so your master copy is always intact. Which resume
    to tailor from is `base_resume_id` in the body (defaults to your
    master resume) — there's deliberately no resume id in the URL path,
    since this always creates a new row rather than acting on an existing
    one."""
    base_resume = db.get(Resume, payload.base_resume_id) if payload.base_resume_id else (
        db.query(Resume).filter(Resume.profile_id == PROFILE_ID, Resume.is_master.is_(True)).first()
    )
    if not base_resume:
        raise HTTPException(400, "No base resume found — create a master resume first")

    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    profile = db.get(Profile, PROFILE_ID)

    tailored = await tailor_resume(provider, profile=profile, base_resume=base_resume, job=job)

    new_resume = Resume(
        profile_id=PROFILE_ID,
        label=f"{job.company} — {job.title}"[:200],
        is_master=False,
        summary=tailored.get("summary", ""),
        skills=tailored.get("skills", []),
        work_history=tailored.get("work_history", []),
        education=base_resume.education,
        projects=tailored.get("projects", []),
        tailored_for_job_id=job.id,
        ats_score=tailored.get("keyword_score"),
        ats_notes=tailored.get("ats_notes"),
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    return new_resume


@router.get("/{resume_id}/export.pdf")
def export_pdf(resume_id: int, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    profile = db.get(Profile, PROFILE_ID)
    if not resume or not profile:
        raise HTTPException(404, "Resume or profile not found")
    pdf_bytes = resume_to_pdf(profile, resume)
    filename = f"{profile.full_name.replace(' ', '_')}_resume.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{resume_id}/export.docx")
def export_docx(resume_id: int, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    profile = db.get(Profile, PROFILE_ID)
    if not resume or not profile:
        raise HTTPException(404, "Resume or profile not found")
    docx_bytes = resume_to_docx(profile, resume)
    filename = f"{profile.full_name.replace(' ', '_')}_resume.docx"
    return Response(
        content=docx_bytes, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
