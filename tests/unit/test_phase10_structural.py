"""Unit tests for Phase 10.2 — Structural Hardening.

Covers:
- P10-06: Named sessions via ``SessionStore``
- P10-07: Formal ``SkillContext`` model and ``load_skill_context()``
- P10-08: Decoupled ``LearningEvent`` (schema v2, v1 compat)
- P10-09: ``RunnerConfig`` Pydantic model and ``build_runner()`` integration
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ── P10-06: SessionStore ────────────────────────────────────────────────


class TestSessionStore:
    """Named session CRUD and migration."""

    def test_list_empty(self, tmp_path: Path) -> None:
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        assert store.list() == []

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        from adt.core.session import SessionContext
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        ctx = SessionContext(problem_summary="Two-sum", current_step=2, total_steps=4)
        store.save(ctx, "two-sum")
        loaded = store.load("two-sum")
        assert loaded.problem_summary == "Two-sum"
        assert loaded.current_step == 2

    def test_list_sorted(self, tmp_path: Path) -> None:
        from adt.core.session import SessionContext
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        for name in ("zebra", "alpha", "mid"):
            store.save(SessionContext(problem_summary=name), name)
        assert store.list() == ["alpha", "mid", "zebra"]

    def test_delete(self, tmp_path: Path) -> None:
        from adt.core.session import SessionContext
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        store.save(SessionContext(), "temp")
        assert "temp" in store.list()
        store.delete("temp")
        assert "temp" not in store.list()

    def test_delete_missing_is_noop(self, tmp_path: Path) -> None:
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        store.delete("nonexistent")  # should not raise

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        ctx = store.load("ghost")
        assert ctx.is_empty()

    def test_slug_sanitization(self, tmp_path: Path) -> None:
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        p = store.path("My Session")
        assert p.name == "my-session.json"

    def test_slug_rejects_traversal(self, tmp_path: Path) -> None:
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        with pytest.raises(ValueError, match="path traversal"):
            store.path("../evil")

    def test_slug_rejects_empty(self, tmp_path: Path) -> None:
        from adt.core.session_store import SessionStore

        store = SessionStore(base_dir=tmp_path / "sessions")
        with pytest.raises(ValueError, match="empty"):
            store.path("   ")

    def test_migrate_legacy(self, tmp_path: Path) -> None:
        """Legacy ``session.json`` is moved into ``sessions/default.json``."""
        from adt.core.session_store import SessionStore

        legacy = tmp_path / "session.json"
        legacy.write_text(
            json.dumps({"problem_summary": "legacy", "current_step": 1}),
            encoding="utf-8",
        )
        store = SessionStore(base_dir=tmp_path / "sessions")
        assert not legacy.exists()
        ctx = store.load("default")
        assert ctx.problem_summary == "legacy"

    def test_migrate_skipped_when_target_exists(self, tmp_path: Path) -> None:
        """Migration must not overwrite an existing ``default.json``."""
        from adt.core.session_store import SessionStore

        legacy = tmp_path / "session.json"
        legacy.write_text('{"problem_summary": "old"}', encoding="utf-8")
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        target = sessions_dir / "default.json"
        target.write_text('{"problem_summary": "new"}', encoding="utf-8")
        SessionStore(base_dir=sessions_dir)
        # legacy not removed, target not overwritten
        assert legacy.exists()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["problem_summary"] == "new"


# ── P10-07: SkillContext ────────────────────────────────────────────────


class TestSkillContext:
    """Formal skill envelope and version parsing."""

    def test_parse_version_present(self) -> None:
        from adt.skills.context import parse_version

        md = "<!-- version: 3 -->\n# Skill Title"
        assert parse_version(md) == "3"

    def test_parse_version_missing(self) -> None:
        from adt.skills.context import parse_version

        assert parse_version("# No version here") == "0"

    def test_skill_context_creation(self) -> None:
        from adt.skills.context import SkillContext

        ctx = SkillContext(name="test", markdown="# Test", version="2")
        assert ctx.name == "test"
        assert ctx.version == "2"

    def test_skill_context_rejects_extra_fields(self) -> None:
        from adt.skills.context import SkillContext

        with pytest.raises(Exception):  # noqa: B017
            SkillContext(name="x", markdown="y", bogus="z")

    def test_load_skill_context_from_path(self, tmp_path: Path) -> None:
        from adt.skills.supervised_engineering.loader import load_skill_context

        md = tmp_path / "SKILL.md"
        md.write_text("<!-- version: 5 -->\n# Custom Skill\n", encoding="utf-8")
        ctx = load_skill_context(path=md, use_cache=False)
        assert ctx.name == "supervised_engineering"
        assert ctx.version == "5"
        assert "Custom Skill" in ctx.markdown

    def test_load_skill_context_packaged(self) -> None:
        """Loading from the installed package should return version >= 1."""
        from adt.skills.supervised_engineering.loader import load_skill_context

        ctx = load_skill_context(use_cache=False)
        assert ctx.name == "supervised_engineering"
        assert int(ctx.version) >= 1

    def test_supervised_prompt_uses_skill_ctx(self) -> None:
        from adt.core.supervised_supervisor import build_supervised_system_prompt
        from adt.skills.context import SkillContext

        ctx = SkillContext(name="mock", markdown="INJECTED_SKILL_BODY")
        prompt = build_supervised_system_prompt("beginner", skill_ctx=ctx)
        assert "INJECTED_SKILL_BODY" in prompt
        assert "beginner" in prompt

    def test_review_prompt_uses_skill_ctx(self) -> None:
        from adt.core.supervised_supervisor import build_review_system_prompt
        from adt.skills.context import SkillContext

        ctx = SkillContext(name="mock", markdown="REVIEW_SKILL_BODY")
        prompt = build_review_system_prompt("advanced", skill_ctx=ctx)
        assert "REVIEW_SKILL_BODY" in prompt
        assert "advanced" in prompt


# ── P10-08: LearningEvent v2 ───────────────────────────────────────────


class TestLearningEventV2:
    """Standalone LearningEvent decoupled from TraceEvent."""

    def test_all_fields_optional(self) -> None:
        from adt.analytics.events import LearningEvent

        ev = LearningEvent()
        assert ev.schema_version == 2
        assert ev.trace_id is None
        assert ev.session_name is None
        assert ev.component == ""

    def test_with_session_name(self) -> None:
        from adt.analytics.events import LearningEvent

        ev = LearningEvent(
            session_name="algo-practice",
            component="reviewer",
            event_type="code_review",
        )
        assert ev.session_name == "algo-practice"

    def test_v1_compat_roundtrip(self) -> None:
        """A v1-style dict (with trace_id, no session_name) should parse."""
        from adt.analytics.events import LearningEvent

        v1_data = {
            "trace_id": "abc123",
            "component": "supervisor",
            "event_type": "supervised_step",
            "step_id": 2,
            "problem_summary": "Binary search",
            "schema_version": 1,
        }
        ev = LearningEvent.model_validate(v1_data)
        assert ev.trace_id == "abc123"
        assert ev.session_name is None
        assert ev.schema_version == 1

    def test_serialization_includes_session_name(self) -> None:
        from adt.analytics.events import LearningEvent

        ev = LearningEvent(session_name="my-session", component="test")
        data = ev.model_dump(mode="json")
        assert data["session_name"] == "my-session"
        assert data["schema_version"] == 2

    def test_categorize_issue_unchanged(self) -> None:
        from adt.analytics.events import categorize_issue
        from adt.models.schemas import CodeIssue

        issue = CodeIssue(
            severity="warning",
            description="off-by-one in loop bound",
        )
        assert categorize_issue(issue) == "off_by_one"


# ── P10-09: RunnerConfig ───────────────────────────────────────────────


class TestRunnerConfig:
    """Pydantic config model for ``build_runner()``."""

    def test_defaults(self, tmp_path: Path) -> None:
        from adt.core.runner_config import RunnerConfig

        cfg = RunnerConfig(repo_roots=tmp_path)
        assert cfg.model == "gpt-4o-mini"
        assert cfg.max_tool_iterations == 5
        assert cfg.use_context_cache is True
        assert cfg.agent_chain == []

    def test_from_legacy(self, tmp_path: Path) -> None:
        from adt.core.runner_config import RunnerConfig

        cfg = RunnerConfig.from_legacy(
            tmp_path,
            model="gpt-4o",
            max_tool_iterations=10,
        )
        assert cfg.model == "gpt-4o"
        assert cfg.max_tool_iterations == 10
        assert cfg.repo_roots == tmp_path

    def test_dict_repo_roots(self, tmp_path: Path) -> None:
        from adt.core.runner_config import RunnerConfig

        roots = {"r0": tmp_path, "r1": tmp_path}
        cfg = RunnerConfig(repo_roots=roots, primary_repo_key="r1")
        assert cfg.primary_repo_key == "r1"
        assert len(cfg.repo_roots) == 2

    def test_build_runner_accepts_config(self, tmp_path: Path) -> None:
        """``build_runner()`` should accept a ``RunnerConfig`` object."""
        from adt.bootstrap import build_runner
        from adt.core.runner_config import RunnerConfig

        cfg = RunnerConfig(repo_roots=tmp_path, api_key="sk-test")
        runner = build_runner(cfg)
        assert runner is not None

    def test_build_runner_legacy_still_works(self, tmp_path: Path) -> None:
        """Legacy keyword-arg calling convention must keep working."""
        from adt.bootstrap import build_runner

        runner = build_runner(tmp_path, api_key="sk-test")
        assert runner is not None
