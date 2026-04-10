"""Integration test for supervised mode end-to-end through Runner."""

from __future__ import annotations

from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.runner import Runner
from adt.core.supervised_supervisor import parse_supervised_response
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.models.schemas import LLMMessage, QueryRequest
from adt.tracing.context import TraceContext
from tests.fake_llm import FakeLLM

_SAMPLE_JSON = """{
    "problem_summary": "Implement binary search",
    "current_step": {
        "step_number": 1,
        "goal": "Define the function signature",
        "requirements": ["accept sorted list", "return index or -1"],
        "hints": ["think about parameter types"],
        "questions": ["why does the list need to be sorted?"]
    },
    "total_steps": 4,
    "progress_note": "next: implement the base case"
}"""


def test_supervised_mode_bypasses_tool_loop(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Supervised mode calls LLM once, no tool execution, returns structured JSON."""
    replies = [LLMMessage(role="assistant", content=_SAMPLE_JSON)]
    fake = FakeLLM(replies)
    supervisor = Supervisor()
    context = ContextBuilder()
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(supervisor, fake, context, executor, tool_registry, agents)

    req = QueryRequest(
        query="Teach me binary search",
        repo_path=sample_repo_path,
        mode="supervised",
        level="beginner",
    )
    res = runner.run(req)

    assert res.routed_agent == "supervised"
    assert res.tools_used == []

    parsed = parse_supervised_response(res.answer)
    assert parsed is not None
    assert parsed.problem_summary == "Implement binary search"
    assert parsed.current_step.step_number == 1
    assert parsed.total_steps == 4


def test_supervised_mode_with_tracing(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Supervised mode emits trace events (supervised_start, llm_call, completed)."""
    trace = TraceContext()
    replies = [LLMMessage(role="assistant", content=_SAMPLE_JSON)]
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

    req = QueryRequest(
        query="Teach me binary search",
        repo_path=sample_repo_path,
        mode="supervised",
    )
    runner.run(req)

    event_types = [e.event_type for e in trace.events]
    assert "supervised_start" in event_types
    assert "llm_call" in event_types
    assert "request_completed" in event_types
    # No tool events since supervised mode does not call tools
    assert "tool_call" not in event_types


def test_execution_mode_still_works(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Execution mode (default) still uses the agent routing + tool loop."""
    replies = [LLMMessage(role="assistant", content="direct answer")]
    fake = FakeLLM(replies)
    supervisor = Supervisor()
    context = ContextBuilder()
    executor = ExecutionController(tool_registry)
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(supervisor, fake, context, executor, tool_registry, agents)

    req = QueryRequest(query="explain this", repo_path=sample_repo_path)
    res = runner.run(req)
    assert res.routed_agent == "repo_agent"
    assert res.answer == "direct answer"
