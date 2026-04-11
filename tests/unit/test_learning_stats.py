"""Unit tests for :func:`compute_stats`."""

from __future__ import annotations

from adt.analytics.events import LearningEvent
from adt.analytics.stats import LearningStats, compute_stats


def _step(
    problem: str,
    *,
    step_id: int,
    iteration: int,
    tokens: int = 0,
    trace_id: str = "",
) -> LearningEvent:
    return LearningEvent(
        trace_id=trace_id or f"s-{problem}-{step_id}",
        component="supervisor",
        event_type="supervised_step",
        step_id=step_id,
        iteration_count=iteration,
        problem_summary=problem,
        level="intermediate",
        data={"prompt_tokens": tokens, "completion_tokens": tokens},
    )


def _review(
    problem: str,
    *,
    step_id: int,
    iteration: int,
    assessment: str,
    errors: list[str],
) -> LearningEvent:
    return LearningEvent(
        trace_id=f"r-{problem}-{iteration}",
        component="reviewer",
        event_type="code_review",
        step_id=step_id,
        iteration_count=iteration,
        assessment=assessment,
        error_types=errors,
        problem_summary=problem,
        level="intermediate",
    )


def test_compute_stats_empty() -> None:
    assert compute_stats([]) == LearningStats()


def test_compute_stats_basic_grouping() -> None:
    events = [
        _step("FizzBuzz", step_id=1, iteration=1, tokens=100),
        _step("FizzBuzz", step_id=2, iteration=2, tokens=200),
        _review(
            "FizzBuzz",
            step_id=2,
            iteration=3,
            assessment="on_track",
            errors=["off_by_one"],
        ),
        _step("Binary search", step_id=1, iteration=1, tokens=150),
    ]
    stats = compute_stats(events)

    assert stats.sessions == 2
    assert stats.reviews == 1
    assert stats.supervised_steps == 3
    # FizzBuzz max step = 2, Binary search max step = 1 -> avg 1.5
    assert stats.avg_steps_per_session == 1.5
    # FizzBuzz max iterations = 3, Binary search = 1 -> avg 2.0
    assert stats.avg_iterations_per_step == 2.0
    assert stats.assessments == {"on_track": 1}
    # tokens: 100*2 + 200*2 + 150*2 = 900
    assert stats.total_tokens == 900
    assert ("off_by_one", 1) in stats.common_issues


def test_compute_stats_improvement_trend_three_sessions() -> None:
    events = [
        _step("P1", step_id=1, iteration=6),
        _step("P2", step_id=1, iteration=4),
        _step("P3", step_id=1, iteration=2),
    ]
    stats = compute_stats(events)
    assert stats.improvement_trend == [6.0, 4.0, 2.0]


def test_compute_stats_last_n_filter() -> None:
    events = [
        _step("old-1", step_id=1, iteration=1),
        _step("old-2", step_id=1, iteration=1),
        _step("recent", step_id=3, iteration=5),
    ]
    stats = compute_stats(events, last_n=1)
    assert stats.sessions == 1
    assert stats.avg_steps_per_session == 3.0
    assert stats.avg_iterations_per_step == 5.0


def test_compute_stats_counts_common_issues_across_reviews() -> None:
    events = [
        _review(
            "P1",
            step_id=1,
            iteration=1,
            assessment="needs_work",
            errors=["off_by_one", "naming"],
        ),
        _review(
            "P1",
            step_id=1,
            iteration=2,
            assessment="needs_work",
            errors=["off_by_one"],
        ),
        _review(
            "P2",
            step_id=1,
            iteration=1,
            assessment="excellent",
            errors=[],
        ),
    ]
    stats = compute_stats(events)
    counts = dict(stats.common_issues)
    assert counts.get("off_by_one") == 2
    assert counts.get("naming") == 1
    assert stats.assessments == {"needs_work": 2, "excellent": 1}
