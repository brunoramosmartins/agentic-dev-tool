"""Tests for :class:`~adt.agents.project_agent.ProjectAgent`."""

from __future__ import annotations

from adt.agents.project_agent import ProjectAgent
from adt.models.schemas import QueryRequest


def test_project_agent_tools_and_prompt() -> None:
    """Declared tools and role should match the Phase 4 contract."""
    agent = ProjectAgent()
    assert agent.tools == ["read_issues", "read_milestones", "read_markdown"]
    assert "project manager" in agent.system_prompt.lower()


def test_project_agent_handle_lists_tools() -> None:
    """``handle`` should reference Runner and list project tools."""
    agent = ProjectAgent()
    res = agent.handle(QueryRequest(query="milestones?"), context="")
    assert "project_agent" in res.answer
    assert "read_issues" in res.tools_used
    assert res.routed_agent == "project_agent"


def test_project_agent_name() -> None:
    """Stable id should remain ``project_agent``."""
    assert ProjectAgent().name == "project_agent"
