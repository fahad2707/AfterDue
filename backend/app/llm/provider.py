"""Language-provider interface. Callers must not import Anthropic."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LanguageUnavailable(RuntimeError):
    """LLM is disabled, unconfigured, or failed. Use the deterministic path."""


class LanguageProvider(Protocol):
    def generate_structured(
        self, *, system: str, user: str, schema: type[T]
    ) -> T: ...


def get_language_provider() -> LanguageProvider | None:
    """None when the language layer is off. Startup never requires a key."""
    settings = get_settings()
    if not settings.llm_enabled or not settings.anthropic_api_key.strip():
        return None
    from app.llm.anthropic_provider import AnthropicProvider

    return AnthropicProvider(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model or "claude-sonnet-4-20250514",
        timeout_seconds=settings.llm_timeout_seconds,
    )
