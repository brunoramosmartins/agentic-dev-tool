"""Integration test verifying full trace event sequence with FakeLLM."""

from __future__ import annotations

from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.runner import Runner
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.models.schemas import LLMMessage, QueryRequest, ToolCall
from adt.tracing.context import TraceContext
from adt.tracing.cost import CostEstimator
from tests.fake_llm import FakeLLM


def test_traced_tool_loop_emits_full_event_sequence(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """TraceContext collects routing, llm_call, tool_call, and request_completed."""
    trace = TraceContext(trace_id="test-trace-001")
    replies = [
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="read_file",
                    arguments={"path": "main.py", "max_lines": 50},
                    agent="repo_agent",
                ),
            ],
        ),
        LLMMessage(role="assistant", content="File explained."),
    ]
    fake = FakeLLM(replies)
    supervisor = Supervisor(trace=trace)
    context = ContextBuilder(trace=trace)
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        supervisor,
        fake,
        context,
        executor,
        tool_registry,
        agents,
        max_tool_iterations=5,
        trace=trace,
    )
    req = QueryRequest(query="explain this code", repo_path=sample_repo_path)
    res = runner.run(req)

    assert res.answer == "File explained."
    assert trace.trace_id == "test-trace-001"

    event_types = [e.event_type for e in trace.events]

    # Supervisor emits routing_decision
    assert "routing_decision" in event_types

    # Runner emits llm_call for each LLM interaction
    assert event_types.count("llm_call") == 2

    # Runner emits tool_call after executing read_file
    assert "tool_call" in event_types
    tool_ev = next(e for e in trace.events if e.event_type == "tool_call")
    assert tool_ev.data["tool"] == "read_file"
    assert tool_ev.data["success"] is True

    # Final request_completed event
    assert "request_completed" in event_types
    done_ev = next(e for e in trace.events if e.event_type == "request_completed")
    assert done_ev.data["agent"] == "repo_agent"
    assert done_ev.data["total_elapsed_ms"] > 0

    # elapsed_ms works
    assert trace.elapsed_ms() > 0


def test_traced_direct_answer_no_tools(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """When the model answers immediately, trace still has routing + llm_call."""
    trace = TraceContext()
    replies = [LLMMessage(role="assistant", content="Direct answer.")]
    fake = FakeLLM(replies)
    supervisor = Supervisor(trace=trace)
    context = ContextBuilder(trace=trace)
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        supervisor, fake, context, executor, tool_registry, agents, trace=trace
    )
    req = QueryRequest(query="explain this code", repo_path=sample_repo_path)
    res = runner.run(req)

    assert res.answer == "Direct answer."
    event_types = [e.event_type for e in trace.events]
    assert "routing_decision" in event_types
    assert "llm_call" in event_types
    assert "request_completed" in event_types
    assert "tool_call" not in event_types


def test_cost_estimator_from_trace_tokens() -> None:
    """CostEstimator works with cumulative token data from TraceContext."""
    trace = TraceContext()
    trace.add_token_usage(prompt_tokens=1000, completion_tokens=500)
    trace.add_token_usage(prompt_tokens=2000, completion_tokens=1000)
    tokens = trace.cumulative_tokens
    cost = CostEstimator.estimate(
        "gpt-4o-mini", tokens["prompt_tokens"], tokens["completion_tokens"]
    )
    assert cost.prompt_tokens == 3000
    assert cost.completion_tokens == 1500
    assert cost.total_cost_usd > 0
