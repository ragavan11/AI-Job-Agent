"""
Greenhouse Job Board API — public, unauthenticated, meant for exactly this.
Docs pattern: GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

One request per tracked company (see tracked_companies.json).
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


class GreenhouseClient(JobSourceClient):
    name = "greenhouse"

    def __init__(self, companies: list[str] | None = None, timeout: float = 15.0):
        self.companies = companies if companies is not None else tracked_companies("greenhouse")
        self.timeout = timeout

    async def fetch(self, limit: int = 100) -> list[NormalizedJob]:
        results: list[NormalizedJob] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for token in self.companies:
                url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
                try:
                    resp = await client.get(url, params={"content": "true"})
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    # A bad/renamed token shouldn't take down the whole refresh —
                    # surface it to the caller's error log instead.
                    raise JobSourceError(f"greenhouse:{token}: {exc}") from exc

                payload = resp.json()
                for raw in payload.get("jobs", [])[:limit]:
                    location_name = (raw.get("location") or {}).get("name", "")
                    description = strip_html(raw.get("content"))
                    results.append(
                        NormalizedJob(
                            source="greenhouse",
                            source_job_id=str(raw["id"]),
                            title=raw.get("title", "Untitled role"),
                            company=token,
                            location=location_name,
                            remote="remote" in location_name.lower(),
                            description=description,
                            apply_url=raw.get("absolute_url", url),
                            posted_at=_parse_dt(raw.get("updated_at")),
                            tags=extract_tags(raw.get("title", ""), description),
                        )
                    )
        return results


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
