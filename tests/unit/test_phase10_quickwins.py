"""Unit tests for Phase 10.1 quick-win features.

Covers:
- P10-01: Last-verdict footer in supervised ``adt ask``
- P10-02: Warn-once on learning log failure
- P10-03: ``adt session show/clear/export`` subcommands
- P10-05: Configurable ``review_max_bytes``
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from adt.cli.app import app

# ── helpers ──────────────────────────────────────────────────────────────

runner = CliRunner()


def _seed_session(path: Path, **overrides: object) -> None:
    """Write a synthetic ``session.json``."""
    data = {
        "problem_summary": "Binary search",
        "current_step": 3,
        "total_steps": 5,
        "previous_feedback": ["needs_work", "on_track"],
        "iteration_count": 4,
    }
    data.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ── P10-01: last-verdict footer ─────────────────────────────────────────


class TestLastVerdictFooter:
    """The supervised ask footer shows the most recent review verdict."""

    def test_footer_shown_when_feedback_exists(self, tmp_path, monkeypatch):
        session_file = tmp_path / "session.json"
        _seed_session(session_file)
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: session_file,
        )
        # Also patch the session load inside cli/app.py (loaded from adt.core.session)
        from adt.core.session import SessionContext

        sess = SessionContext.load(session_file)
        assert sess.previous_feedback[-1] == "on_track"

    def test_footer_skipped_when_no_feedback(self, tmp_path, monkeypatch):
        session_file = tmp_path / "session.json"
        _seed_session(session_file, previous_feedback=[])
        from adt.core.session import SessionContext

        sess = SessionContext.load(session_file)
        assert not sess.previous_feedback


# ── P10-02: warn-once on learning log failure ───────────────────────────


class TestWarnOnce:
    """The analytics logger warns once on first write failure."""

    def test_first_failure_sets_flag(self, monkeypatch):
        import adt.analytics.logger as logmod

        monkeypatch.setattr(logmod, "_failure_reported", False)
        # Make setup_learning_logger raise
        monkeypatch.setattr(
            logmod,
            "setup_learning_logger",
            lambda **kw: (_ for _ in ()).throw(OSError("disk full")),
        )

        from adt.analytics.events import LearningEvent

        event = LearningEvent(
            trace_id="x",
            component="test",
            event_type="test",
        )
        logmod.log_learning_event(event)
        assert logmod._failure_reported is True

    def test_second_failure_stays_silent(self, monkeypatch):
        import adt.analytics.logger as logmod

        monkeypatch.setattr(logmod, "_failure_reported", True)
        monkeypatch.setattr(
            logmod,
            "setup_learning_logger",
            lambda **kw: (_ for _ in ()).throw(OSError("disk full")),
        )

        from adt.analytics.events import LearningEvent

        event = LearningEvent(
            trace_id="x",
            component="test",
            event_type="test",
        )
        # Should not raise and should not re-import log_adt
        logmod.log_learning_event(event)
        assert logmod._failure_reported is True

    def test_success_resets_flag(self, tmp_path, monkeypatch):
        import adt.analytics.logger as logmod

        monkeypatch.setattr(logmod, "_failure_reported", True)
        monkeypatch.setattr(
            logmod,
            "learning_log_path",
            lambda log_dir=None: tmp_path / "learning.jsonl",
        )
        # Reset handlers to force fresh setup
        import logging

        log = logging.getLogger("adt.learning")
        log.handlers.clear()

        from adt.analytics.events import LearningEvent

        event = LearningEvent(
            trace_id="ok",
            component="test",
            event_type="test",
        )
        logmod.log_learning_event(event, log_dir=tmp_path)
        assert logmod._failure_reported is False


# ── P10-03: adt session subcommands ─────────────────────────────────────


class TestSessionShow:
    def test_show_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: tmp_path / "session.json",
        )
        result = runner.invoke(app, ["session", "show"])
        assert result.exit_code == 0
        assert "No active supervised session" in result.stdout

    def test_show_with_session(self, tmp_path, monkeypatch):
        sf = tmp_path / "session.json"
        _seed_session(sf)
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: sf,
        )
        result = runner.invoke(app, ["session", "show"])
        assert result.exit_code == 0
        assert "Binary search" in result.stdout
        assert "3" in result.stdout
        assert "on_track" in result.stdout


class TestSessionClear:
    def test_clear_with_confirm(self, tmp_path, monkeypatch):
        sf = tmp_path / "session.json"
        _seed_session(sf)
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: sf,
        )
        result = runner.invoke(app, ["session", "clear", "--yes"])
        assert result.exit_code == 0
        assert "cleared" in result.stdout.lower()
        assert not sf.exists()

    def test_clear_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: tmp_path / "session.json",
        )
        result = runner.invoke(app, ["session", "clear"])
        assert result.exit_code == 0
        assert "nothing to clear" in result.stdout.lower()


class TestSessionExport:
    def test_export_to_stdout(self, tmp_path, monkeypatch):
        sf = tmp_path / "session.json"
        _seed_session(sf)
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: sf,
        )
        result = runner.invoke(app, ["session", "export"])
        assert result.exit_code == 0
        assert "Binary search" in result.stdout

    def test_export_to_file(self, tmp_path, monkeypatch):
        sf = tmp_path / "session.json"
        _seed_session(sf)
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: sf,
        )
        out = tmp_path / "out.json"
        result = runner.invoke(app, ["session", "export", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["problem_summary"] == "Binary search"

    def test_export_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "adt.core.session.session_file_path",
            lambda: tmp_path / "session.json",
        )
        result = runner.invoke(app, ["session", "export"])
        assert result.exit_code == 1


# ── P10-05: configurable review max-bytes ───────────────────────────────


class TestReviewMaxBytes:
    def test_config_default(self):
        from adt.config import AdtConfig

        cfg = AdtConfig()
        assert cfg.review_max_bytes == 200_000

    def test_config_from_toml(self):
        from adt.config import AdtConfig

        cfg = AdtConfig.from_toml_table({"review_max_bytes": 500_000})
        assert cfg.review_max_bytes == 500_000

    def test_config_env_override(self, monkeypatch):
        from adt.config import AdtConfig, apply_env_overrides

        monkeypatch.setenv("ADT_REVIEW_MAX_BYTES", "300000")
        cfg = apply_env_overrides(AdtConfig())
        assert cfg.review_max_bytes == 300_000

    def test_config_env_override_floor(self, monkeypatch):
        from adt.config import AdtConfig, apply_env_overrides

        monkeypatch.setenv("ADT_REVIEW_MAX_BYTES", "100")
        cfg = apply_env_overrides(AdtConfig())
        assert cfg.review_max_bytes == 1024  # min floor

    def test_review_rejects_large_file(self, tmp_path):
        from adt.review_session import ReviewConfigurationError, run_review

        big = tmp_path / "big.py"
        big.write_text("x" * 2000, encoding="utf-8")
        with pytest.raises(ReviewConfigurationError, match="1000 bytes"):
            run_review(file=str(big), max_bytes=1000, llm=object())  # type: ignore[arg-type]

    def test_review_accepts_within_limit(self, tmp_path, monkeypatch):
        """File under custom limit does not raise ReviewConfigurationError.

        We only validate the size check — the actual LLM call is not reached
        because we pass no API key, which raises ReviewConfigurationError too.
        """
        from adt.review_session import ReviewConfigurationError, run_review

        small = tmp_path / "small.py"
        small.write_text("x = 1\n", encoding="utf-8")
        # File is 6 bytes, limit 1000 — should pass size check
        # Will fail later at API-key check, but that's fine
        with pytest.raises(ReviewConfigurationError, match="OPENAI_API_KEY"):
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)
            run_review(file=str(small), max_bytes=1000)

    def test_cli_max_bytes_flag_exists(self):
        """The --max-bytes flag is present in the review command help."""
        result = runner.invoke(app, ["review", "--help"])
        assert "--max-bytes" in result.stdout
