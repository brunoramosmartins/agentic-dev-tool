"""Test doubles for the LLM layer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from adt.models.schemas import LLMMessage


class FakeLLM:
    """Returns a fixed sequence of assistant messages (for integration tests)."""

    def __init__(
        self,
        replies: list[LLMMessage],
        *,
        router_json: dict[str, Any] | None = None,
    ) -> None:
        self._replies = list(replies)
        self._idx = 0
        self.last_usage: dict[str, int] = {}
        self.model = "gpt-4o-mini"
        self._router_json: dict[str, Any] = dict(router_json or {"agent": "repo_agent"})

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

    def complete_json_object(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_completion_tokens: int = 120,
    ) -> dict[str, Any]:
        """Return fixed JSON for routing tests."""
        del system, user, model, max_completion_tokens
        self.last_usage = {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        }
        return dict(self._router_json)
