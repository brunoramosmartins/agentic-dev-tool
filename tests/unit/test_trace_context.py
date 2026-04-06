"""Unit tests for TraceContext."""

from __future__ import annotations

import time

from adt.tracing.context import TraceContext


def test_trace_context_auto_id() -> None:
    ctx = TraceContext()
    assert len(ctx.trace_id) == 16
    assert ctx.events == []


def test_trace_context_custom_id() -> None:
    ctx = TraceContext(trace_id="custom-123")
    assert ctx.trace_id == "custom-123"


def test_emit_creates_event() -> None:
    ctx = TraceContext(trace_id="t1")
    ev = ctx.emit("runner", "llm_call", iteration=1, model="gpt-4o-mini")
    assert ev.trace_id == "t1"
    assert ev.component == "runner"
    assert ev.event_type == "llm_call"
    assert ev.iteration == 1
    assert ev.data["model"] == "gpt-4o-mini"
    assert len(ctx.events) == 1


def test_emit_multiple_events() -> None:
    ctx = TraceContext()
    ctx.emit("supervisor", "routing_decision", agent="repo_agent")
    ctx.emit("context", "context_build", files=5)
    ctx.emit("runner", "llm_call", iteration=0)
    assert len(ctx.events) == 3
    assert ctx.events[0].event_type == "routing_decision"
    assert ctx.events[2].event_type == "llm_call"


def test_add_token_usage() -> None:
    ctx = TraceContext()
    ctx.add_token_usage(prompt_tokens=100, completion_tokens=50)
    ctx.add_token_usage(prompt_tokens=200, completion_tokens=100)
    tok = ctx.cumulative_tokens
    assert tok["prompt_tokens"] == 300
    assert tok["completion_tokens"] == 150
    assert tok["total_tokens"] == 450


def test_cumulative_tokens_default_zero() -> None:
    ctx = TraceContext()
    tok = ctx.cumulative_tokens
    assert tok == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def test_elapsed_ms() -> None:
    ctx = TraceContext()
    time.sleep(0.02)
    ms = ctx.elapsed_ms()
    assert ms >= 5  # at least ~20ms but allow generous slack
