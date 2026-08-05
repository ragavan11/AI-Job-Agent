"""
Ashby Job Board API — public, unauthenticated.
Docs pattern: GET https://api.ashbyhq.com/posting-api/job-board/{clientname}

Note: Ashby's exact field names have shifted slightly across API versions
in the past (e.g. jobUrl vs applyUrl). This client reads defensively with
fallbacks; if Ashby changes their shape again, `_first()` below is the
one place to add a new fallback key.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.job_sources.base import (
    JobSourceClient,
    JobSourceError,
    NormalizedJob,
    extract_tags,
    strip_html,
    tracked_companies,
)


def _first(raw: dict, *keys, default=None):
    for key in keys:
        if raw.get(key) not in (None, ""):
            return raw[key]
    return default


class AshbyClient(JobSourceClient):
    name = "ashby"

    def __init__(self, companies: list[str] | None = None, timeout: float = 15.0):
        self.companies = companies if companies is not None else tracked_companies("ashby")
        self.timeout = timeout

    async def fetch(self, limit: int = 100) -> list[NormalizedJob]:
        results: list[NormalizedJob] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for company in self.companies:
                url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    raise JobSourceError(f"ashby:{company}: {exc}") from exc

                payload = resp.json()
                for raw in payload.get("jobs", [])[:limit]:
                    location = _first(raw, "location", "locationName", default="")
                    description = strip_html(_first(raw, "descriptionHtml", "descriptionPlain", default=""))
                    is_remote = bool(raw.get("isRemote")) or "remote" in str(location).lower()
                    results.append(
                        NormalizedJob(
                            source="ashby",
                            source_job_id=str(raw.get("id", raw.get("jobId", ""))),
                            title=raw.get("title", "Untitled role"),
                            company=company,
                            location=str(location),
                            remote=is_remote,
                            description=description,
                            apply_url=_first(raw, "jobUrl", "applyUrl", "applicationUrl", default=url),
                            posted_at=_parse_dt(_first(raw, "publishedAt", "publishedDate")),
                            tags=extract_tags(raw.get("title", ""), description, raw.get("department", "") or ""),
                        )
                    )
        return results


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
