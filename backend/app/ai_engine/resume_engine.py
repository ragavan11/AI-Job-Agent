"""
Resume tailoring + ATS scoring.

ATS scoring is split deliberately into two halves:
  - a deterministic keyword-coverage score (testable, explainable, free)
  - LLM qualitative notes on phrasing/impact (needs judgment, costs a call)
Both are stored on the Resume row so the UI can show "82% keyword coverage"
next to "the AI's actual notes" rather than one opaque number.
"""
from __future__ import annotations

import json
import re

from app.ai_engine.base import LLMProvider
from app.models import Job, Profile, Resume

SYSTEM_PROMPT = """You are an expert resume writer and technical recruiter. \
You tailor resumes to specific job descriptions without ever inventing \
experience, employers, titles, dates, or skills the candidate does not \
have. You only rephrase, reorder, and re-emphasize what is actually true. \
You respond with strict JSON only — no markdown fences, no commentary."""


def keyword_coverage_score(resume_text: str, job_tags: list[str], job_description: str) -> float:
    """Deterministic half of the ATS score: what fraction of the job's
    known keywords actually appear in the resume text, case-insensitive."""
    if not job_tags:
        return 50.0  # nothing to compare against
    text_lower = resume_text.lower()
    hits = sum(1 for tag in job_tags if re.search(rf"(?<!\w){re.escape(tag.lower())}(?!\w)", text_lower))
    return round(100 * hits / len(job_tags), 1)


def _resume_to_text(resume: Resume) -> str:
    parts = [resume.summary, " ".join(resume.skills)]
    for job in resume.work_history:
        parts.append(f"{job.get('title', '')} {job.get('company', '')} " + " ".join(job.get("bullets", [])))
    for proj in resume.projects:
        parts.append(f"{proj.get('name', '')} {proj.get('description', '')} " + " ".join(proj.get("tech", [])))
    return "\n".join(parts)


async def tailor_resume(provider: LLMProvider, *, profile: Profile, base_resume: Resume, job: Job) -> dict:
    """Returns a dict with the tailored summary/skills/work_history/projects
    plus the LLM's qualitative ATS notes. Raises ValueError if the model
    doesn't return parseable JSON (surfaced to the API as a 502, not
    silently swallowed into a fake result)."""

    prompt = f"""Tailor this resume for the job below. Keep every fact true \
— do not add skills, employers, titles, or achievements that aren't in \
the original. You may reorder bullets, rewrite phrasing for impact, and \
choose which existing bullets/projects to emphasize or trim.

CANDIDATE'S EXISTING RESUME (source of truth — do not exceed this):
{json.dumps({
    "summary": base_resume.summary,
    "skills": base_resume.skills,
    "work_history": base_resume.work_history,
    "education": base_resume.education,
    "projects": base_resume.projects,
}, indent=2)}

TARGET JOB:
Title: {job.title}
Company: {job.company}
Description: {job.description[:4000]}

Respond with JSON in exactly this shape:
{{
  "summary": "2-3 sentence tailored professional summary",
  "skills": ["reordered/filtered list of the candidate's real skills, most relevant first"],
  "work_history": [{{"company": "...", "title": "...", "start": "...", "end": "...", "bullets": ["..."]}}],
  "projects": [{{"name": "...", "description": "...", "tech": ["..."]}}],
  "ats_notes": "2-4 sentences of concrete, actionable feedback on how well this resume now matches the job and what's still missing"
}}"""

    raw = await provider.complete(system=SYSTEM_PROMPT, prompt=prompt, max_tokens=3000)
    data = _parse_json_response(raw)

    resume_text = _resume_to_text_from_dict(data)
    data["keyword_score"] = keyword_coverage_score(resume_text, job.tags, job.description)
    return data


def _resume_to_text_from_dict(data: dict) -> str:
    parts = [data.get("summary", ""), " ".join(data.get("skills", []))]
    for job in data.get("work_history", []):
        parts.append(" ".join(job.get("bullets", [])))
    for proj in data.get("projects", []):
        parts.append(f"{proj.get('description', '')} " + " ".join(proj.get("tech", [])))
    return "\n".join(parts)


def _parse_json_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?", "", cleaned).rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI provider did not return valid JSON: {exc}\nRaw response: {raw[:500]}") from exc
