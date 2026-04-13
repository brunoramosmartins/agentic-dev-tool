"""Structured events for supervised learning analytics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from adt.models.schemas import CodeIssue

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


class LearningEvent(BaseModel):
    """Standalone event for supervised learning analytics (schema v2).

    Decoupled from :class:`~adt.tracing.events.TraceEvent` so that review
    events are not forced to carry an empty ``trace_id``.

    Attributes:
        trace_id: Trace correlation id (``None`` for review-only events).
        session_name: Named session this event belongs to (``None`` for
            legacy v1 events).
        timestamp: UTC timestamp (auto-generated).
        component: Emitting component (``supervisor`` or ``reviewer``).
        event_type: ``supervised_step`` or ``code_review``.
        iteration: Optional loop iteration number.
        data: Arbitrary key-value pairs (token counts, etc.).
        step_id: 1-based step the user is on.
        iteration_count: Commands executed against this session so far.
        assessment: Review verdict or ``"n/a"`` for step-guidance events.
        error_types: Coarse issue categories from the reviewer.
        completion_time_ms: Wall clock time in milliseconds.
        problem_summary: Free-text problem description (session grouping key).
        level: Difficulty level at emit time.
        schema_version: ``2`` for new events; reader tolerates ``1``.
    """

    trace_id: str | None = None
    session_name: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    component: str = ""
    event_type: str = ""
    iteration: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    step_id: int = 0
    iteration_count: int = 0
    assessment: str = "n/a"
    error_types: list[str] = []  # noqa: RUF012 — Pydantic default
    completion_time_ms: int | None = None
    problem_summary: str = ""
    level: str = "intermediate"
    schema_version: int = 2
