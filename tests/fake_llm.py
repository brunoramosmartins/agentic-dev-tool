"""Test doubles for the LLM layer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from adt.models.schemas import LLMMessage


class FakeLLM:
    """Returns a fixed sequence of assistant messages (for integration tests)."""

    def __init__(self, replies: list[LLMMessage]) -> None:
        self._replies = list(replies)
        self._idx = 0
        self.last_usage: dict[str, int] = {}
        self.model = "gpt-4o-mini"

    def chat(
        self,
        messages: Sequence[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_completion_tokens: int | None = None,
    ) -> LLMMessage:
        del messages, tools, max_completion_tokens
        if self._idx >= len(self._replies):
            return LLMMessage(role="assistant", content="")
        r = self._replies[self._idx]
        self._idx += 1
        return r
