"""Unit tests for the ReviewRenderer."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from adt.cli.review_renderer import ReviewRenderer
from adt.models.schemas import CodeIssue, ReviewFeedback


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=120)


def _sample_feedback() -> ReviewFeedback:
    return ReviewFeedback(
        issues=[
            CodeIssue(
                line=12,
                severity="warning",
                description="Variable `x` is not descriptive",
                fix_hint="What does this value represent?",
            ),
            CodeIssue(
                line=18,
                severity="error",
                description="Off-by-one in boundary check",
                fix_hint="Should `high` be inclusive?",
            ),
        ],
        improvements=["Add edge case handling for empty list"],
        strengths=["Correct function signature and types"],
        next_step="Fix the boundary check, then implement the recursive case.",
        overall_assessment="needs_work",
    )


def test_renderer_shows_assessment_and_issues() -> None:
    con = _make_console()
    ReviewRenderer(con).render(_sample_feedback())
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "Assessment" in out
    assert "Needs Work" in out
    assert "Line 12" in out
    assert "Variable `x` is not descriptive" in out
    assert "What does this value represent?" in out
    assert "Line 18" in out
    assert "Off-by-one" in out


def test_renderer_shows_strengths_improvements_next_step() -> None:
    con = _make_console()
    ReviewRenderer(con).render(_sample_feedback())
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "Strengths" in out
    assert "Correct function signature and types" in out
    assert "Improvements" in out
    assert "Add edge case handling for empty list" in out
    assert "Next Step" in out
    assert "boundary check" in out


def test_renderer_skips_empty_sections() -> None:
    con = _make_console()
    fb = ReviewFeedback(overall_assessment="excellent")
    ReviewRenderer(con).render(fb)
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "Excellent" in out
    assert "Issues" not in out
    assert "Strengths" not in out
    assert "Improvements" not in out
    assert "Next Step" not in out


def test_renderer_handles_issue_without_line() -> None:
    con = _make_console()
    fb = ReviewFeedback(
        issues=[
            CodeIssue(severity="suggestion", description="missing module docstring"),
        ],
        overall_assessment="on_track",
    )
    ReviewRenderer(con).render(fb)
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "missing module docstring" in out
    assert "On Track" in out
    assert "Line " not in out
