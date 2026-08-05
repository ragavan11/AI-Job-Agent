"""
Application settings.

Everything that could vary between machines or that is remotely sensitive
(API keys, the local API auth token) lives in environment variables, never
in source. Copy .env.example to .env and fill it in — pydantic-settings
loads it automatically.
"""
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Local API access ---
    # This API has no user accounts (it's single-user, local), but it still
    # requires a shared-secret bearer token so that nothing on your machine
    # or network can hit it unauthenticated. Generate one with:
    #   python -c "import secrets; print(secrets.token_urlsafe(32))"
    api_auth_token: str = Field(..., description="Bearer token required on every request")

    # --- Database ---
    database_url: str = Field(default="sqlite:///./data/jobagent.db")

    # --- AI provider selection ---
    ai_provider: Literal["anthropic", "openai", "gemini"] = Field(default="anthropic")
    anthropic_api_key: Optional[str] = Field(default=None)
    anthropic_model: str = Field(default="claude-sonnet-4-6")
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4o")
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-2.0-flash")

    # --- Job search filters (your defaults; overridable per-request later) ---
    target_skills: list[str] = Field(
        default=["Python", "SQL", "Machine Learning", "LLM", "RAG", "Pandas", "NumPy", "Scikit-learn"]
    )
    target_locations: list[str] = Field(
        default=["Bangalore", "Chennai", "Hyderabad", "Pune", "Remote"]
    )
    min_experience_years: float = Field(default=0.0)
    max_experience_years: float = Field(default=2.0)
    min_salary: Optional[int] = Field(default=None)

    # --- Matching engine weights (must sum to 1.0) ---
    weight_skill: float = Field(default=0.40)
    weight_location: float = Field(default=0.25)
    weight_salary: float = Field(default=0.20)
    weight_experience: float = Field(default=0.15)

    # --- Automation posture ---
    # Every application submission is held for manual review by default.
    # This is intentional — see the README before flipping it.
    require_review_before_submit: bool = Field(default=True)

    # --- Background refresh ---
    auto_refresh_minutes: int = Field(default=60)
    enable_scheduler: bool = Field(default=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
