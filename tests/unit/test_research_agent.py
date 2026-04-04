"""Tests for :class:`~adt.agents.research_agent.ResearchAgent`."""

from __future__ import annotations

from adt.agents.research_agent import ResearchAgent
from adt.models.schemas import QueryRequest


def test_research_agent_tools_and_prompt() -> None:
    """Declared tools and role should match the Phase 3 contract."""
    agent = ResearchAgent()
    assert agent.tools == ["search_papers", "fetch_article"]
    assert "technical researcher" in agent.system_prompt.lower()


def test_research_agent_handle_lists_tools() -> None:
    """``handle`` should mention Runner and list research tools."""
    agent = ResearchAgent()
    res = agent.handle(QueryRequest(query="papers?"), context="")
    assert "research_agent" in res.answer
    assert "search_papers" in res.tools_used
    assert res.routed_agent == "research_agent"


def test_research_agent_name() -> None:
    """Stable id should remain ``research_agent``."""
    assert ResearchAgent().name == "research_agent"
