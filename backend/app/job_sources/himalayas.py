"""
Himalayas public API — global remote-jobs feed, free, no key required.
Docs pattern: GET https://himalayas.app/jobs/api

Read defensively with fallback keys, same reasoning as ashby.py: this is
a smaller, less-standardized API and field names are the most likely
thing to need a tweak on first real run.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.job_sources.base import JobSourceClient, JobSourceError, NormalizedJob, extract_tags, strip_html


def _first(raw: dict, *keys, default=None):
    for key in keys:
        if raw.get(key) not in (None, ""):
            return raw[key]
    return default


class HimalayasClient(JobSourceClient):
    name = "himalayas"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch(self, limit: int = 100) -> list[NormalizedJob]:
        url = "https://himalayas.app/jobs/api"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params={"limit": limit})
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise JobSourceError(f"himalayas: {exc}") from exc

            payload = resp.json()

        raw_jobs = payload.get("jobs", payload if isinstance(payload, list) else [])
        results: list[NormalizedJob] = []
        for raw in raw_jobs[:limit]:
            title = _first(raw, "title", default="Untitled role")
            company = _first(raw, "companyName", "company", default="Unknown")
            description = strip_html(_first(raw, "description", "excerpt", default=""))
            locations = _first(raw, "locationRestrictions", "locations", default=[])
            location = ", ".join(locations) if isinstance(locations, list) and locations else "Remote"
            categories = _first(raw, "categories", "tags", default=[]) or []
            results.append(
                NormalizedJob(
                    source="himalayas",
                    source_job_id=str(_first(raw, "id", "guid", "slug", default=title)),
                    title=title,
                    company=str(company),
                    location=location,
                    remote=True,  # Himalayas is a remote-jobs board by definition
                    description=description,
                    apply_url=_first(raw, "applicationLink", "apply_url", "url", default=url),
                    posted_at=_parse_dt(_first(raw, "pubDate", "publishedAt")),
                    salary_min=_safe_int(_first(raw, "minSalary", "salaryMin")),
                    salary_max=_safe_int(_first(raw, "maxSalary", "salaryMax")),
                    salary_currency=_first(raw, "salaryCurrency", default="USD"),
                    tags=list(dict.fromkeys([*(categories or []), *extract_tags(title, description)])),
                )
            )
        return results


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in (None, "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")) if fmt is None else datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _safe_int(value) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None
