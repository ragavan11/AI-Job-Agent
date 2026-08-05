"""
Job Matching Engine.

Deliberately deterministic and dependency-free (no LLM call) — a job's
score should be reproducible, explainable, and fast to compute for
hundreds of jobs at once. The AI engine (ai_engine/) is for the parts
that genuinely need judgment: tailoring resume language, writing a cover
letter, giving qualitative ATS feedback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import Settings

# Rough, transparent heuristic for years-of-experience requirements
# mentioned in a posting. Deliberately conservative: if nothing is found,
# the job is treated as experience-neutral (60%) rather than penalized,
# since plenty of real postings never state a number at all.
_EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+)\s*\+?\s*-?\s*(?:to)?\s*-?\s*(\d+)?\s*years?", re.IGNORECASE),
]


@dataclass
class MatchResult:
    skill_match_pct: float
    location_match_pct: float
    salary_match_pct: float
    experience_match_pct: float
    overall_score: float
    matched_skills: list[str]
    missing_skills: list[str]


def _score_skills(profile_skills: list[str], job_tags: list[str]) -> tuple[float, list[str], list[str]]:
    if not profile_skills:
        return 0.0, [], []
    profile_set = {s.strip().lower() for s in profile_skills}
    job_set = {t.strip().lower() for t in job_tags}
    matched = profile_set & job_set
    missing = profile_set - job_set
    pct = round(100 * len(matched) / len(profile_set), 1)
    # Return in original casing for display
    matched_display = [s for s in profile_skills if s.strip().lower() in matched]
    missing_display = [s for s in profile_skills if s.strip().lower() in missing]
    return pct, matched_display, missing_display


def _score_location(preferred_locations: list[str], remote_ok: bool, job_location: str, job_remote: bool) -> float:
    if job_remote and remote_ok:
        return 100.0
    if not preferred_locations:
        # No preference stated — neutral, don't penalize
        return 70.0
    job_loc_lower = job_location.lower()
    for loc in preferred_locations:
        if loc.strip().lower() in job_loc_lower:
            return 100.0
    if job_remote and not remote_ok:
        return 40.0  # remote offered but you said you don't want remote — partial credit
    return 15.0


def _score_salary(min_salary: int | None, job_min: int | None, job_max: int | None) -> float:
    if min_salary is None:
        return 70.0  # you haven't set a floor — neutral rather than penalizing every job
    if job_min is None and job_max is None:
        return 50.0  # unknown — genuinely ambiguous, not a match failure
    job_ceiling = job_max or job_min
    if job_ceiling is None:
        return 50.0
    if job_ceiling >= min_salary:
        return 100.0
    # Partial credit scaling down to 0 as the gap grows past 50% under target
    ratio = job_ceiling / min_salary
    return round(max(0.0, ratio) * 100, 1)


def _extract_experience_range(description: str) -> tuple[float, float] | None:
    match = _EXPERIENCE_PATTERNS[0].search(description)
    if not match:
        return None
    low = float(match.group(1))
    high = float(match.group(2)) if match.group(2) else low
    return low, high


def _score_experience(profile_years: float, description: str) -> float:
    found = _extract_experience_range(description)
    if found is None:
        return 60.0  # not stated — mildly neutral, most 0-2yr-friendly roles don't state a range
    low, high = found
    if low <= profile_years <= high + 1:  # +1 year of slack — requirements are rarely exact
        return 100.0
    if profile_years < low:
        gap = low - profile_years
        return round(max(0.0, 100 - gap * 35), 1)
    # over-qualified reads as a smaller penalty than under-qualified
    gap = profile_years - high
    return round(max(0.0, 100 - gap * 15), 1)


def score_job(
    settings: Settings,
    *,
    profile_skills: list[str],
    profile_experience_years: float,
    profile_preferred_locations: list[str],
    profile_remote_ok: bool,
    profile_min_salary: int | None,
    job_tags: list[str],
    job_location: str,
    job_remote: bool,
    job_salary_min: int | None,
    job_salary_max: int | None,
    job_description: str,
) -> MatchResult:
    skill_pct, matched, missing = _score_skills(profile_skills, job_tags)
    location_pct = _score_location(profile_preferred_locations, profile_remote_ok, job_location, job_remote)
    salary_pct = _score_salary(profile_min_salary, job_salary_min, job_salary_max)
    experience_pct = _score_experience(profile_experience_years, job_description)

    overall = (
        skill_pct * settings.weight_skill
        + location_pct * settings.weight_location
        + salary_pct * settings.weight_salary
        + experience_pct * settings.weight_experience
    )

    return MatchResult(
        skill_match_pct=skill_pct,
        location_match_pct=location_pct,
        salary_match_pct=salary_pct,
        experience_match_pct=experience_pct,
        overall_score=round(overall, 1),
        matched_skills=matched,
        missing_skills=missing,
    )
