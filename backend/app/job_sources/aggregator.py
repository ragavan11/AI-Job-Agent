"""Runs every configured job source concurrently and returns a combined,
normalized result — plus a per-source error list, since a broken company
token or a source being temporarily down should never take the others out."""
from __future__ import annotations

import asyncio
import logging

from app.job_sources.ashby import AshbyClient
from app.job_sources.base import JobSourceError, NormalizedJob
from app.job_sources.greenhouse import GreenhouseClient
from app.job_sources.himalayas import HimalayasClient
from app.job_sources.lever import LeverClient
from app.job_sources.remoteok import RemoteOKClient

logger = logging.getLogger("job_agent.aggregator")


def all_clients() -> list:
    return [GreenhouseClient(), LeverClient(), AshbyClient(), RemoteOKClient(), HimalayasClient()]


async def fetch_all(limit_per_source: int = 100) -> tuple[list[NormalizedJob], list[str], dict[str, int]]:
    """Returns (jobs, error_messages, count_by_source)."""
    clients = all_clients()
    tasks = [client.fetch(limit=limit_per_source) for client in clients]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    jobs: list[NormalizedJob] = []
    errors: list[str] = []
    by_source: dict[str, int] = {}

    for client, outcome in zip(clients, outcomes):
        if isinstance(outcome, JobSourceError):
            logger.warning("Source %s failed: %s", client.name, outcome)
            errors.append(str(outcome))
            by_source[client.name] = 0
        elif isinstance(outcome, Exception):
            # Anything unexpected (bad JSON, network timeout not wrapped, etc.)
            # is still logged and skipped rather than crashing the whole refresh.
            logger.exception("Unexpected error fetching %s", client.name)
            errors.append(f"{client.name}: unexpected error — {outcome}")
            by_source[client.name] = 0
        else:
            jobs.extend(outcome)
            by_source[client.name] = len(outcome)

    return jobs, errors, by_source
