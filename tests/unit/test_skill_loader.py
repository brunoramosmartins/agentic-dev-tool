"""Unit tests for the supervised engineering skill loader."""

from __future__ import annotations

from pathlib import Path

from adt.skills.supervised_engineering import (
    SKILL_FILENAME,
    SKILL_NAME,
    load_skill_content,
)
from adt.skills.supervised_engineering.loader import reset_cache


def test_skill_constants() -> None:
    assert SKILL_NAME == "supervised_engineering"
    assert SKILL_FILENAME == "SKILL.md"


def test_packaged_skill_loads_and_contains_sections() -> None:
    reset_cache()
    content = load_skill_content()
    assert "# Supervised Engineering Skill" in content
    assert "Teaching Heuristics" in content
    assert "Decomposition Patterns" in content
    assert "Feedback Guidelines" in content
    assert "Anti-Patterns" in content
    assert "When to Use" in content
    assert "When NOT to Use" in content


def test_packaged_skill_is_cached() -> None:
    reset_cache()
    first = load_skill_content()
    second = load_skill_content()
    assert first == second
    # Same identity thanks to the module-level cache
    assert first is second


def test_path_override_bypasses_cache(tmp_path: Path) -> None:
    reset_cache()
    load_skill_content()  # populate cache
    custom = tmp_path / "SKILL.md"
    custom.write_text("# Custom skill body\n", encoding="utf-8")
    out = load_skill_content(path=custom)
    assert out == "# Custom skill body\n"
    # Original cache still intact for the packaged path
    assert "# Supervised Engineering Skill" in load_skill_content()


def test_missing_path_returns_fallback(tmp_path: Path) -> None:
    out = load_skill_content(path=tmp_path / "nope.md")
    assert "fallback" in out.lower()


def test_use_cache_false_rereads_package() -> None:
    reset_cache()
    a = load_skill_content(use_cache=False)
    b = load_skill_content(use_cache=False)
    assert a == b
    assert "Teaching Heuristics" in a
