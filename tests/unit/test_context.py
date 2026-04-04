"""Context builder heuristics and repo scanning."""

from __future__ import annotations

from adt.mcp.context import ContextBuilder


def test_estimate_tokens() -> None:
    cb = ContextBuilder()
    # 3 words -> ceil(3/0.75) = 4
    assert cb.estimate_tokens("a b c") == 4


def test_truncate_preserves_ends() -> None:
    cb = ContextBuilder()
    words = " ".join(f"w{i}" for i in range(100))
    out = cb.truncate(words, max_tokens=10)
    assert out.startswith("w0")
    assert "w99" in out
    assert "..." in out


def test_build_from_text_wraps() -> None:
    cb = ContextBuilder()
    s = cb.build_from_text("  hi  ")
    assert "[context:text]" in s
    assert "hi" in s


def test_build_from_repo_sample(sample_repo_path: str) -> None:
    cb = ContextBuilder()
    ctx = cb.build_from_repo(sample_repo_path, max_depth=5)
    assert "[tree]" in ctx
    assert "main.py" in ctx
