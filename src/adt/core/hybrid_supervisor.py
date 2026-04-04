"""Supervisor that prefers a cheap LLM classifier, falling back to keyword rules."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from adt.core.supervisor import Supervisor
from adt.models.schemas import QueryRequest, RoutedRequest

if TYPE_CHECKING:
    from adt.core.llm import LLMClient

logger = logging.getLogger(__name__)

_VALID_AGENTS = frozenset({"repo_agent", "project_agent", "research_agent"})

_ROUTER_SYSTEM = """You route user messages to exactly one agent id.
Agents:
- repo_agent: local codebase, files, implementation, architecture, debugging code
- project_agent: GitHub issues, milestones, roadmap, sprint, backlog, kanban
- research_agent: academic papers, arxiv, DOI, literature review, publications

Reply with a single JSON object only, no markdown: {"agent":"<id>"}
where <id> is one of: repo_agent, project_agent, research_agent."""


class HybridSupervisor:
    """Try LLM JSON classification; on failure use :class:`Supervisor` rules."""

    def __init__(
        self,
        *,
        llm: LLMClient | None,
        use_llm_routing: bool = True,
        routing_model: str | None = None,
    ) -> None:
        self._llm = llm
        self._use = use_llm_routing and llm is not None
        self._routing_model = routing_model or (
            llm.model if llm is not None else "gpt-4o-mini"
        )
        self._rules = Supervisor()

    def route(self, request: QueryRequest) -> RoutedRequest:
        """Classify intent; fall back to keyword routing when LLM is off or errors."""
        if not self._use or self._llm is None:
            return self._rules.route(request)

        agent = _llm_classify_agent(
            self._llm,
            request.query,
            model=self._routing_model,
        )
        if agent is None:
            return self._rules.route(request)

        enriched = request.model_copy(deep=True)
        enriched.options = {**enriched.options, "route": "llm_classifier"}
        return RoutedRequest(agent_name=agent, request=enriched)


def _llm_classify_agent(
    llm: LLMClient,
    query: str,
    *,
    model: str,
) -> str | None:
    """Return agent id or None if parsing fails."""
    try:
        raw = llm.complete_json_object(
            system=_ROUTER_SYSTEM,
            user=query.strip()[:4000],
            model=model,
            max_completion_tokens=80,
        )
    except Exception as exc:
        logger.info(
            "llm routing failed, using rules: %s",
            exc,
            extra={"adt": {"event": "llm_route_fallback", "error": str(exc)}},
        )
        return None

    agent = raw.get("agent") if isinstance(raw, dict) else None
    if not isinstance(agent, str):
        return None
    agent = agent.strip()
    if agent not in _VALID_AGENTS:
        return None
    return agent


def parse_router_json(content: str) -> dict[str, Any] | None:
    """Parse model output for tests (exported for mocking layers)."""
    text = content.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
