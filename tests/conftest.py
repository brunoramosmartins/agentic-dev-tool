"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from adt.bootstrap import register_repo_tools, register_research_tools
from adt.mcp.registry import ToolRegistry


@pytest.fixture
def tool_registry(sample_repo_path: str) -> ToolRegistry:
    """A tool registry with repo tools bound to the sample fixture repository."""
    reg = ToolRegistry()
    register_repo_tools(reg, Path(sample_repo_path))
    register_research_tools(reg)
    return reg


@pytest.fixture
def sample_repo_path() -> str:
    """Absolute path to the minimal sample repository under ``tests/fixtures``."""
    return str(Path(__file__).resolve().parent / "fixtures" / "sample_repo")
