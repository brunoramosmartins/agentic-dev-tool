"""Execution controller validation and error handling."""

from __future__ import annotations

import pytest

from adt.mcp.executor import ExecutionController
from adt.mcp.registry import ToolDefinition, ToolRegistry
from adt.models.schemas import ToolCall


@pytest.fixture
def reg_with_tool() -> ToolRegistry:
    reg = ToolRegistry()

    def double(n: int) -> int:
        return n * 2

    reg.register(
        ToolDefinition(
            name="double",
            description="Double an integer.",
            parameters={
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=double,
        ),
    )
    return reg


def test_execute_success(reg_with_tool: ToolRegistry) -> None:
    ex = ExecutionController(reg_with_tool)
    res = ex.execute(
        ToolCall(name="double", arguments={"n": 3}, agent="repo_agent"),
    )
    assert res.success
    assert res.output == "6"


def test_execute_validation_error(reg_with_tool: ToolRegistry) -> None:
    ex = ExecutionController(reg_with_tool)
    res = ex.execute(
        ToolCall(name="double", arguments={"n": "bad"}, agent="repo_agent")
    )
    assert not res.success
    assert res.error is not None


def test_execute_unknown_tool(reg_with_tool: ToolRegistry) -> None:
    ex = ExecutionController(reg_with_tool)
    res = ex.execute(ToolCall(name="missing", arguments={}, agent="repo_agent"))
    assert not res.success


def test_execute_handler_exception(reg_with_tool: ToolRegistry) -> None:
    reg = ToolRegistry()

    def boom() -> str:
        raise RuntimeError("fail")

    reg.register(
        ToolDefinition(
            name="boom",
            description="x",
            parameters={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=boom,
        ),
    )
    ex = ExecutionController(reg)
    res = ex.execute(ToolCall(name="boom", arguments={}, agent="repo_agent"))
    assert not res.success
    assert "RuntimeError" in (res.error or "")
