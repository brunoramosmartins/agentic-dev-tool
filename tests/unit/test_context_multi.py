"""Multi-repository context blocks."""

from __future__ import annotations

from pathlib import Path

from adt.mcp.context import ContextBuilder


def test_build_from_repos_labels(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "README.md").write_text("# A", encoding="utf-8")
    (b / "README.md").write_text("# B", encoding="utf-8")
    ctx = ContextBuilder(use_repo_tree_cache=False)
    out = ctx.build_from_repos({"r0": a, "r1": b}, query="readme", use_cache=False)
    assert "[context:repo label=r0" in out
    assert "[context:repo label=r1" in out
    assert "# A" in out or "README" in out
