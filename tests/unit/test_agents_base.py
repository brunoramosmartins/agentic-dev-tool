"""Base agent contract."""

from __future__ import annotations

import pytest

from adt.agents.base import BaseAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.models.schemas import AgentResponse, QueryRequest


def test_cannot_instantiate_base() -> None:
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore[abstract,misc]


def test_repo_agent_name_and_handle() -> None:
    a = RepoAgent()
    assert a.name == "repo_agent"
    r = a.handle(QueryRequest(query="q"), context="ctx")
    assert isinstance(r, AgentResponse)
    assert "repo_agent" in r.answer
    assert r.tools_used


def test_research_agent_name_and_handle() -> None:
    """Research agent should expose a stable id and non-empty tool list."""
    a = ResearchAgent()
    assert a.name == "research_agent"
    r = a.handle(QueryRequest(query="q"), context="ctx")
    assert isinstance(r, AgentResponse)
    assert "research_agent" in r.answer
    assert r.tools_used
