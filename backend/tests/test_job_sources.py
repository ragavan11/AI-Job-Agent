"""
These mock each source's *documented* response shape rather than hitting
the live APIs — this sandbox's network allowlist doesn't include job
boards, and a test suite shouldn't depend on the public internet being
reachable and unchanged anyway. If a source tweaks its schema, these are
exactly the tests that should start failing, which is the point.
"""
import respx
from httpx import Response

from app.job_sources.ashby import AshbyClient
from app.job_sources.greenhouse import GreenhouseClient
from app.job_sources.himalayas import HimalayasClient
from app.job_sources.lever import LeverClient
from app.job_sources.remoteok import RemoteOKClient


@respx.mock
async def test_greenhouse_client_normalizes_response():
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs").mock(
        return_value=Response(
            200,
            json={
                "jobs": [
                    {
                        "id": 123,
                        "title": "ML Engineer",
                        "location": {"name": "Remote"},
                        "content": "<p>Need Python and SQL experience.</p>",
                        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
        )
    )
    jobs = await GreenhouseClient(companies=["stripe"]).fetch()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "greenhouse"
    assert job.source_job_id == "123"
    assert job.title == "ML Engineer"
    assert job.remote is True
    assert "Python" in job.description
    assert "Python" in job.tags and "SQL" in job.tags


@respx.mock
async def test_lever_client_normalizes_response():
    respx.get("https://api.lever.co/v0/postings/palantir").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "abc123",
                    "text": "Data Scientist",
                    "categories": {"location": "Bangalore", "team": "Data", "commitment": "Full-time"},
                    "descriptionPlain": "Looking for someone strong in Python and SQL.",
                    "hostedUrl": "https://jobs.lever.co/palantir/abc123",
                    "createdAt": 1735689600000,
                    "lists": [],
                }
            ],
        )
    )
    jobs = await LeverClient(companies=["palantir"]).fetch()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "lever"
    assert job.title == "Data Scientist"
    assert job.location == "Bangalore"
    assert job.remote is False
    assert job.posted_at is not None


@respx.mock
async def test_ashby_client_normalizes_response_and_handles_field_fallbacks():
    respx.get("https://api.ashbyhq.com/posting-api/job-board/notion").mock(
        return_value=Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "xyz",
                        "title": "ML Engineer",
                        "location": "Remote",
                        "descriptionHtml": "<p>Python, SQL, Machine Learning.</p>",
                        "jobUrl": "https://jobs.ashbyhq.com/notion/xyz",
                        "publishedAt": "2026-01-01T00:00:00Z",
                        "isRemote": True,
                        "department": "Engineering",
                    }
                ]
            },
        )
    )
    jobs = await AshbyClient(companies=["notion"]).fetch()
    assert len(jobs) == 1
    assert jobs[0].remote is True
    assert jobs[0].apply_url == "https://jobs.ashbyhq.com/notion/xyz"


@respx.mock
async def test_remoteok_client_skips_the_legal_notice_object():
    respx.get("https://remoteok.com/api").mock(
        return_value=Response(
            200,
            json=[
                {"legal": "https://remoteok.com/legal", "info": "not a job"},
                {
                    "id": 111,
                    "position": "Data Analyst",
                    "company": "Acme",
                    "location": "Worldwide",
                    "tags": ["python", "sql"],
                    "description": "<p>Python and SQL role.</p>",
                    "url": "https://remoteok.com/remote-jobs/111",
                    "date": "2026-01-01T00:00:00+00:00",
                    "salary_min": 50000,
                    "salary_max": 80000,
                },
            ],
        )
    )
    jobs = await RemoteOKClient().fetch()
    assert len(jobs) == 1
    assert jobs[0].title == "Data Analyst"
    assert jobs[0].remote is True
    assert jobs[0].salary_min == 50000


@respx.mock
async def test_himalayas_client_normalizes_response():
    respx.get("https://himalayas.app/jobs/api").mock(
        return_value=Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "h1",
                        "title": "ML Engineer",
                        "companyName": "Acme Remote",
                        "description": "Python, SQL, Machine Learning needed.",
                        "locationRestrictions": ["Worldwide"],
                        "applicationLink": "https://himalayas.app/jobs/h1",
                        "pubDate": "2026-01-01T00:00:00Z",
                        "categories": ["Python", "SQL"],
                    }
                ]
            },
        )
    )
    jobs = await HimalayasClient().fetch()
    assert len(jobs) == 1
    assert jobs[0].company == "Acme Remote"
    assert jobs[0].remote is True
    assert "Python" in jobs[0].tags


@respx.mock
async def test_greenhouse_raises_job_source_error_on_http_failure():
    respx.get("https://boards-api.greenhouse.io/v1/boards/doesnotexist/jobs").mock(return_value=Response(404))
    from app.job_sources.base import JobSourceError

    try:
        await GreenhouseClient(companies=["doesnotexist"]).fetch()
        assert False, "expected JobSourceError"
    except JobSourceError:
        pass
