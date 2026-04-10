"""Unit tests for SupervisedRenderer."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from adt.cli.supervised_renderer import SupervisedRenderer
from adt.models.schemas import SupervisedResponse, SupervisedStep


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=120)


def _sample_response() -> SupervisedResponse:
    return SupervisedResponse(
        problem_summary="Implement binary search",
        current_step=SupervisedStep(
            step_number=1,
            goal="Define the function signature",
            requirements=["Accept sorted list", "Return index or -1"],
            hints=["Consider type annotations"],
            questions=["Why must the list be sorted?"],
        ),
        total_steps=4,
        progress_note="Next: handle the base case",
    )


def test_renderer_shows_problem_and_step() -> None:
    con = _make_console()
    SupervisedRenderer(con).render(_sample_response())
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "Implement binary search" in out
    assert "Step 1 of 4" in out
    assert "Define the function signature" in out


def test_renderer_shows_all_sections() -> None:
    con = _make_console()
    SupervisedRenderer(con).render(_sample_response())
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "Requirements" in out
    assert "Accept sorted list" in out
    assert "Hints" in out
    assert "Consider type annotations" in out
    assert "Questions for you" in out
    assert "Why must the list be sorted?" in out
    assert "Next" in out


def test_renderer_skips_empty_sections() -> None:
    con = _make_console()
    resp = SupervisedResponse(
        problem_summary="X",
        current_step=SupervisedStep(step_number=1, goal="Y"),
        total_steps=1,
    )
    SupervisedRenderer(con).render(resp)
    out = con.file.getvalue()  # type: ignore[union-attr]
    assert "Requirements" not in out
    assert "Hints" not in out
    assert "Questions" not in out
