"""Unit tests for TraceEvent model."""

from __future__ import annotations

from datetime import timezone

from adt.tracing.events import TraceEvent


def test_trace_event_defaults() -> None:
    ev = TraceEvent(trace_id="abc", component="runner", event_type="llm_call")
    assert ev.trace_id == "abc"
    assert ev.component == "runner"
    assert ev.event_type == "llm_call"
    assert ev.iteration is None
    assert ev.data == {}
    assert ev.timestamp.tzinfo == timezone.utc


def test_trace_event_with_data() -> None:
    ev = TraceEvent(
        trace_id="x",
        component="supervisor",
        event_type="routing_decision",
        iteration=0,
        data={"agent": "repo_agent", "confidence": 0.95},
    )
    assert ev.iteration == 0
    assert ev.data["agent"] == "repo_agent"


def test_trace_event_serialization_roundtrip() -> None:
    ev = TraceEvent(
        trace_id="rt",
        component="context",
        event_type="context_build",
        data={"files": 10},
    )
    raw = ev.model_dump()
    restored = TraceEvent.model_validate(raw)
    assert restored.trace_id == ev.trace_id
    assert restored.data == ev.data
