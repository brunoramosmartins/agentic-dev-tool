"""OpenAI-compatible chat client with retries and usage tracking."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from typing import Any

from openai import APIStatusError, OpenAI

from adt.models.schemas import LLMMessage, ToolCall

logger = logging.getLogger(__name__)

_RETRY_STATUS = frozenset({429, 500, 502, 503})


def _messages_to_openai(messages: Sequence[LLMMessage]) -> list[dict[str, Any]]:
    """Convert internal :class:`LLMMessage` objects to OpenAI chat message dicts."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m.tool_call_id or "",
                    "content": m.content,
                },
            )
            continue

        entry: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.id or "",
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in m.tool_calls
            ]
        out.append(entry)
    return out


def _tool_calls_from_openai(raw: Any) -> list[ToolCall] | None:
    """Parse provider tool call objects into :class:`ToolCall` models."""
    if not raw:
        return None
    calls: list[ToolCall] = []
    for tc in raw:
        fn = tc.function
        try:
            args = json.loads(fn.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append(
            ToolCall(
                id=tc.id,
                name=fn.name,
                arguments=args if isinstance(args, dict) else {},
            ),
        )
    return calls or None


class LLMClient:
    """Thin wrapper around the OpenAI chat completions API."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        *,
        max_retries: int = 3,
        timeout: float = 120.0,
        client: OpenAI | None = None,
    ) -> None:
        self._model = model
        self._max_retries = max(1, max_retries)
        self._client = client or OpenAI(api_key=api_key, timeout=timeout)
        self._last_usage: dict[str, int] = {}

    @property
    def model(self) -> str:
        """Configured chat model name."""
        return self._model

    @property
    def last_usage(self) -> dict[str, int]:
        """Token usage from the most recent successful API call."""
        return dict(self._last_usage)

    def chat(
        self,
        messages: Sequence[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_completion_tokens: int | None = None,
    ) -> LLMMessage:
        """Send chat messages and return the assistant (or tool-bearing) reply."""
        payload = _messages_to_openai(messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": payload,
        }
        if tools:
            kwargs["tools"] = tools
        if max_completion_tokens is not None:
            kwargs["max_tokens"] = max_completion_tokens

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                completion = self._client.chat.completions.create(**kwargs)
                choice = completion.choices[0].message
                usage = completion.usage
                if usage is not None:
                    self._last_usage = {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    }
                    logger.info(
                        "",
                        extra={"adt": {"event": "llm_usage", **self._last_usage}},
                    )
                tool_calls = _tool_calls_from_openai(choice.tool_calls)
                return LLMMessage(
                    role="assistant",
                    content=choice.content or "",
                    tool_calls=tool_calls,
                )
            except APIStatusError as exc:
                last_error = exc
                code = getattr(exc, "status_code", None)
                if code in _RETRY_STATUS and attempt < self._max_retries - 1:
                    delay = 2**attempt
                    logger.warning(
                        "",
                        extra={
                            "adt": {
                                "event": "llm_retry",
                                "attempt": attempt + 1,
                                "status_code": code,
                                "sleep_s": delay,
                            },
                        },
                    )
                    time.sleep(delay)
                    continue
                raise
        assert last_error is not None
        raise last_error

    def complete_json_object(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_completion_tokens: int = 120,
    ) -> dict[str, Any]:
        """Single-turn JSON object completion (routing, tiny structured outputs)."""
        use_model = model or self._model
        kwargs: dict[str, Any] = {
            "model": use_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_completion_tokens,
            "response_format": {"type": "json_object"},
        }
        completion = self._client.chat.completions.create(**kwargs)
        choice = completion.choices[0].message
        usage = completion.usage
        if usage is not None:
            self._last_usage = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
        text = (choice.content or "").strip()
        if not text:
            return {}
        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = "router returned non-json"
            raise ValueError(msg) from exc
        return parsed if isinstance(parsed, dict) else {}
