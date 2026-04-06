"""Structured trace event model for agent observability."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """Single structured event emitted during a traced request."""

    trace_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    component: str
    event_type: str
    iteration: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)
