"""Abstract base type for all specialized agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from adt.models.schemas import AgentResponse, QueryRequest


class BaseAgent(ABC):
    """Contract: system prompt, declared tool names, and a handle entrypoint.

    Phase 1 provides stubs; Phase 2+ flesh out ``handle`` and real tool wiring.
    The :class:`~adt.core.runner.Runner` uses ``system_prompt`` and ``tools`` for
    the LLM loop; ``handle`` remains available for higher-level orchestration.
    """

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Instructions injected as the system message for this agent."""

    @property
    @abstractmethod
    def tools(self) -> list[str]:
        """Names of tools this agent may call (must exist in the registry)."""

    @abstractmethod
    def handle(self, request: QueryRequest, context: str) -> AgentResponse:
        """Produce a response given the user request and assembled context text."""

    @property
    def name(self) -> str:
        """Stable agent id from the class name (``RepoAgent`` → ``repo_agent``)."""
        stem = self.__class__.__name__.removesuffix("Agent").lower()
        return f"{stem}_agent"
