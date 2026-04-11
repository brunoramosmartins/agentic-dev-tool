"""Unit tests for :class:`LearningEvent` and ``categorize_issue``."""

from __future__ import annotations

from adt.analytics.events import LearningEvent, categorize_issue
from adt.models.schemas import CodeIssue


def _issue(description: str, severity: str = "warning") -> CodeIssue:
    return CodeIssue(line=1, severity=severity, description=description, fix_hint="")


def test_learning_event_defaults() -> None:
    event = LearningEvent(
        trace_id="t1",
        component="supervisor",
        event_type="supervised_step",
    )
    assert event.step_id == 0
    assert event.iteration_count == 0
    assert event.assessment == "n/a"
    assert event.error_types == []
    assert event.completion_time_ms is None
    assert event.problem_summary == ""
    assert event.level == "intermediate"


def test_learning_event_full_payload_roundtrip() -> None:
    event = LearningEvent(
        trace_id="t2",
        component="reviewer",
        event_type="code_review",
        step_id=3,
        iteration_count=5,
        assessment="on_track",
        error_types=["off_by_one", "naming"],
        completion_time_ms=1234,
        problem_summary="Implement binary search",
        level="advanced",
        data={"issue_count": 2},
    )
    raw = event.model_dump(mode="json")
    restored = LearningEvent.model_validate(raw)
    assert restored.assessment == "on_track"
    assert restored.error_types == ["off_by_one", "naming"]
    assert restored.step_id == 3
    assert restored.data["issue_count"] == 2


def test_categorize_off_by_one() -> None:
    assert categorize_issue(_issue("classic off-by-one error on loop bounds")) == (
        "off_by_one"
    )
    assert categorize_issue(_issue("boundary condition missing")) == "off_by_one"


def test_categorize_edge_case() -> None:
    assert categorize_issue(_issue("does not handle empty list")) == "edge_case"
    assert categorize_issue(_issue("negative input not considered")) == "edge_case"


def test_categorize_naming_and_types() -> None:
    assert categorize_issue(_issue("variable name is unclear")) == "naming"
    assert categorize_issue(_issue("missing type hint on return")) == "type_annotation"


def test_categorize_error_handling() -> None:
    assert categorize_issue(_issue("should raise ValueError on bad input")) == (
        "error_handling"
    )


def test_categorize_fallback_to_other() -> None:
    assert categorize_issue(_issue("something weird going on")) == "other"
    assert categorize_issue(_issue("")) == "other"
