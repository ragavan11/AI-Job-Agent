from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.ai_engine import LLMProvider, provider_dependency
from app.ai_engine.cover_letter_engine import generate_cover_letter
from app.auth import require_auth
from app.database import get_db
from app.models import CoverLetter, Job, Profile
from app.pdf_export import cover_letter_to_pdf
from app.schemas import CoverLetterOut, GenerateCoverLetterRequest

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"], dependencies=[Depends(require_auth)])

PROFILE_ID = 1


@router.post("", response_model=CoverLetterOut)
async def generate(
    payload: GenerateCoverLetterRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(provider_dependency),
):
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    profile = db.get(Profile, PROFILE_ID)
    if not profile:
        raise HTTPException(400, "Set up your profile first")

    content = await generate_cover_letter(provider, profile=profile, job=job, tone=payload.tone)

    letter = CoverLetter(job_id=job.id, profile_id=PROFILE_ID, content=content)
    db.add(letter)
    db.commit()
    db.refresh(letter)
    return letter


@router.get("/{letter_id}", response_model=CoverLetterOut)
def get_letter(letter_id: int, db: Session = Depends(get_db)):
    letter = db.get(CoverLetter, letter_id)
    if not letter:
        raise HTTPException(404, "Cover letter not found")
    return letter


@router.get("/{letter_id}/export.pdf")
def export_pdf(letter_id: int, db: Session = Depends(get_db)):
    letter = db.get(CoverLetter, letter_id)
    if not letter:
        raise HTTPException(404, "Cover letter not found")
    profile = db.get(Profile, PROFILE_ID)
    job = db.get(Job, letter.job_id)
    pdf_bytes = cover_letter_to_pdf(profile, job.company if job else "", letter.content)
    filename = f"cover_letter_{job.company.replace(' ', '_') if job else letter_id}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
