"""Unit tests for TraceRenderer."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from adt.tracing.context import TraceContext
from adt.tracing.renderer import TraceRenderer


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=120)


def test_renderer_outputs_trace_panel() -> None:
    con = _make_console()
    trace = TraceContext(trace_id="render-test")
    trace.emit("supervisor", "routing_decision", agent="repo_agent")
    trace.emit("runner", "llm_call", iteration=0, model="gpt-4o-mini")
    trace.emit("runner", "request_completed", total_elapsed_ms=42.5)

    renderer = TraceRenderer(con)
    renderer.render(trace, model="gpt-4o-mini")

    output = con.file.getvalue()  # type: ignore[union-attr]
    assert "render-test" in output
    assert "routing_decision" in output
    assert "llm_call" in output
    assert "request_completed" in output


def test_renderer_shows_cost_when_tokens_present() -> None:
    con = _make_console()
    trace = TraceContext(trace_id="cost-test")
    trace.add_token_usage(prompt_tokens=1000, completion_tokens=500)
    trace.emit("runner", "llm_call", iteration=0)

    renderer = TraceRenderer(con)
    renderer.render(trace, model="gpt-4o-mini")

    output = con.file.getvalue()  # type: ignore[union-attr]
    assert "Cost estimate" in output
    assert "USD" in output


def test_renderer_no_cost_when_zero_tokens() -> None:
    con = _make_console()
    trace = TraceContext(trace_id="no-cost")
    trace.emit("runner", "llm_call", iteration=0)

    renderer = TraceRenderer(con)
    renderer.render(trace, model="gpt-4o-mini")

    output = con.file.getvalue()  # type: ignore[union-attr]
    assert "Cost estimate" not in output
