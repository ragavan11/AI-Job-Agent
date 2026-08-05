"""
RemoteOK public API — global feed (not per-company), no auth required.
Docs pattern: GET https://remoteok.com/api

The first element of the response array is always a legal/notice object,
not a job — it's filtered out below by checking for an "id" field.
RemoteOK is known to reject requests with a generic/default User-Agent,
so a realistic one is set explicitly.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.job_sources.base import JobSourceClient, JobSourceError, NormalizedJob, extract_tags, strip_html

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PersonalJobAgent/1.0; +local-use-only)"}


class RemoteOKClient(JobSourceClient):
    name = "remoteok"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch(self, limit: int = 100) -> list[NormalizedJob]:
        url = "https://remoteok.com/api"
        async with httpx.AsyncClient(timeout=self.timeout, headers=HEADERS) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise JobSourceError(f"remoteok: {exc}") from exc

            payload = resp.json()

        results: list[NormalizedJob] = []
        for raw in payload:
            if "id" not in raw or "position" not in raw:
                continue  # skips the legal-notice object RemoteOK always puts first
            description = strip_html(raw.get("description"))
            tags = raw.get("tags") or []
            results.append(
                NormalizedJob(
                    source="remoteok",
                    source_job_id=str(raw["id"]),
                    title=raw.get("position", "Untitled role"),
                    company=raw.get("company", "Unknown"),
                    location=raw.get("location") or "Remote",
                    remote=True,  # RemoteOK is remote-only by definition
                    description=description,
                    apply_url=raw.get("url") or raw.get("apply_url") or url,
                    posted_at=_parse_dt(raw.get("date")),
                    salary_min=_safe_int(raw.get("salary_min")),
                    salary_max=_safe_int(raw.get("salary_max")),
                    salary_currency="USD",
                    tags=list(dict.fromkeys([*tags, *extract_tags(raw.get("position", ""), description)])),
                )
            )
            if len(results) >= limit:
                break
        return results


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None
