"""Unit tests for the review prompt builders and JSON parser."""

from __future__ import annotations

from adt.core.supervised_supervisor import (
    build_review_system_prompt,
    build_review_user_prompt,
    parse_review_feedback,
)


def test_review_prompt_includes_level() -> None:
    prompt = build_review_system_prompt("advanced")
    assert "advanced" in prompt
    assert "JSON" in prompt
    assert "overall_assessment" in prompt


def test_user_prompt_includes_code_and_path() -> None:
    msg = build_review_user_prompt(
        file_path="solution.py",
        code="def f():\n    return 1\n",
    )
    assert "solution.py" in msg
    assert "def f():" in msg


def test_user_prompt_includes_step_and_extra_context() -> None:
    msg = build_review_user_prompt(
        file_path="x.py",
        code="pass\n",
        extra_context="should sort the list",
        step_context="Step 2 of 4",
    )
    assert "should sort the list" in msg
    assert "Step 2 of 4" in msg


def test_parse_valid_feedback() -> None:
    raw = """{
        "issues": [
            {"line": 12, "severity": "warning",
             "description": "bad name", "fix_hint": "rename"}
        ],
        "improvements": ["add docstring"],
        "strengths": ["clear types"],
        "next_step": "fix the warning",
        "overall_assessment": "on_track"
    }"""
    fb = parse_review_feedback(raw)
    assert fb is not None
    assert fb.overall_assessment == "on_track"
    assert len(fb.issues) == 1
    assert fb.issues[0].line == 12
    assert fb.improvements == ["add docstring"]


def test_parse_feedback_with_markdown_fences() -> None:
    raw = """```json
{
  "issues": [],
  "improvements": [],
  "strengths": [],
  "next_step": "",
  "overall_assessment": "excellent"
}
```"""
    fb = parse_review_feedback(raw)
    assert fb is not None
    assert fb.overall_assessment == "excellent"


def test_parse_invalid_json_returns_none() -> None:
    assert parse_review_feedback("totally not json") is None


def test_parse_non_dict_json_returns_none() -> None:
    assert parse_review_feedback("[1, 2, 3]") is None


def test_parse_skips_malformed_issue_entries() -> None:
    raw = """{
        "issues": ["not a dict", {"severity": "error",
         "description": "real one"}],
        "improvements": [],
        "strengths": [],
        "next_step": "",
        "overall_assessment": "needs_work"
    }"""
    fb = parse_review_feedback(raw)
    assert fb is not None
    assert len(fb.issues) == 1
    assert fb.issues[0].severity == "error"


def test_parse_missing_assessment_defaults_to_on_track() -> None:
    raw = '{"issues": [], "improvements": [], "strengths": [], "next_step": ""}'
    fb = parse_review_feedback(raw)
    assert fb is not None
    assert fb.overall_assessment == "on_track"
