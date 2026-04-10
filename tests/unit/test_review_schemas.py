"""Unit tests for the review feedback schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from adt.models.schemas import CodeIssue, ReviewFeedback


def test_code_issue_minimal() -> None:
    issue = CodeIssue(severity="warning", description="bad name")
    assert issue.line is None
    assert issue.severity == "warning"
    assert issue.fix_hint == ""


def test_code_issue_invalid_severity_rejected() -> None:
    with pytest.raises(ValidationError):
        CodeIssue(severity="critical", description="x")  # type: ignore[arg-type]


def test_review_feedback_minimal() -> None:
    fb = ReviewFeedback(overall_assessment="on_track")
    assert fb.issues == []
    assert fb.improvements == []
    assert fb.strengths == []
    assert fb.next_step == ""


def test_review_feedback_full() -> None:
    fb = ReviewFeedback(
        issues=[
            CodeIssue(
                line=12,
                severity="error",
                description="off-by-one",
                fix_hint="check the upper bound",
            )
        ],
        improvements=["add docstring"],
        strengths=["clear naming"],
        next_step="run the failing test",
        overall_assessment="needs_work",
    )
    assert fb.overall_assessment == "needs_work"
    assert fb.issues[0].line == 12
    assert fb.issues[0].severity == "error"


def test_review_feedback_invalid_assessment_rejected() -> None:
    with pytest.raises(ValidationError):
        ReviewFeedback(overall_assessment="amazing")  # type: ignore[arg-type]
