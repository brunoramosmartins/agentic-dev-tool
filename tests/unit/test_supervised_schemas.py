"""Unit tests for supervised mode schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from adt.models.schemas import QueryRequest, SupervisedResponse, SupervisedStep


def test_query_request_defaults_to_execution_mode() -> None:
    req = QueryRequest(query="hello")
    assert req.mode == "execution"
    assert req.level == "intermediate"


def test_query_request_supervised_mode() -> None:
    req = QueryRequest(query="teach me", mode="supervised", level="beginner")
    assert req.mode == "supervised"
    assert req.level == "beginner"


def test_query_request_invalid_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="x", mode="autopilot")  # type: ignore[arg-type]


def test_query_request_invalid_level_rejected() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="x", level="expert")  # type: ignore[arg-type]


def test_supervised_step_minimal() -> None:
    step = SupervisedStep(step_number=1, goal="define signature")
    assert step.step_number == 1
    assert step.goal == "define signature"
    assert step.requirements == []
    assert step.hints == []
    assert step.questions == []


def test_supervised_response_full() -> None:
    step = SupervisedStep(
        step_number=2,
        goal="implement base case",
        requirements=["handle empty list"],
        hints=["think about the termination condition"],
        questions=["what if the list has one element?"],
    )
    resp = SupervisedResponse(
        problem_summary="Binary search",
        current_step=step,
        total_steps=4,
        progress_note="next we add the loop",
    )
    assert resp.total_steps == 4
    assert resp.current_step.step_number == 2
    assert resp.current_step.hints == ["think about the termination condition"]


def test_supervised_response_requires_total_steps_at_least_one() -> None:
    step = SupervisedStep(step_number=1, goal="x")
    with pytest.raises(ValidationError):
        SupervisedResponse(
            problem_summary="x",
            current_step=step,
            total_steps=0,
        )
