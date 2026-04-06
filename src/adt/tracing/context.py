"""Trace context that accumulates events for a single request."""

from __future__ import annotations

import time
import uuid
from typing import Any

from adt.tracing.events import TraceEvent


class TraceContext:
    """Collects :class:`TraceEvent` instances for one ``trace_id``."""

    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id: str = trace_id or uuid.uuid4().hex[:16]
        self.events: list[TraceEvent] = []
        self._start: float = time.perf_counter()
        self._prompt_tokens: int = 0
        self._completion_tokens: int = 0

    def emit(
        self,
        component: str,
        event_type: str,
        *,
        iteration: int | None = None,
        **data: Any,
    ) -> TraceEvent:
        """Create and record a trace event, returning it for inspection."""
        event = TraceEvent(
            trace_id=self.trace_id,
            component=component,
            event_type=event_type,
            iteration=iteration,
            data=data,
        )
        self.events.append(event)
        return event

    def add_token_usage(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Accumulate token counts from an LLM call."""
        self._prompt_tokens += prompt_tokens
        self._completion_tokens += completion_tokens

    @property
    def cumulative_tokens(self) -> dict[str, int]:
        """Return accumulated prompt/completion/total token counts."""
        return {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
        }

    def elapsed_ms(self) -> float:
        """Milliseconds since this trace was created."""
        return round((time.perf_counter() - self._start) * 1000, 2)
