"""
These override provider_dependency with a fake LLM that returns a fixed,
known response — so they test the endpoint's plumbing (does it save the
right rows, return the right shape, wire the prompt correctly) without
needing a real API key or making a real network call.

The prompt-quality itself (does Anthropic/OpenAI/Gemini actually produce
good tailored resumes) isn't something a unit test can meaningfully
assert — that needs a real key and a human reading the output, which is
exactly what the README's first-run checklist is for.
"""
import json

from app.ai_engine.base import LLMProvider, provider_dependency
from app.main import app
from app.models import Job, Profile, Resume


class FakeProvider(LLMProvider):
    def __init__(self, response: str):
        self._response = response

    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2000) -> str:
        return self._response


def _seed_profile_and_job(db_session):
    profile = Profile(
        id=1, full_name="Asha Rao", email="asha@example.com",
        skills=["Python", "SQL"], experience_years=1.0,
    )
    resume = Resume(
        profile_id=1, label="Master", is_master=True,
        summary="Early-career data scientist.", skills=["Python", "SQL"],
        work_history=[{"company": "Acme", "title": "Data Analyst", "start": "2024", "end": "Present", "bullets": ["Built dashboards"]}],
        education=[{"school": "IIT", "degree": "B.Tech", "year": "2024"}],
        projects=[],
    )
    job = Job(
        source="remoteok", source_job_id="99", title="ML Engineer", company="Initech",
        location="Remote", remote=True, description="Need Python and SQL skills.",
        tags=["Python", "SQL"], apply_url="https://example.com/99",
    )
    db_session.add_all([profile, resume, job])
    db_session.commit()
    db_session.refresh(resume)
    db_session.refresh(job)
    return profile, resume, job


def test_tailor_resume_creates_new_resume_without_touching_master(client, auth_headers, db_session):
    _, master_resume, job = _seed_profile_and_job(db_session)

    fake_json = json.dumps({
        "summary": "Data scientist tailored for Initech's ML role.",
        "skills": ["Python", "SQL"],
        "work_history": [{"company": "Acme", "title": "Data Analyst", "start": "2024", "end": "Present", "bullets": ["Built ML-adjacent dashboards"]}],
        "projects": [],
        "ats_notes": "Strong keyword overlap; consider adding a project bullet.",
    })
    app.dependency_overrides[provider_dependency] = lambda: FakeProvider(fake_json)
    try:
        resp = client.post("/resumes/tailor", json={"job_id": job.id}, headers=auth_headers)
    finally:
        del app.dependency_overrides[provider_dependency]

    assert resp.status_code == 200
    body = resp.json()
    assert body["tailored_for_job_id"] == job.id
    assert body["is_master"] is False
    assert "Initech" in body["summary"]
    assert body["ats_score"] is not None  # deterministic keyword_coverage_score was computed

    # Master resume must be untouched
    list_resp = client.get("/resumes", headers=auth_headers)
    labels = {r["label"] for r in list_resp.json()}
    assert "Master" in labels


def test_tailor_resume_without_job_id_returns_404(client, auth_headers, db_session):
    _seed_profile_and_job(db_session)
    app.dependency_overrides[provider_dependency] = lambda: FakeProvider("{}")
    try:
        resp = client.post("/resumes/tailor", json={"job_id": 99999}, headers=auth_headers)
    finally:
        del app.dependency_overrides[provider_dependency]
    assert resp.status_code == 404


def test_generate_cover_letter(client, auth_headers, db_session):
    _seed_profile_and_job(db_session)
    job = db_session.query(Job).filter(Job.source_job_id == "99").first()

    fake_letter = "Dear Initech Hiring Team,\n\nI'm excited to apply for the ML Engineer role."
    app.dependency_overrides[provider_dependency] = lambda: FakeProvider(fake_letter)
    try:
        resp = client.post("/cover-letters", json={"job_id": job.id}, headers=auth_headers)
    finally:
        del app.dependency_overrides[provider_dependency]

    assert resp.status_code == 200
    assert resp.json()["content"] == fake_letter
