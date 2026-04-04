"""Project and issue management agent (stub for Phase 1)."""

from __future__ import annotations

from adt.agents.base import BaseAgent
from adt.models.schemas import AgentResponse, QueryRequest


class ProjectAgent(BaseAgent):
    """GitHub-centric project insights; Phase 4 adds API-backed tools."""

    @property
    def system_prompt(self) -> str:
        """Return a short stub prompt until GitHub tools land in Phase 4."""
        return (
            "You are a technical project manager. "
            "Summarize issues and milestones when tools exist."
        )

    @property
    def tools(self) -> list[str]:
        """No registered tools yet for this agent."""
        return []

    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        """Echo the query as a stub response for tests and future orchestration."""
        return AgentResponse(
            answer=f"(stub project_agent) Query: {request.query!r}",
            tools_used=[],
            context_summary=context[:500],
        )
