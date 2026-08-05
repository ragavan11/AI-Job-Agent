"""Pydantic schemas — the API's actual contract with the frontend."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ApplicationStatus, JobSource


# ---------- Profile ----------
class WorkHistoryItem(BaseModel):
    company: str
    title: str
    start: str
    end: str = "Present"
    bullets: list[str] = []


class EducationItem(BaseModel):
    school: str
    degree: str
    year: str


class ProjectItem(BaseModel):
    name: str
    description: str
    tech: list[str] = []


class ProfileIn(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    location: Optional[str] = None
    skills: list[str] = []
    experience_years: float = 0.0
    education: list[EducationItem] = []
    certificates: list[str] = []
    projects: list[ProjectItem] = []
    work_history: list[WorkHistoryItem] = []
    preferred_locations: list[str] = []
    remote_ok: bool = True
    min_salary: Optional[int] = None
    work_authorization: Optional[str] = None
    notice_period_days: Optional[int] = None


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


# ---------- Jobs ----------
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: JobSource
    title: str
    company: str
    location: str
    remote: bool
    description: str
    tags: list[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: Optional[str]
    apply_url: str
    posted_at: Optional[datetime]


class JobScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    skill_match_pct: float
    location_match_pct: float
    salary_match_pct: float
    experience_match_pct: float
    overall_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    computed_at: datetime


class ScoredJobOut(BaseModel):
    job: JobOut
    score: JobScoreOut


class RefreshResult(BaseModel):
    fetched: int
    new: int
    scored: int
    by_source: dict[str, int]
    errors: list[str] = []


# ---------- Resumes ----------
class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    profile_id: int
    label: str
    is_master: bool
    summary: str
    skills: list[str]
    work_history: list[dict]
    education: list[dict]
    projects: list[dict]
    tailored_for_job_id: Optional[int]
    ats_score: Optional[float]
    ats_notes: Optional[str]
    created_at: datetime


class TailorResumeRequest(BaseModel):
    job_id: int
    base_resume_id: Optional[int] = None  # defaults to the master resume


# ---------- Cover letters ----------
class CoverLetterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    profile_id: int
    content: str
    created_at: datetime


class GenerateCoverLetterRequest(BaseModel):
    job_id: int
    tone: str = Field(default="professional", description="professional | enthusiastic | concise")


# ---------- Applications ----------
class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    profile_id: int
    resume_id: Optional[int]
    cover_letter_id: Optional[int]
    status: ApplicationStatus
    notes: Optional[str]
    applied_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    resume_id: Optional[int] = None
    cover_letter_id: Optional[int] = None
