"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from adt.mcp.registry import ToolDefinition, ToolRegistry


def _echo_handler(message: str) -> str:
    return f"echo:{message}"


@pytest.fixture
def tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        ToolDefinition(
            name="echo",
            description="Echo a string back to the model.",
            parameters={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=_echo_handler,
        ),
    )
    return reg


@pytest.fixture
def sample_repo_path() -> str:
    return str(Path(__file__).resolve().parent / "fixtures" / "sample_repo")
