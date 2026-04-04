"""Pydantic models for queries, tool calls, LLM messages, and agent responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["system", "user", "assistant", "tool"]


class QueryRequest(BaseModel):
    """User query and optional repository context for a single agent run."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Natural language question or instruction.")
    repo_path: str | None = Field(
        default=None,
        description="Optional filesystem path to a repository root.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary flags and metadata (e.g. routing hints, verbosity).",
    )
    force_agent: str | None = Field(
        default=None,
        description=(
            "When set, skip supervisor routing and use this agent id "
            "(e.g. research_agent, repo_agent)."
        ),
    )


class ToolCall(BaseModel):
    """A function-style tool invocation produced by the model or the framework."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(
        default=None,
        description="Provider-specific tool call id (e.g. OpenAI tool_call id).",
    )
    name: str = Field(..., description="Registered tool name.")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments matching the tool JSON Schema.",
    )
    agent: str = Field(
        default="",
        description="Agent context that issued or owns this call (for auditing).",
    )


class ToolResult(BaseModel):
    """Normalized outcome of executing a single tool."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Tool that was executed.")
    output: str = Field(default="", description="Serialized tool output (often text).")
    success: bool = Field(..., description="Whether execution finished without error.")
    error: str | None = Field(
        default=None,
        description="Error message when success is False.",
    )


class AgentResponse(BaseModel):
    """Final answer returned to the user after a full agent run."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., description="Natural language response shown to the user.")
    tools_used: list[str] = Field(
        default_factory=list,
        description="Names of tools invoked during the run.",
    )
    context_summary: str = Field(
        default="",
        description="Short description of context that was available (for logging).",
    )
    routed_agent: str = Field(
        default="",
        description="Agent id that produced the answer (after routing or force_agent).",
    )


class LLMMessage(BaseModel):
    """One message in an OpenAI-style chat transcript, including optional tool calls."""

    model_config = ConfigDict(extra="forbid")

    role: Role = Field(..., description="Message role in the chat protocol.")
    content: str = Field(
        default="",
        description="Visible text; may be empty when the model emits tool_calls only.",
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None,
        description="Tool calls proposed by an assistant message.",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="Required for role 'tool': links the result to a prior tool call.",
    )

    @model_validator(mode="after")
    def tool_role_requires_call_id(self) -> LLMMessage:
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("tool_call_id is required when role is 'tool'")
        return self

    @field_validator("role")
    @classmethod
    def role_must_be_known(cls, v: str) -> str:
        allowed = {"system", "user", "assistant", "tool"}
        if v not in allowed:
            msg = f"role must be one of {allowed}, got {v!r}"
            raise ValueError(msg)
        return v


class RoutedRequest(BaseModel):
    """Supervisor output: chosen agent and the (possibly enriched) request."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(
        ...,
        description="Agent id: repo_agent, project_agent, or research_agent.",
    )
    request: QueryRequest = Field(
        ...,
        description="Original or enriched request (options may hold routing metadata).",
    )
