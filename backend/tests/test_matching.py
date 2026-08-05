from app.config import Settings
from app.matching import score_job


def make_settings(**overrides) -> Settings:
    defaults = dict(
        api_auth_token="t",
        anthropic_api_key="k",
        weight_skill=0.40,
        weight_location=0.25,
        weight_salary=0.20,
        weight_experience=0.15,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_perfect_match_scores_high():
    settings = make_settings()
    result = score_job(
        settings,
        profile_skills=["Python", "SQL", "Machine Learning"],
        profile_experience_years=1.5,
        profile_preferred_locations=["Bangalore"],
        profile_remote_ok=True,
        profile_min_salary=None,
        job_tags=["Python", "SQL", "Machine Learning", "Pandas"],
        job_location="Bangalore, India",
        job_remote=False,
        job_salary_min=None,
        job_salary_max=None,
        job_description="Looking for 1-2 years of experience with Python and SQL.",
    )
    assert result.skill_match_pct == 100.0
    assert result.location_match_pct == 100.0
    assert result.experience_match_pct == 100.0
    assert result.overall_score > 90


def test_no_skill_overlap_scores_zero_on_skills():
    settings = make_settings()
    result = score_job(
        settings,
        profile_skills=["Python", "SQL"],
        profile_experience_years=1.0,
        profile_preferred_locations=[],
        profile_remote_ok=True,
        profile_min_salary=None,
        job_tags=["Java", "Kotlin"],
        job_location="Remote",
        job_remote=True,
        job_salary_min=None,
        job_salary_max=None,
        job_description="",
    )
    assert result.skill_match_pct == 0.0
    assert result.matched_skills == []
    assert set(result.missing_skills) == {"Python", "SQL"}


def test_remote_job_matches_remote_ok_profile_regardless_of_location_list():
    settings = make_settings()
    result = score_job(
        settings,
        profile_skills=["Python"],
        profile_experience_years=1.0,
        profile_preferred_locations=["Chennai"],
        profile_remote_ok=True,
        profile_min_salary=None,
        job_tags=["Python"],
        job_location="Anywhere",
        job_remote=True,
        job_salary_min=None,
        job_salary_max=None,
        job_description="",
    )
    assert result.location_match_pct == 100.0


def test_salary_below_minimum_gets_partial_credit_not_zero():
    settings = make_settings()
    result = score_job(
        settings,
        profile_skills=["Python"],
        profile_experience_years=1.0,
        profile_preferred_locations=[],
        profile_remote_ok=True,
        profile_min_salary=1_000_000,
        job_tags=["Python"],
        job_location="Remote",
        job_remote=True,
        job_salary_min=700_000,
        job_salary_max=800_000,
        job_description="",
    )
    assert 0 < result.salary_match_pct < 100


def test_missing_salary_data_is_neutral_not_penalized():
    settings = make_settings()
    result = score_job(
        settings,
        profile_skills=["Python"],
        profile_experience_years=1.0,
        profile_preferred_locations=[],
        profile_remote_ok=True,
        profile_min_salary=1_000_000,
        job_tags=["Python"],
        job_location="Remote",
        job_remote=True,
        job_salary_min=None,
        job_salary_max=None,
        job_description="",
    )
    assert result.salary_match_pct == 50.0


def test_experience_requirement_extracted_from_description():
    settings = make_settings()
    over_qualified = score_job(
        settings,
        profile_skills=["Python"],
        profile_experience_years=8.0,
        profile_preferred_locations=[],
        profile_remote_ok=True,
        profile_min_salary=None,
        job_tags=["Python"],
        job_location="Remote",
        job_remote=True,
        job_salary_min=None,
        job_salary_max=None,
        job_description="We need someone with 0-2 years of experience.",
    )
    under_qualified = score_job(
        settings,
        profile_skills=["Python"],
        profile_experience_years=0.0,
        profile_preferred_locations=[],
        profile_remote_ok=True,
        profile_min_salary=None,
        job_tags=["Python"],
        job_location="Remote",
        job_remote=True,
        job_salary_min=None,
        job_salary_max=None,
        job_description="We need someone with 5+ years of experience.",
    )
    assert over_qualified.experience_match_pct < 100
    assert under_qualified.experience_match_pct < over_qualified.experience_match_pct


def test_overall_score_respects_configured_weights():
    all_skill_weight = make_settings(weight_skill=1.0, weight_location=0.0, weight_salary=0.0, weight_experience=0.0)
    result = score_job(
        all_skill_weight,
        profile_skills=["Python"],
        profile_experience_years=1.0,
        profile_preferred_locations=[],
        profile_remote_ok=False,
        profile_min_salary=None,
        job_tags=["Python"],
        job_location="Nowhere you want",
        job_remote=False,
        job_salary_min=None,
        job_salary_max=None,
        job_description="",
    )
    # location/salary/experience would all be mediocre-to-bad here, but
    # with 100% weight on skill (a perfect match), overall should track
    # the skill score almost exactly.
    assert result.overall_score == result.skill_match_pct
