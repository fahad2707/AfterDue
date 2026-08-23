"""Anthropic adapter. The only module that may mention the vendor SDK."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.provider import LanguageUnavailable

T = TypeVar("T", bound=BaseModel)


class AnthropicProvider:
    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_structured(
        self, *, system: str, user: str, schema: type[T]
    ) -> T:
        try:
            import anthropic
        except ImportError as exc:
            raise LanguageUnavailable("anthropic package is not installed") from exc
        client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout_seconds)
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=800,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            raise LanguageUnavailable(f"anthropic request failed: {exc}") from exc
        text = "".join(part.text for part in message.content if getattr(part, "type", "") == "text")
        try:
            payload = json.loads(_extract_json(text))
            return schema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise LanguageUnavailable(f"malformed language output: {exc}") from exc


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise LanguageUnavailable("language output contained no JSON object")
    return text[start : end + 1]
