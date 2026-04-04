"""Multi-root repo tool registration."""

from __future__ import annotations

from pathlib import Path

from adt.bootstrap import register_repo_tools
from adt.mcp.executor import ExecutionController
from adt.mcp.registry import ToolRegistry
from adt.models.schemas import ToolCall


def test_register_repo_tools_two_roots_read_and_compare(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "x.txt").write_text("alpha", encoding="utf-8")
    (b / "y.txt").write_text("beta", encoding="utf-8")
    reg = ToolRegistry()
    register_repo_tools(reg, {"r0": a, "r1": b}, primary_repo_key="r0")
    ex = ExecutionController(reg)
    r0 = ex.execute(
        ToolCall(
            name="read_file",
            arguments={"path": "x.txt", "repo_key": "r0"},
            agent="repo_agent",
        ),
    )
    assert r0.success and "alpha" in r0.output
    bad = ex.execute(
        ToolCall(
            name="read_file",
            arguments={"path": "x.txt", "repo_key": "r1"},
            agent="repo_agent",
        ),
    )
    assert not bad.success or "error" in bad.output.lower()
    cmp = ex.execute(
        ToolCall(
            name="compare_repos",
            arguments={"repo_a": "r0", "repo_b": "r1"},
            agent="repo_agent",
        ),
    )
    assert cmp.success
    assert "compare_repos" in cmp.output
