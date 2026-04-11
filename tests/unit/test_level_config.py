"""Unit tests for :mod:`adt.core.level_config`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from adt.core.level_config import (
    LEVEL_CONFIGS,
    LevelConfig,
    format_level_directives,
    get_level_config,
)


def test_registry_covers_all_levels() -> None:
    assert set(LEVEL_CONFIGS) == {"beginner", "intermediate", "advanced"}


def test_beginner_values() -> None:
    cfg = LEVEL_CONFIGS["beginner"]
    assert cfg.hints_per_step == 3
    assert cfg.questions_per_step == 1
    assert cfg.explanation_depth == "detailed"
    assert cfg.show_alternatives is False
    assert cfg.feedback_focus == "encouraging"


def test_intermediate_values() -> None:
    cfg = LEVEL_CONFIGS["intermediate"]
    assert cfg.hints_per_step == 2
    assert cfg.questions_per_step == 2
    assert cfg.explanation_depth == "moderate"
    assert cfg.show_alternatives is True
    assert cfg.feedback_focus == "balanced"


def test_advanced_values() -> None:
    cfg = LEVEL_CONFIGS["advanced"]
    assert cfg.hints_per_step == 0
    assert cfg.questions_per_step == 3
    assert cfg.explanation_depth == "minimal"
    assert cfg.show_alternatives is True
    assert cfg.feedback_focus == "critical"


def test_level_config_is_frozen() -> None:
    cfg = LEVEL_CONFIGS["beginner"]
    with pytest.raises(ValidationError):
        cfg.hints_per_step = 99  # type: ignore[misc]


def test_level_config_rejects_out_of_range_hints() -> None:
    with pytest.raises(ValidationError):
        LevelConfig(
            name="intermediate",
            hints_per_step=99,
            questions_per_step=2,
            explanation_depth="moderate",
            show_alternatives=True,
            feedback_focus="balanced",
        )


def test_level_config_rejects_invalid_depth() -> None:
    with pytest.raises(ValidationError):
        LevelConfig(
            name="beginner",
            hints_per_step=1,
            questions_per_step=1,
            explanation_depth="very detailed",  # type: ignore[arg-type]
            show_alternatives=False,
            feedback_focus="encouraging",
        )


def test_get_level_config_known() -> None:
    assert get_level_config("beginner").name == "beginner"
    assert get_level_config("advanced").name == "advanced"


def test_get_level_config_unknown_falls_back() -> None:
    assert get_level_config("expert").name == "intermediate"  # type: ignore[arg-type]


def test_format_beginner_directives() -> None:
    text = format_level_directives(LEVEL_CONFIGS["beginner"])
    assert "Level: beginner" in text
    assert "Provide exactly 3 hints" in text
    assert "1 reflective question" in text
    assert "detailed prose" in text
    assert "Do NOT mention alternative approaches" in text
    assert "encouraging" in text


def test_format_advanced_directives() -> None:
    text = format_level_directives(LEVEL_CONFIGS["advanced"])
    assert "Level: advanced" in text
    assert "Provide NO hints" in text
    assert "3 reflective questions" in text
    assert "minimal" in text.lower()
    assert "alternative" in text.lower()
    assert "critical" in text.lower()


def test_format_intermediate_directives() -> None:
    text = format_level_directives(LEVEL_CONFIGS["intermediate"])
    assert "Level: intermediate" in text
    assert "Provide exactly 2 hints" in text
    assert "2 reflective questions" in text
    assert "moderate prose" in text
    assert "balanced" in text
