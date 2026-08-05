"""
Shared contract for job-source clients.

Every source is wildly inconsistent about field names (title vs text vs
position, location as a string vs a nested object, salary present or
absent entirely) — each client's only job is to normalize its source's
response into a NormalizedJob. Nothing downstream needs to know which
source a job came from.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

COMPANIES_FILE = Path(__file__).resolve().parent.parent / "tracked_companies.json"


def tracked_companies(source: str) -> list[str]:
    """Companies to query for a per-company ATS source, from the editable
    tracked_companies.json config (not hardcoded, not a database table —
    it's meant to be hand-edited as you decide who to track)."""
    data = json.loads(COMPANIES_FILE.read_text())
    return data.get(source, [])


@dataclass
class NormalizedJob:
    source: str
    source_job_id: str
    title: str
    company: str
    location: str
    remote: bool
    description: str  # plain text, HTML stripped
    apply_url: str
    posted_at: datetime | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    tags: list[str] = field(default_factory=list)


class _HTMLStripper(HTMLParser):
    """Tiny dependency-free HTML-to-text converter — job descriptions from
    these APIs are almost always HTML and we only ever need plain text for
    scoring, ATS comparison, and display."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "li", "div"):
            self.parts.append("\n")


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(raw)
    text = unescape("".join(stripper.parts))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# A deliberately broad, extensible skill/keyword vocabulary used to tag
# jobs from sources (RemoteOK, Himalayas) that don't already return tags.
# This is intentionally simple and regex-based rather than an ML model —
# transparent, fast, zero extra dependencies, and easy for you to extend
# in one place as your target roles change.
SKILL_VOCAB = [
    "Python", "SQL", "R", "Java", "Scala", "Go", "C++",
    "Machine Learning", "Deep Learning", "NLP", "LLM", "RAG", "Computer Vision",
    "PyTorch", "TensorFlow", "Scikit-learn", "Keras", "Hugging Face",
    "Pandas", "NumPy", "Spark", "Hadoop", "Airflow", "dbt",
    "Power BI", "Tableau", "Looker", "Excel",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Snowflake", "BigQuery",
    "React", "Node.js", "FastAPI", "Django", "Flask",
    "Data Science", "Data Engineering", "Data Analyst", "MLOps",
]

_SKILL_PATTERNS = [(s, re.compile(rf"(?<![\w+#]){re.escape(s)}(?![\w+#])", re.IGNORECASE)) for s in SKILL_VOCAB]


def extract_tags(*texts: str) -> list[str]:
    """Find which known skills appear in the given text(s). Order-preserving,
    de-duplicated, case-insensitive match but canonical-case output."""
    blob = " ".join(t for t in texts if t)
    found: list[str] = []
    for canonical, pattern in _SKILL_PATTERNS:
        if pattern.search(blob) and canonical not in found:
            found.append(canonical)
    return found


class JobSourceClient(ABC):
    """One instance per source. `fetch()` does the real HTTP call — no
    mock data, no cached fixtures pretending to be live results."""

    name: str

    @abstractmethod
    async def fetch(self, limit: int = 100) -> list[NormalizedJob]:
        ...


class JobSourceError(RuntimeError):
    """Raised when a single company/source fetch fails. The aggregator
    catches this per-source so one bad token or one down API doesn't stop
    the others from returning results."""
