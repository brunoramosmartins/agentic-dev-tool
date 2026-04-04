"""Repository analysis agent (stub implementation for Phase 1)."""

from __future__ import annotations

from adt.agents.base import BaseAgent
from adt.models.schemas import AgentResponse, QueryRequest


class RepoAgent(BaseAgent):
    """Analyzes local repositories; Phase 2 adds real repo tools and prompts."""

    @property
    def system_prompt(self) -> str:
        return (
            "You are a senior engineer analyzing a codebase. "
            "Answer clearly using tools when they are available."
        )

    @property
    def tools(self) -> list[str]:
        return ["echo"]

    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        return AgentResponse(
            answer=f"(stub repo_agent) Query: {request.query!r}",
            tools_used=[],
            context_summary=context[:500],
        )
