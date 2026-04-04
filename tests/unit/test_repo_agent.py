"""Tests for :class:`~adt.agents.repo_agent.RepoAgent`."""

from __future__ import annotations

from adt.agents.repo_agent import RepoAgent
from adt.models.schemas import QueryRequest


def test_repo_agent_tools_and_prompt() -> None:
    """Declared tools and prompt should match the MVP contract."""
    agent = RepoAgent()
    assert agent.tools == [
        "read_repo_tree",
        "read_file",
        "search_code",
        "compare_repos",
    ]
    assert "senior software engineer" in agent.system_prompt.lower()


def test_repo_agent_handle_builds_context(sample_repo_path: str) -> None:
    """``handle`` should assemble context from ``repo_path`` when set."""
    agent = RepoAgent()
    req = QueryRequest(query="what is this?", repo_path=sample_repo_path)
    res = agent.handle(req, context="")
    assert "read_repo_tree" in res.tools_used
    assert len(res.context_summary) > 0
    assert "Runner" in res.answer or "adt ask" in res.answer


def test_repo_agent_name() -> None:
    """Agent id should remain ``repo_agent``."""
    assert RepoAgent().name == "repo_agent"
