"""Supervisor routing rules."""

from __future__ import annotations

import pytest

from adt.core.supervisor import Supervisor
from adt.models.schemas import QueryRequest


@pytest.fixture
def supervisor() -> Supervisor:
    return Supervisor()


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("open issues in the backlog", "project_agent"),
        ("read the project roadmap", "project_agent"),
        ("find papers on RAG", "research_agent"),
        ("literature review", "research_agent"),
        ("explain this repo architecture", "repo_agent"),
        ("where is this function defined", "repo_agent"),
        ("hello world", "repo_agent"),
    ],
)
def test_route_agents(supervisor: Supervisor, query: str, expected: str) -> None:
    req = QueryRequest(query=query)
    out = supervisor.route(req)
    assert out.agent_name == expected
    assert "route" in out.request.options
