"""Unit tests for :class:`StatsRenderer`."""

from __future__ import annotations

import io

from rich.console import Console

from adt.analytics.stats import LearningStats
from adt.cli.stats_renderer import StatsRenderer


def _render(stats: LearningStats) -> str:
    buf = io.StringIO()
    console = Console(file=buf, color_system=None, width=100, record=False)
    StatsRenderer(console).render(stats)
    return buf.getvalue()


def test_stats_renderer_empty() -> None:
    out = _render(LearningStats())
    assert "Learning Stats" in out
    assert "No supervised learning events" in out
    assert "Sessions: 0" in out


def test_stats_renderer_full_payload() -> None:
    stats = LearningStats(
        sessions=3,
        reviews=2,
        supervised_steps=5,
        avg_steps_per_session=2.5,
        avg_iterations_per_step=3.0,
        common_issues=[("off_by_one", 4), ("naming", 2)],
        improvement_trend=[5.0, 3.0, 2.0],
        total_tokens=12345,
        assessments={"needs_work": 1, "on_track": 1},
    )
    out = _render(stats)
    assert "Sessions: 3" in out
    assert "Reviews:  2" in out
    assert "off_by_one" in out
    assert "naming" in out
    assert "Review Verdicts" in out
    assert "needs_work" in out
    assert "on_track" in out
    assert "Improvement Trend" in out
    assert "5.0 -> 3.0 -> 2.0" in out
    assert "12,345" in out


def test_stats_renderer_skips_empty_sections() -> None:
    stats = LearningStats(
        sessions=1,
        reviews=0,
        supervised_steps=1,
        avg_steps_per_session=1.0,
        avg_iterations_per_step=1.0,
    )
    out = _render(stats)
    assert "Common Issues" not in out
    assert "Review Verdicts" not in out
    assert "Improvement Trend" not in out
