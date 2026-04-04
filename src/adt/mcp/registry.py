"""Register tools, enforce per-agent permissions, and export OpenAI function schemas."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolDefinition(BaseModel):
    """Metadata and handler for a callable tool."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str = Field(..., description="Unique tool name used in API calls.")
    description: str = Field(..., description="Human-readable purpose for the model.")
    parameters: dict[str, Any] = Field(
        ...,
        description="JSON Schema object describing the function parameters.",
    )
    allowed_agents: list[str] = Field(
        ...,
        description="Agent names that may invoke this tool.",
    )
    handler: Callable[..., Any] = Field(
        ...,
        description="Python callable executed by the controller.",
    )


class ToolRegistry:
    """In-memory catalog mapping tool names to definitions and permissions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        """Add a tool; raises ``ValueError`` if the name is already registered."""
        if tool_def.name in self._tools:
            msg = f"tool already registered: {tool_def.name}"
            raise ValueError(msg)
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> ToolDefinition:
        """Return a tool definition by name."""
        if name not in self._tools:
            msg = f"unknown tool: {name}"
            raise KeyError(msg)
        return self._tools[name]

    def list_for_agent(self, agent: str) -> list[ToolDefinition]:
        """Tools where ``agent`` appears in ``allowed_agents``."""
        return [t for t in self._tools.values() if agent in t.allowed_agents]

    def to_openai_format(self, agent: str) -> list[dict[str, Any]]:
        """OpenAI Chat Completions ``tools`` payload for one agent."""
        tools: list[dict[str, Any]] = []
        for t in self.list_for_agent(agent):
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                },
            )
        return tools
