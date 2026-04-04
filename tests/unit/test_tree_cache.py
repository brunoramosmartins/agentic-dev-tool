"""Repository tree cache."""

from __future__ import annotations

from adt.mcp.cache import RepoTreeCache


def test_tree_cache_second_call_reuses_within_ttl(tmp_path) -> None:
    """Identical key within TTL should skip rebuild."""
    cache_dir = tmp_path / "c"
    c = RepoTreeCache(cache_dir, ttl_seconds=3600.0)
    root = tmp_path / "repo"
    root.mkdir()
    calls = {"n": 0}

    def build() -> list[str]:
        calls["n"] += 1
        return ["line1", "line2"]

    a = c.get_or_build(root, max_depth=2, build=build)
    b = c.get_or_build(root, max_depth=2, build=build)
    assert a == b
    assert calls["n"] == 1
