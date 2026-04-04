"""End-to-end runner test with a fake LLM and real tool execution."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.runner import Runner
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.models.schemas import LLMMessage, QueryRequest, ToolCall
from tests.fake_llm import FakeLLM
from tests.unit.test_tools_project import _mock_httpx_client_for_github_get
from tests.unit.test_tools_research import _ARXIV_ATOM, _mock_httpx_client_for_get


def test_runner_tool_loop_then_answer(
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Model requests read_file; executor runs real tool; second turn returns text."""
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
    assert "read_file" in res.tools_used
    assert res.routed_agent == "repo_agent"


@patch("adt.tools.research.httpx.Client")
def test_runner_research_search_papers_then_answer(
    mock_client_cls,
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Research route: ``search_papers`` (mocked arXiv), then the model text."""
    mock_client_cls.return_value = _mock_httpx_client_for_get(_ARXIV_ATOM)
    replies = [
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=[
                ToolCall(
                    id="call_r1",
                    name="search_papers",
                    arguments={"query": "rag", "max_results": 2},
                    agent="research_agent",
                ),
            ],
        ),
        LLMMessage(role="assistant", content="Found relevant work."),
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
    req = QueryRequest(
        query="survey arxiv papers on retrieval augmented generation",
        repo_path=sample_repo_path,
    )
    res = runner.run(req)
    assert res.answer == "Found relevant work."
    assert "search_papers" in res.tools_used
    assert res.routed_agent == "research_agent"


@patch("adt.tools.project.httpx.Client")
def test_runner_project_read_issues_then_answer(
    mock_client_cls,
    tool_registry,
    sample_repo_path: str,
) -> None:
    """Project route runs ``read_issues`` (mocked GitHub) then returns model text."""
    payload = [
        {
            "number": 7,
            "title": "Fix bug",
            "state": "open",
            "user": {"login": "bot"},
            "html_url": "https://github.com/o/r/issues/7",
            "labels": [{"name": "bug"}],
        },
    ]
    mock_client_cls.return_value = _mock_httpx_client_for_github_get(payload)
    replies = [
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=[
                ToolCall(
                    id="call_p1",
                    name="read_issues",
                    arguments={"owner": "o", "repo": "r", "state": "open"},
                    agent="project_agent",
                ),
            ],
        ),
        LLMMessage(role="assistant", content="Issues summarized."),
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
    req = QueryRequest(
        query="summarize open issues in the backlog",
        repo_path=sample_repo_path,
    )
    res = runner.run(req)
    assert res.answer == "Issues summarized."
    assert "read_issues" in res.tools_used
    assert res.routed_agent == "project_agent"


def test_runner_max_iterations_stops(
    tool_registry,
) -> None:
    """LLM always requests a tool -> runner hits iteration cap."""
    tc = ToolCall(
        id="loop",
        name="read_repo_tree",
        arguments={"path": ".", "max_depth": 1},
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
