"""Cover letter generation — grounded strictly in the candidate's real
profile data. The prompt explicitly forbids inventing achievements,
because a fabricated claim in a cover letter is a much bigger liability
than a generic one."""
from __future__ import annotations

import json

from app.ai_engine.base import LLMProvider
from app.models import Job, Profile

SYSTEM_PROMPT = """You are an expert cover letter writer. You write \
specific, concrete cover letters grounded only in the candidate's real \
background — never invented achievements, numbers, or experience. You \
avoid generic filler ("I am a hard worker who is passionate about..."). \
You respond with plain text only: the letter body, no subject line, no \
JSON, no markdown fences, no placeholder brackets like [Company Name]."""


async def generate_cover_letter(provider: LLMProvider, *, profile: Profile, job: Job, tone: str = "professional") -> str:
    prompt = f"""Write a cover letter for this candidate applying to this job. \
Tone: {tone}. Length: 3-4 short paragraphs. Reference 1-2 specific, real \
things from the candidate's background that genuinely connect to this \
role — not a generic list of their skills.

CANDIDATE:
{json.dumps({
    "name": profile.full_name,
    "skills": profile.skills,
    "experience_years": profile.experience_years,
    "work_history": profile.work_history,
    "projects": profile.projects,
    "education": profile.education,
}, indent=2)}

JOB:
Title: {job.title}
Company: {job.company}
Description: {job.description[:3000]}

Write the letter body now. Do not include a greeting line placeholder \
like [Hiring Manager] — write "Dear {job.company} Hiring Team," as the \
opening line, then the letter."""

    return (await provider.complete(system=SYSTEM_PROMPT, prompt=prompt, max_tokens=1200)).strip()
