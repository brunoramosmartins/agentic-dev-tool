"""Edge-case tests for mcp/tokens.py covering uncovered branches."""

from __future__ import annotations

from adt.mcp.tokens import (
    count_tokens,
    get_encoder_for_model,
    trim_context,
    truncate_head_tail,
)


def test_get_encoder_fallback_unknown_model() -> None:
    enc = get_encoder_for_model("totally-fake-model-xyz")
    assert enc.name == "cl100k_base"


def test_get_encoder_known_model() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    assert enc is not None


def test_trim_context_zero_tokens() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    assert trim_context("hello world", 0, enc) == ""


def test_trim_context_negative_tokens() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    assert trim_context("hello world", -5, enc) == ""


def test_trim_context_actually_trims() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    long_text = "word " * 500
    result = trim_context(long_text, 10, enc)
    assert "[trimmed]" in result
    assert count_tokens(result, enc) < count_tokens(long_text, enc)


def test_trim_context_short_text_unchanged() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    result = trim_context("hi", 100, enc)
    assert result == "hi"


def test_truncate_head_tail_zero_tokens() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    assert truncate_head_tail("hello world", 0, enc) == ""


def test_truncate_head_tail_actually_truncates() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    long_text = "word " * 500
    result = truncate_head_tail(long_text, 10, enc)
    assert "..." in result


def test_truncate_head_tail_short_text_unchanged() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    result = truncate_head_tail("hi", 100, enc)
    assert result == "hi"


def test_count_tokens_empty() -> None:
    enc = get_encoder_for_model("gpt-4o-mini")
    assert count_tokens("", enc) == 0
