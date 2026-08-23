"""Language layer. Optional. Never on the measured economic path."""

from app.llm.provider import LanguageUnavailable, get_language_provider

__all__ = ["LanguageUnavailable", "get_language_provider"]
