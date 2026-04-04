"""Technical research agent (stub for Phase 1)."""

from __future__ import annotations

from adt.agents.base import BaseAgent
from adt.models.schemas import AgentResponse, QueryRequest


class ResearchAgent(BaseAgent):
    """Literature and article workflows; Phase 3 adds arXiv and fetch tools."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are a technical researcher. "
            "Use search tools when available to ground answers."
        )

    @property
    def tools(self) -> list[str]:
        return []

    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        return AgentResponse(
            answer=f"(stub research_agent) Query: {request.query!r}",
            tools_used=[],
            context_summary=context[:500],
        )
