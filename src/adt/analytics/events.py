"""Structured events for supervised learning analytics."""

from __future__ import annotations

from adt.models.schemas import CodeIssue
from adt.tracing.events import TraceEvent

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "off_by_one",
        ("off-by-one", "off by one", "boundary", "inclusive", "<=", ">="),
    ),
    (
        "edge_case",
        ("edge case", "empty", "null", "none", "zero", "negative", "overflow"),
    ),
    (
        "naming",
        ("name", "naming", "variable name", "rename", "descriptive"),
    ),
    (
        "type_annotation",
        ("type", "annotation", "typing", "hint"),
    ),
    (
        "docstring",
        ("docstring", "documentation", "doc comment"),
    ),
    (
        "error_handling",
        ("error", "exception", "try", "except", "raise", "handle"),
    ),
    (
        "logic",
        ("logic", "incorrect", "wrong", "bug", "condition"),
    ),
    (
        "style",
        ("style", "idiomatic", "pythonic", "readability", "format"),
    ),
    (
        "performance",
        ("performance", "slow", "complexity", "big o", "efficient"),
    ),
    (
        "testing",
        ("test", "coverage", "assertion", "case"),
    ),
)


def categorize_issue(issue: CodeIssue) -> str:
    """Classify a :class:`CodeIssue` into a coarse category string.

    The classification is a simple keyword match against the issue
    description. It is intentionally approximate: the goal is to cluster
    recurring themes in stats ("5 off-by-one errors this week"), not to
    build a full taxonomy. Falls back to ``"other"`` when no keyword
    matches.
    """
    text = (issue.description or "").lower()
    if not text:
        return "other"
    for label, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return label
    return "other"


class LearningEvent(TraceEvent):
    """Trace event specific to supervised learning sessions.

    Extends :class:`~adt.tracing.events.TraceEvent` with fields describing
    a single pedagogical interaction. Each supervised ``ask`` emits one
    ``supervised_step`` event and each ``review`` emits one ``code_review``
    event. They share a trace id per CLI invocation but can be correlated
    across invocations via ``problem_summary``.

    Attributes:
        step_id: 1-based step the user is on in the current supervised
            session. ``0`` when not applicable (e.g. session not started).
        iteration_count: Number of commands executed against this session
            so far, including the current one.
        assessment: Review verdict (``needs_work`` / ``on_track`` /
            ``excellent``) for review events; ``"n/a"`` for pure
            step-guidance events.
        error_types: Coarse categories of issues found during a review
            (empty for non-review events).
        completion_time_ms: Wall clock time taken to produce this event's
            payload, in milliseconds. ``None`` when unavailable.
        problem_summary: Free-text restatement of the problem the user is
            working on. Used to group events into sessions.
        level: Difficulty level at the moment the event was emitted.
    """

    step_id: int = 0
    iteration_count: int = 0
    assessment: str = "n/a"
    error_types: list[str] = []  # noqa: RUF012 — Pydantic default
    completion_time_ms: int | None = None
    problem_summary: str = ""
    level: str = "intermediate"
