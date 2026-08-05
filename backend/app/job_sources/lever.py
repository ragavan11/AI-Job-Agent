"""
Lever Postings API — public, unauthenticated.
Docs pattern: GET https://api.lever.co/v0/postings/{company}?mode=json
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.job_sources.base import (
    JobSourceClient,
    JobSourceError,
    NormalizedJob,
    extract_tags,
    strip_html,
    tracked_companies,
)


class LeverClient(JobSourceClient):
    name = "lever"

    def __init__(self, companies: list[str] | None = None, timeout: float = 15.0):
        self.companies = companies if companies is not None else tracked_companies("lever")
        self.timeout = timeout

    async def fetch(self, limit: int = 100) -> list[NormalizedJob]:
        results: list[NormalizedJob] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for company in self.companies:
                url = f"https://api.lever.co/v0/postings/{company}"
                try:
                    resp = await client.get(url, params={"mode": "json"})
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    raise JobSourceError(f"lever:{company}: {exc}") from exc

                for raw in resp.json()[:limit]:
                    categories = raw.get("categories", {}) or {}
                    location = categories.get("location", "") or ""
                    description_plain = raw.get("descriptionPlain") or strip_html(raw.get("description"))
                    lists_text = " ".join(
                        item.get("content", "") for lst in raw.get("lists", []) for item in [lst]
                    )
                    results.append(
                        NormalizedJob(
                            source="lever",
                            source_job_id=str(raw["id"]),
                            title=raw.get("text", "Untitled role"),
                            company=company,
                            location=location,
                            remote="remote" in location.lower() or categories.get("commitment", "").lower() == "remote",
                            description=description_plain,
                            apply_url=raw.get("hostedUrl", url),
                            posted_at=_epoch_ms_to_dt(raw.get("createdAt")),
                            tags=extract_tags(raw.get("text", ""), description_plain, lists_text, categories.get("team", "")),
                        )
                    )
        return results


def _epoch_ms_to_dt(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (ValueError, TypeError):
        return None
