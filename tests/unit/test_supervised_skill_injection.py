"""Unit tests verifying the skill content is injected into the prompts."""

from __future__ import annotations

from adt.core.supervised_supervisor import (
    build_review_system_prompt,
    build_supervised_system_prompt,
)
from adt.skills.supervised_engineering import load_skill_content
from adt.skills.supervised_engineering.loader import reset_cache


def test_supervised_prompt_embeds_skill_heuristics() -> None:
    reset_cache()
    prompt = build_supervised_system_prompt("intermediate")
    assert "Skill: Supervised Engineering" in prompt
    assert "Teaching Heuristics" in prompt
    assert "Decomposition Patterns" in prompt
    # Level still interpolated after the skill block
    assert "intermediate" in prompt
    # JSON output spec still present
    assert '"problem_summary"' in prompt


def test_review_prompt_embeds_skill_heuristics() -> None:
    reset_cache()
    prompt = build_review_system_prompt("advanced")
    assert "Skill: Supervised Engineering" in prompt
    assert "Feedback Guidelines" in prompt
    assert "Anti-Patterns" in prompt
    assert "advanced" in prompt
    assert '"overall_assessment"' in prompt


def test_supervised_prompt_accepts_skill_override() -> None:
    prompt = build_supervised_system_prompt(
        "beginner",
        skill_content="# Custom\n- rule one\n",
    )
    assert "Custom" in prompt
    assert "rule one" in prompt
    # Packaged content should NOT leak in when override is used
    assert "Decomposition Patterns" not in prompt
    # Base prompt still interpolated
    assert "beginner" in prompt
    assert '"problem_summary"' in prompt


def test_review_prompt_accepts_skill_override() -> None:
    prompt = build_review_system_prompt(
        "beginner",
        skill_content="# Override\n",
    )
    assert "Override" in prompt
    assert "Decomposition Patterns" not in prompt
    assert '"overall_assessment"' in prompt


def test_skill_content_is_complete_and_reused() -> None:
    reset_cache()
    raw = load_skill_content()
    prompt = build_supervised_system_prompt("intermediate")
    # Every non-empty line of the skill must appear in the prompt
    for line in raw.strip().splitlines():
        stripped = line.strip()
        if stripped:
            assert stripped in prompt
