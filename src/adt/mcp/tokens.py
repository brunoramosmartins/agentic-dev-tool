"""tiktoken-backed counting and trimming for prompt context."""

from __future__ import annotations

import tiktoken


def get_encoder_for_model(model: str) -> tiktoken.Encoding:
    """Return a tiktoken encoding suitable for ``model`` (cl100k fallback)."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, encoding: tiktoken.Encoding) -> int:
    """Count tokens in ``text`` using the given encoding."""
    if not text:
        return 0
    return len(encoding.encode(text))


def trim_context(text: str, max_tokens: int, encoding: tiktoken.Encoding) -> str:
    """Trim ``text`` to at most ``max_tokens`` tokens, keeping the start.

    If trimming occurs, appends a short marker so callers know content was cut.

    Args:
        text: UTF-8 prompt fragment.
        max_tokens: Maximum tokens to keep (non-positive yields empty string).
        encoding: tiktoken encoding instance.

    Returns:
        Possibly shortened text.
    """
    if max_tokens <= 0:
        return ""
    ids = encoding.encode(text)
    if len(ids) <= max_tokens:
        return text
    body = encoding.decode(ids[:max_tokens])
    return f"{body}\n[trimmed]"


def truncate_head_tail(
    text: str,
    max_tokens: int,
    encoding: tiktoken.Encoding,
) -> str:
    """Trim by keeping the first and last token runs (legacy context behavior)."""
    if max_tokens <= 0:
        return ""
    ids = encoding.encode(text)
    if len(ids) <= max_tokens:
        return text
    head = max_tokens // 2
    tail = max_tokens - head
    beginning = encoding.decode(ids[:head])
    ending = encoding.decode(ids[-tail:])
    return f"{beginning}\n...\n{ending}"
