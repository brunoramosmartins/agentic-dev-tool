"""Unit tests for the supervised SessionContext lifecycle and persistence."""

from __future__ import annotations

from pathlib import Path

from adt.core.session import SessionContext
from adt.models.schemas import SupervisedResponse, SupervisedStep


def _supervised(problem: str, step: int = 1, total: int = 4) -> SupervisedResponse:
    return SupervisedResponse(
        problem_summary=problem,
        current_step=SupervisedStep(step_number=step, goal="g"),
        total_steps=total,
    )


def test_empty_session_is_empty() -> None:
    sess = SessionContext()
    assert sess.is_empty()
    assert sess.as_step_context() == ""


def test_update_from_supervised_populates_state() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("Binary search", step=2, total=5))
    assert not sess.is_empty()
    assert sess.problem_summary == "Binary search"
    assert sess.current_step == 2
    assert sess.total_steps == 5
    assert sess.iteration_count == 1


def test_update_with_different_problem_clears_feedback() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("Binary search"))
    sess.record_feedback("on_track")
    assert sess.previous_feedback == ["on_track"]

    sess.update_from_supervised(_supervised("Quicksort"))
    assert sess.previous_feedback == []
    assert sess.problem_summary == "Quicksort"


def test_update_with_same_problem_keeps_feedback() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("Binary search"))
    sess.record_feedback("needs_work")
    sess.update_from_supervised(_supervised("Binary search", step=2))
    assert sess.previous_feedback == ["needs_work"]
    assert sess.current_step == 2


def test_record_feedback_caps_history() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("X"))
    for _ in range(15):
        sess.record_feedback("on_track")
    assert len(sess.previous_feedback) == 10


def test_as_step_context_includes_recent_feedback() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("Binary search", step=3, total=5))
    sess.record_feedback("needs_work")
    out = sess.as_step_context()
    assert "Binary search" in out
    assert "Step 3 of 5" in out
    assert "needs_work" in out


def test_clear_resets_state() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("X"))
    sess.clear()
    assert sess.is_empty()
    assert sess.previous_feedback == []


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "session.json"
    sess = SessionContext()
    sess.update_from_supervised(_supervised("Binary search", step=2, total=4))
    sess.record_feedback("excellent")
    sess.save(target)

    loaded = SessionContext.load(target)
    assert loaded.problem_summary == "Binary search"
    assert loaded.current_step == 2
    assert loaded.total_steps == 4
    assert loaded.previous_feedback == ["excellent"]


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    sess = SessionContext.load(tmp_path / "nope.json")
    assert sess.is_empty()


def test_load_corrupted_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "session.json"
    target.write_text("{not valid json", encoding="utf-8")
    sess = SessionContext.load(target)
    assert sess.is_empty()


def test_reset_deletes_file(tmp_path: Path) -> None:
    target = tmp_path / "session.json"
    target.write_text("{}", encoding="utf-8")
    SessionContext.reset(target)
    assert not target.exists()
    # No error if missing
    SessionContext.reset(target)


def test_matches_problem_loose_containment() -> None:
    sess = SessionContext()
    sess.update_from_supervised(_supervised("Binary search"))
    assert sess.matches_problem("Binary search")
    assert sess.matches_problem("Binary search algorithm")
    assert not sess.matches_problem("Quicksort")
