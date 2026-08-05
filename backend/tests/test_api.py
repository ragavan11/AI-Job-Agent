from app.models import Job, JobScore


def test_rejects_requests_without_auth(client):
    resp = client.get("/profile")
    assert resp.status_code == 401


def test_profile_create_and_fetch(client, auth_headers):
    payload = {
        "full_name": "Asha Rao",
        "email": "asha@example.com",
        "skills": ["Python", "SQL", "Machine Learning"],
        "experience_years": 1.0,
        "preferred_locations": ["Chennai", "Bangalore"],
        "remote_ok": True,
    }
    put_resp = client.put("/profile", json=payload, headers=auth_headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["full_name"] == "Asha Rao"

    get_resp = client.get("/profile", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["skills"] == ["Python", "SQL", "Machine Learning"]


def test_profile_missing_before_creation(client, auth_headers):
    resp = client.get("/profile", headers=auth_headers)
    assert resp.status_code == 404


def test_jobs_list_ranks_by_score_desc(client, auth_headers, db_session):
    job_low = Job(
        source="remoteok", source_job_id="1", title="Junior Analyst", company="A",
        location="Remote", remote=True, description="", tags=["Excel"], apply_url="https://example.com/1",
    )
    job_high = Job(
        source="remoteok", source_job_id="2", title="ML Engineer", company="B",
        location="Remote", remote=True, description="", tags=["Python"], apply_url="https://example.com/2",
    )
    db_session.add_all([job_low, job_high])
    db_session.commit()
    db_session.refresh(job_low)
    db_session.refresh(job_high)

    db_session.add(JobScore(
        job_id=job_low.id, profile_id=1, skill_match_pct=10, location_match_pct=100,
        salary_match_pct=50, experience_match_pct=50, overall_score=30.0,
    ))
    db_session.add(JobScore(
        job_id=job_high.id, profile_id=1, skill_match_pct=100, location_match_pct=100,
        salary_match_pct=100, experience_match_pct=100, overall_score=95.0,
    ))
    db_session.commit()

    resp = client.get("/jobs", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert results[0]["job"]["title"] == "ML Engineer"  # higher score first
    assert results[0]["score"]["overall_score"] == 95.0


def test_jobs_list_filters_by_min_score(client, auth_headers, db_session):
    job = Job(
        source="remoteok", source_job_id="3", title="Low Match", company="C",
        location="Remote", remote=True, description="", tags=[], apply_url="https://example.com/3",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    db_session.add(JobScore(
        job_id=job.id, profile_id=1, skill_match_pct=0, location_match_pct=0,
        salary_match_pct=0, experience_match_pct=0, overall_score=5.0,
    ))
    db_session.commit()

    resp = client.get("/jobs", params={"min_score": 50}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_application_save_and_status_update(client, auth_headers, db_session):
    job = Job(
        source="remoteok", source_job_id="4", title="Data Analyst", company="D",
        location="Remote", remote=True, description="", tags=[], apply_url="https://example.com/4",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    save_resp = client.post(f"/applications/{job.id}", headers=auth_headers)
    assert save_resp.status_code == 200
    application_id = save_resp.json()["id"]
    assert save_resp.json()["status"] == "saved"

    update_resp = client.patch(
        f"/applications/{application_id}", json={"status": "applied", "notes": "Applied via company site"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["status"] == "applied"
    assert body["applied_at"] is not None

    stats_resp = client.get("/applications/stats", headers=auth_headers)
    assert stats_resp.status_code == 200
    assert stats_resp.json()["counts"]["applied"] == 1
