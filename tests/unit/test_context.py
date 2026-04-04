"""Context builder, tiktoken, and repo scanning."""

from __future__ import annotations

from adt.mcp.context import ContextBuilder


def test_estimate_tokens_uses_tiktoken() -> None:
    """Token counts should be positive for non-empty strings."""
    cb = ContextBuilder()
    assert cb.estimate_tokens("hello world") >= 1
    assert cb.estimate_tokens("") == 0


def test_truncate_preserves_ends() -> None:
    """Head/tail truncation should keep start and end token runs."""
    cb = ContextBuilder()
    words = " ".join(f"w{i}" for i in range(100))
    out = cb.truncate(words, max_tokens=30)
    assert "w0" in out
    assert "..." in out


def test_trim_context_prefix() -> None:
    """trim_context should shorten from the end of the token stream."""
    cb = ContextBuilder()
    long_text = "word " * 500
    trimmed = cb.trim_context(long_text, max_tokens=10)
    assert len(trimmed) < len(long_text)
    assert cb.estimate_tokens(trimmed) < cb.estimate_tokens(long_text)


def test_build_from_text_wraps() -> None:
    """Labeled blocks should wrap stripped text."""
    cb = ContextBuilder()
    s = cb.build_from_text("  hi  ")
    assert "[context:text]" in s
    assert "hi" in s


def test_build_from_repo_sample(sample_repo_path: str) -> None:
    """Fixture repo should appear in tree and ranked files."""
    cb = ContextBuilder(use_repo_tree_cache=False)
    ctx = cb.build_from_repo(
        sample_repo_path,
        max_depth=5,
        query="main python",
        use_cache=False,
    )
    assert "[tree]" in ctx
    assert "main.py" in ctx


def test_build_from_repo_respects_no_cache(tmp_path) -> None:
    """use_cache=False should still produce output (bypass tree cache read/write)."""
    d = tmp_path / "proj"
    d.mkdir()
    (d / "a.md").write_text("# hi", encoding="utf-8")
    cb = ContextBuilder(
        use_repo_tree_cache=True,
        cache_dir=tmp_path / "cache",
    )
    ctx = cb.build_from_repo(str(d), use_cache=False, max_depth=2)
    assert "a.md" in ctx
