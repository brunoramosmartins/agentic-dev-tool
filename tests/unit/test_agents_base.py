"""Base agent contract."""

from __future__ import annotations

import pytest

from adt.agents.base import BaseAgent
from adt.agents.repo_agent import RepoAgent
from adt.models.schemas import AgentResponse, QueryRequest


def test_cannot_instantiate_base() -> None:
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore[abstract,misc]


def test_repo_agent_name_and_handle() -> None:
    a = RepoAgent()
    assert a.name == "repo_agent"
    r = a.handle(QueryRequest(query="q"), context="ctx")
    assert isinstance(r, AgentResponse)
    assert "stub" in r.answer
