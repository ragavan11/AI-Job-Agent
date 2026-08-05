from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.models import Profile
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"], dependencies=[Depends(require_auth)])

PROFILE_ID = 1  # Phase 1 is single-profile; see models.py docstring


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    profile = db.get(Profile, PROFILE_ID)
    if not profile:
        raise HTTPException(404, "No profile yet — POST /profile to create one")
    return profile


@router.put("", response_model=ProfileOut)
def upsert_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    """PUT rather than separate POST/PATCH: a single-row resource is
    naturally idempotent to replace wholesale."""
    profile = db.get(Profile, PROFILE_ID)
    data = payload.model_dump()
    if profile is None:
        profile = Profile(id=PROFILE_ID, **data)
        db.add(profile)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile
