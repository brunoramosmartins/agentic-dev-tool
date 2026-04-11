"""Unit tests verifying prompts differ across supervision levels."""

from __future__ import annotations

from adt.core.supervised_supervisor import (
    build_review_system_prompt,
    build_supervised_system_prompt,
)


def test_beginner_supervised_prompt_has_three_hints() -> None:
    prompt = build_supervised_system_prompt("beginner", skill_content="# skill\n")
    assert "Level: beginner" in prompt
    assert "Provide exactly 3 hints" in prompt
    assert "detailed prose" in prompt
    assert "encouraging" in prompt


def test_advanced_supervised_prompt_withholds_hints() -> None:
    prompt = build_supervised_system_prompt("advanced", skill_content="# skill\n")
    assert "Level: advanced" in prompt
    assert "Provide NO hints" in prompt
    assert "critical" in prompt.lower()
    # Advanced must not claim to give 3 hints
    assert "Provide exactly 3 hints" not in prompt


def test_intermediate_is_different_from_extremes() -> None:
    beg = build_supervised_system_prompt("beginner", skill_content="# s\n")
    mid = build_supervised_system_prompt("intermediate", skill_content="# s\n")
    adv = build_supervised_system_prompt("advanced", skill_content="# s\n")
    assert beg != mid != adv
    assert "Provide exactly 2 hints" in mid
    assert "balanced" in mid


def test_review_prompt_reflects_level_tone() -> None:
    beg = build_review_system_prompt("beginner", skill_content="# s\n")
    adv = build_review_system_prompt("advanced", skill_content="# s\n")
    assert "encouraging" in beg
    assert "critical" in adv.lower()
    # JSON schema still present regardless of level
    assert '"overall_assessment"' in beg
    assert '"overall_assessment"' in adv


def test_unknown_level_falls_back_to_intermediate_directives() -> None:
    prompt = build_supervised_system_prompt("expert", skill_content="# s\n")
    # The base prompt still shows the raw level, but the directive block
    # falls back to intermediate values.
    assert "Level: intermediate" in prompt
    assert "Provide exactly 2 hints" in prompt
