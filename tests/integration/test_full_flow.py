"""End-to-end runner test with a fake LLM and real tool execution."""

from __future__ import annotations

from pathlib import Path

from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.runner import Runner
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.models.schemas import LLMMessage, QueryRequest, ToolCall
from tests.fake_llm import FakeLLM


def test_runner_tool_loop_then_answer(
    tool_registry,
    sample_repo_path: str,
) -> None:
    replies = [
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="echo",
                    arguments={"message": "ping"},
                    agent="repo_agent",
                ),
            ],
        ),
        LLMMessage(role="assistant", content="Final synthesis."),
    ]
    fake = FakeLLM(replies)
    supervisor = Supervisor()
    context = ContextBuilder()
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
    )
    req = QueryRequest(query="explain this file tree", repo_path=sample_repo_path)
    res = runner.run(req)
    assert res.answer == "Final synthesis."
    assert "echo" in res.tools_used


def test_runner_max_iterations_stops(
    tool_registry,
) -> None:
    """LLM always requests a tool -> runner hits iteration cap."""
    tc = ToolCall(
        id="loop",
        name="echo",
        arguments={"message": "again"},
        agent="repo_agent",
    )
    replies = [
        LLMMessage(role="assistant", content="", tool_calls=[tc]),
    ] * 3
    fake = FakeLLM(replies)
    supervisor = Supervisor()
    context = ContextBuilder()
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
        max_tool_iterations=3,
    )
    repo = Path(__file__).resolve().parents[1] / "fixtures" / "sample_repo"
    res = runner.run(
        QueryRequest(query="explain the repo", repo_path=str(repo)),
    )
    assert "maximum tool iterations" in res.answer
