"""Pydantic model collecting every parameter for :func:`build_runner`.

Replaces the 13+ keyword arguments with a single validated object,
making the call-site readable and enabling config-driven construction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunnerConfig(BaseModel):
    """All parameters needed to construct a :class:`~adt.core.runner.Runner`."""

    repo_roots: dict[str, Path] | Path
    markdown_root: Path | None = None
    primary_repo_key: str | None = None
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    github_token: str | None = None
    max_tool_iterations: int = 5
    use_context_cache: bool = True
    context_cache_ttl: float | None = None
    token_budget_total: int | None = None
    use_llm_routing: bool = True
    routing_model: str | None = None
    agent_chain: list[str] = Field(default_factory=list)
    trace: Any = None  # TraceContext | None — Any avoids circular import

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_legacy(
        cls, repo_roots: Path | dict[str, Path], **kwargs: Any
    ) -> RunnerConfig:
        """Build from the legacy positional + keyword calling convention."""
        return cls(repo_roots=repo_roots, **kwargs)
