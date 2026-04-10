"""Integration test for the review flow through ``run_review`` with a fake LLM."""

from __future__ import annotations

from pathlib import Path

from adt.core.session import SessionContext
from adt.models.schemas import LLMMessage, SupervisedResponse, SupervisedStep
from adt.review_session import run_review
from tests.fake_llm import FakeLLM

_REVIEW_JSON = """{
    "issues": [
        {"line": 2, "severity": "error",
         "description": "Off-by-one in upper bound",
         "fix_hint": "Should `high` be inclusive?"}
    ],
    "improvements": ["Add a docstring with examples"],
    "strengths": ["Clear function signature"],
    "next_step": "Fix the boundary check and rerun the test.",
    "overall_assessment": "needs_work"
}"""


def test_run_review_parses_feedback_and_updates_session(tmp_path: Path) -> None:
    target = tmp_path / "solution.py"
    target.write_text("def search(xs):\n    return -1\n", encoding="utf-8")

    sess_file = tmp_path / "session.json"
    sess = SessionContext()
    sess.update_from_supervised(
        SupervisedResponse(
            problem_summary="Implement binary search",
            current_step=SupervisedStep(step_number=2, goal="add base case"),
            total_steps=4,
        ),
    )
    sess.save(sess_file)

    fake = FakeLLM([LLMMessage(role="assistant", content=_REVIEW_JSON)])
    loaded = SessionContext.load(sess_file)
    result = run_review(
        file=target,
        extra_context="should return the index of `target` in xs",
        level="beginner",
        configure_logging=False,
        llm=fake,
        session=loaded,
    )

    assert result.feedback is not None
    assert result.feedback.overall_assessment == "needs_work"
    assert result.feedback.issues[0].line == 2
    # Session was updated with the review outcome
    assert "needs_work" in result.session.previous_feedback


def test_run_review_returns_raw_when_llm_returns_garbage(tmp_path: Path) -> None:
    target = tmp_path / "x.py"
    target.write_text("a = 1\n", encoding="utf-8")
    fake = FakeLLM([LLMMessage(role="assistant", content="not json at all")])
    result = run_review(
        file=target,
        configure_logging=False,
        llm=fake,
        session=SessionContext(),
    )
    assert result.feedback is None
    assert "not json" in result.raw_answer


def test_run_review_missing_file_raises(tmp_path: Path) -> None:
    from adt.review_session import ReviewConfigurationError

    missing = tmp_path / "nope.py"
    try:
        run_review(
            file=missing,
            configure_logging=False,
            llm=FakeLLM([]),
            session=SessionContext(),
        )
    except ReviewConfigurationError as exc:
        assert "not found" in str(exc).lower()
    else:
        raise AssertionError("expected ReviewConfigurationError")
