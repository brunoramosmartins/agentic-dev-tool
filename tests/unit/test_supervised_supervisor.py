"""Unit tests for SupervisedSupervisor parsing and prompt building."""

from __future__ import annotations

from adt.core.supervised_supervisor import (
    build_supervised_system_prompt,
    parse_supervised_response,
)


def test_build_prompt_includes_level() -> None:
    prompt = build_supervised_system_prompt("beginner")
    assert "beginner" in prompt
    assert "JSON" in prompt
    assert "problem_summary" in prompt


def test_parse_valid_json() -> None:
    raw = """{
        "problem_summary": "Implement binary search",
        "current_step": {
            "step_number": 1,
            "goal": "Define the function signature",
            "requirements": ["accept sorted list", "return index or -1"],
            "hints": ["think about parameter types"],
            "questions": ["why sorted?"]
        },
        "total_steps": 4,
        "progress_note": "next: base case"
    }"""
    result = parse_supervised_response(raw)
    assert result is not None
    assert result.problem_summary == "Implement binary search"
    assert result.current_step.step_number == 1
    assert result.current_step.requirements == [
        "accept sorted list",
        "return index or -1",
    ]
    assert result.total_steps == 4


def test_parse_json_with_markdown_fences() -> None:
    raw = """```json
{
  "problem_summary": "X",
  "current_step": {
    "step_number": 1,
    "goal": "Y",
    "requirements": [],
    "hints": [],
    "questions": []
  },
  "total_steps": 2,
  "progress_note": ""
}
```"""
    result = parse_supervised_response(raw)
    assert result is not None
    assert result.problem_summary == "X"
    assert result.total_steps == 2


def test_parse_invalid_json_returns_none() -> None:
    assert parse_supervised_response("not json at all") is None


def test_parse_non_dict_json_returns_none() -> None:
    assert parse_supervised_response("[1, 2, 3]") is None


def test_parse_missing_fields_uses_defaults() -> None:
    raw = (
        '{"problem_summary": "X", '
        '"current_step": {"step_number": 1, "goal": "Y"}, '
        '"total_steps": 1}'
    )
    result = parse_supervised_response(raw)
    assert result is not None
    assert result.current_step.requirements == []
    assert result.progress_note == ""
