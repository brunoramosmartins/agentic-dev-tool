"""LLM routing with rule fallback."""

from __future__ import annotations

from adt.core.hybrid_supervisor import HybridSupervisor, parse_router_json
from adt.core.supervisor import Supervisor
from adt.models.schemas import QueryRequest
from tests.fake_llm import FakeLLM


class _ExplodingRouter:
    """Stub LLM that fails JSON routing."""

    model = "gpt-4o-mini"

    def complete_json_object(self, **kwargs: object) -> dict[str, str]:
        del kwargs
        msg = "simulated router failure"
        raise RuntimeError(msg)


def test_hybrid_uses_llm_when_enabled() -> None:
    llm = FakeLLM([], router_json={"agent": "project_agent"})
    sup = HybridSupervisor(llm=llm, use_llm_routing=True, routing_model="gpt-4o-mini")
    req = QueryRequest(query="hello world")
    out = sup.route(req)
    assert out.agent_name == "project_agent"
    assert out.request.options.get("route") == "llm_classifier"


def test_hybrid_falls_back_when_llm_disabled() -> None:
    llm = FakeLLM([], router_json={"agent": "project_agent"})
    sup = HybridSupervisor(llm=llm, use_llm_routing=False)
    req = QueryRequest(query="hello world")
    out = sup.route(req)
    assert out.agent_name == "repo_agent"
    assert out.request.options.get("route") == "default"


def test_hybrid_falls_back_when_llm_raises() -> None:
    sup = HybridSupervisor(llm=_ExplodingRouter(), use_llm_routing=True)
    req = QueryRequest(query="hello world")
    out = sup.route(req)
    assert out.agent_name == "repo_agent"
    assert out.request.options.get("route") == "default"


def test_parse_router_json() -> None:
    raw = '{"agent":"research_agent"}'
    assert parse_router_json(raw) == {"agent": "research_agent"}
    assert parse_router_json("") is None


def test_rules_match_supervisor_keyword() -> None:
    """Keyword routing should match plain Supervisor."""
    hybrid = HybridSupervisor(llm=None, use_llm_routing=True)
    plain = Supervisor()
    q = QueryRequest(query="list open issues")
    assert hybrid.route(q).agent_name == plain.route(q).agent_name
