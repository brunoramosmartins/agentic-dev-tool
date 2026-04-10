"""Pydantic models for queries, tool calls, LLM messages, and agent responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["system", "user", "assistant", "tool"]


Mode = Literal["execution", "supervised"]
Level = Literal["beginner", "intermediate", "advanced"]
Severity = Literal["error", "warning", "suggestion"]
Assessment = Literal["needs_work", "on_track", "excellent"]


class QueryRequest(BaseModel):
    """User query and optional repository context for a single agent run."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Natural language question or instruction.")
    mode: Mode = Field(
        default="execution",
        description="Operational mode: execution (default) or supervised (guided).",
    )
    level: Level = Field(
        default="intermediate",
        description="Difficulty level for supervised mode guidance.",
    )
    repo_path: str | None = Field(
        default=None,
        description=(
            "Primary local directory: first repository root and default markdown "
            "root for project_agent."
        ),
    )
    additional_repo_paths: list[str] = Field(
        default_factory=list,
        description="Extra local repository roots (multi-repo sessions).",
    )
    github_owner: str | None = Field(
        default=None,
        description="With github_repo, default GitHub API owner login.",
    )
    github_repo: str | None = Field(
        default=None,
        description="With github_owner, default GitHub API repository name.",
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

    @model_validator(mode="after")
    def github_owner_repo_pair(self) -> QueryRequest:
        """Require ``github_owner`` and ``github_repo`` to be set together."""
        has_o = self.github_owner is not None
        has_r = self.github_repo is not None
        if has_o ^ has_r:
            msg = "github_owner and github_repo must both be set or both omitted."
            raise ValueError(msg)
        return self

    def effective_repo_paths(self) -> list[str]:
        """Return unique local roots in order (primary ``repo_path`` first)."""
        out: list[str] = []
        if self.repo_path:
            out.append(self.repo_path)
        for p in self.additional_repo_paths:
            if p and p not in out:
                out.append(p)
        return out


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


class SupervisedStep(BaseModel):
    """A single guided step in the supervised learning flow."""

    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(..., description="1-based index of this step.")
    goal: str = Field(..., description="What the user should achieve in this step.")
    requirements: list[str] = Field(
        default_factory=list,
        description="Concrete deliverables or acceptance criteria.",
    )
    hints: list[str] = Field(
        default_factory=list,
        description="Optional nudges without revealing the solution.",
    )
    questions: list[str] = Field(
        default_factory=list,
        description="Reflective questions to deepen understanding.",
    )


class SupervisedResponse(BaseModel):
    """Structured response from supervised mode with the current guided step."""

    model_config = ConfigDict(extra="forbid")

    problem_summary: str = Field(
        ..., description="Concise restatement of the problem to solve."
    )
    current_step: SupervisedStep = Field(
        ..., description="The step the user should work on now."
    )
    total_steps: int = Field(..., description="Total number of planned steps.", ge=1)
    progress_note: str = Field(
        default="",
        description="Brief, specific note on what comes next (not generic praise).",
    )


class CodeIssue(BaseModel):
    """A specific issue found in the user's code during supervised review."""

    model_config = ConfigDict(extra="forbid")

    line: int | None = Field(
        default=None,
        description="1-based line number where the issue is; None if file-wide.",
    )
    severity: Severity = Field(
        ...,
        description="error (blocks correctness), warning (risky), suggestion (polish).",
    )
    description: str = Field(..., description="What is wrong, in concrete terms.")
    fix_hint: str = Field(
        default="",
        description="Nudge toward the fix without revealing the full solution.",
    )


class ReviewFeedback(BaseModel):
    """Structured feedback from a supervised code review."""

    model_config = ConfigDict(extra="forbid")

    issues: list[CodeIssue] = Field(
        default_factory=list,
        description="Specific issues found in the submitted code.",
    )
    improvements: list[str] = Field(
        default_factory=list,
        description="Non-blocking improvements the user could apply next.",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="What the user did well (specific, not generic praise).",
    )
    next_step: str = Field(
        default="",
        description="Concrete action the user should take after addressing feedback.",
    )
    overall_assessment: Assessment = Field(
        ...,
        description="High-level verdict: needs_work, on_track, or excellent.",
    )
