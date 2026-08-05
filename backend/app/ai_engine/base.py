"""
Provider-agnostic LLM interface.

resume_engine.py and cover_letter_engine.py depend only on this
interface, never on `anthropic`, `openai`, or `google.generativeai`
directly. That's what makes "AI Provider" a one-line setting instead of
a rewrite — and it's why swapping providers can't accidentally leave one
feature on the old vendor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from fastapi import Depends

from app.config import Settings, get_settings


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, *, system: str, prompt: str, max_tokens: int = 2000) -> str:
        """Single-turn completion. Returns plain text — callers that need
        structured output ask for JSON in the prompt and parse it
        themselves, so this interface stays identical across vendors."""


def get_provider(settings: Settings) -> LLMProvider:
    if settings.ai_provider == "anthropic":
        from app.ai_engine.anthropic_provider import AnthropicProvider

        if not settings.anthropic_api_key:
            raise MissingAPIKeyError("ANTHROPIC_API_KEY is not set (see .env.example)")
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)

    if settings.ai_provider == "openai":
        from app.ai_engine.openai_provider import OpenAIProvider

        if not settings.openai_api_key:
            raise MissingAPIKeyError("OPENAI_API_KEY is not set (see .env.example)")
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)

    if settings.ai_provider == "gemini":
        from app.ai_engine.gemini_provider import GeminiProvider

        if not settings.gemini_api_key:
            raise MissingAPIKeyError("GEMINI_API_KEY is not set (see .env.example)")
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)

    raise ValueError(f"Unknown ai_provider: {settings.ai_provider}")


class MissingAPIKeyError(RuntimeError):
    pass


def provider_dependency(settings: Settings = Depends(get_settings)) -> LLMProvider:
    """FastAPI dependency version of get_provider — routes use
    `Depends(provider_dependency)` instead of calling get_provider()
    directly, specifically so tests can override it with a fake provider
    via app.dependency_overrides instead of needing a real API key."""
    return get_provider(settings)
