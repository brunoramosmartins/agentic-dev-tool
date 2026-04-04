"""Tool registry registration and OpenAI export."""

from __future__ import annotations

import pytest

from adt.mcp.registry import ToolDefinition, ToolRegistry


def test_register_get_list() -> None:
    reg = ToolRegistry()

    def add(a: int, b: int) -> int:
        return a + b

    reg.register(
        ToolDefinition(
            name="add",
            description="Add integers.",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=add,
        ),
    )
    assert reg.get("add").name == "add"
    listed = reg.list_for_agent("repo_agent")
    assert len(listed) == 1
    assert listed[0].name == "add"
    assert reg.list_for_agent("project_agent") == []


def test_duplicate_register_raises() -> None:
    reg = ToolRegistry()

    def fn() -> str:
        return "x"

    td = ToolDefinition(
        name="dup",
        description="d",
        parameters={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        allowed_agents=["repo_agent"],
        handler=fn,
    )
    reg.register(td)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(td)


def test_to_openai_format() -> None:
    reg = ToolRegistry()

    def noop() -> str:
        return "ok"

    reg.register(
        ToolDefinition(
            name="noop",
            description="No parameters.",
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent", "project_agent"],
            handler=noop,
        ),
    )
    fmt = reg.to_openai_format("project_agent")
    assert fmt[0]["type"] == "function"
    assert fmt[0]["function"]["name"] == "noop"
