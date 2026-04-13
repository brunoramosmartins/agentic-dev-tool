"""Unit tests for Phase 10.3 — Reach & Parity.

Covers:
- P10-10: HTTP parity for supervised + trace (POST /ask, POST /review)
- P10-11: /stats and /sessions endpoints
- P10-12: Stats export (CSV / JSON / Markdown)
- P10-13: Strict ``adt config set`` validator
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from adt.api.server import app as api_app
from adt.cli.app import app as cli_app

client = TestClient(api_app)
runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── P10-10: HTTP parity ────────────────────────────────────────────────


class TestPostAskParity:
    """POST /ask now accepts mode, level, trace, session."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False)
    @patch("adt.api.server.run_ask")
    def test_supervised_fields_in_request(self, mock_run: MagicMock) -> None:
        from adt.ask_session import AskExecution
        from adt.models.schemas import AgentResponse

        mock_run.return_value = AskExecution(
            response=AgentResponse(
                answer="step guidance",
                routed_agent="supervisor",
            ),
            runner=MagicMock(last_token_usage={}),
        )
        res = client.post(
            "/ask",
            json={
                "query": "binary search",
                "mode": "supervised",
                "level": "beginner",
                "session": "algo",
            },
        )
        assert res.status_code == 200
        mock_run.assert_called_once()
        call_kw = mock_run.call_args
        assert call_kw.kwargs["mode"] == "supervised"
        assert call_kw.kwargs["level"] == "beginner"
        assert call_kw.kwargs["session_name"] == "algo"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False)
    @patch("adt.api.server.run_ask")
    def test_supervised_response_in_output(self, mock_run: MagicMock) -> None:
        from adt.ask_session import AskExecution
        from adt.models.schemas import (
            AgentResponse,
            SupervisedResponse,
            SupervisedStep,
        )

        sup = SupervisedResponse(
            problem_summary="Two-sum",
            current_step=SupervisedStep(step_number=1, goal="define fn"),
            total_steps=3,
        )
        mock_run.return_value = AskExecution(
            response=AgentResponse(answer="{}"),
            runner=MagicMock(last_token_usage={}),
            supervised_response=sup,
        )
        res = client.post("/ask", json={"query": "two-sum", "mode": "supervised"})
        assert res.status_code == 200
        body = res.json()
        assert body["supervised_response"] is not None
        assert body["supervised_response"]["problem_summary"] == "Two-sum"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False)
    @patch("adt.api.server.run_ask")
    def test_trace_events_in_output(self, mock_run: MagicMock) -> None:
        from adt.ask_session import AskExecution
        from adt.models.schemas import AgentResponse
        from adt.tracing.context import TraceContext

        tc = TraceContext()
        tc.emit("test", "test_event", data={"key": "value"})
        mock_run.return_value = AskExecution(
            response=AgentResponse(answer="ok"),
            runner=MagicMock(last_token_usage={}),
            trace_context=tc,
        )
        res = client.post("/ask", json={"query": "x", "trace": True})
        assert res.status_code == 200
        body = res.json()
        assert body["trace_events"] is not None
        assert len(body["trace_events"]) >= 1

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False)
    @patch("adt.api.server.run_ask")
    def test_defaults_no_supervised_or_trace(self, mock_run: MagicMock) -> None:
        from adt.ask_session import AskExecution
        from adt.models.schemas import AgentResponse

        mock_run.return_value = AskExecution(
            response=AgentResponse(answer="hi"),
            runner=MagicMock(last_token_usage={}),
        )
        res = client.post("/ask", json={"query": "hello"})
        body = res.json()
        assert body["supervised_response"] is None
        assert body["trace_events"] is None


class TestPostReview:
    """POST /review accepts file_content directly."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False)
    @patch("adt.review_session.run_review")
    def test_review_success(self, mock_review: MagicMock) -> None:
        from adt.core.session import SessionContext
        from adt.models.schemas import ReviewFeedback
        from adt.review_session import ReviewExecution

        fb = ReviewFeedback(
            next_step="fix the bug",
            overall_assessment="on_track",
        )
        mock_review.return_value = ReviewExecution(
            feedback=fb,
            raw_answer="{}",
            session=SessionContext(problem_summary="test"),
        )
        res = client.post(
            "/review",
            json={
                "file_content": "def foo(): pass",
                "context": "should return 1",
                "level": "beginner",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["feedback"] is not None
        assert body["feedback"]["overall_assessment"] == "on_track"
        assert body["session"]["problem_summary"] == "test"

    @patch("adt.review_session.run_review")
    def test_review_missing_key(self, mock_review: MagicMock) -> None:
        from adt.review_session import ReviewConfigurationError

        mock_review.side_effect = ReviewConfigurationError(
            "Missing OPENAI_API_KEY."
        )
        res = client.post("/review", json={"file_content": "x=1"})
        assert res.status_code == 503


# ── P10-11: /stats and /sessions ───────────────────────────────────────


class TestGetStats:
    def test_stats_endpoint_returns_200(self) -> None:
        """The /stats endpoint returns valid JSON with expected keys."""
        res = client.get("/stats")
        assert res.status_code == 200
        body = res.json()
        assert "sessions" in body
        assert "reviews" in body
        assert "assessments" in body


class TestSessions:
    def test_list_sessions(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "adt.core.session_store.ensure_adt_dir", lambda: tmp_path
        )
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "alpha.json").write_text("{}", encoding="utf-8")
        (sessions_dir / "beta.json").write_text("{}", encoding="utf-8")
        res = client.get("/sessions")
        assert res.status_code == 200
        assert res.json() == ["alpha", "beta"]

    def test_get_session(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "adt.core.session_store.ensure_adt_dir", lambda: tmp_path
        )
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        data = {
            "problem_summary": "sorting",
            "current_step": 2,
            "total_steps": 5,
            "previous_feedback": ["on_track"],
            "iteration_count": 3,
        }
        (sessions_dir / "algo.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        res = client.get("/sessions/algo")
        assert res.status_code == 200
        body = res.json()
        assert body["problem_summary"] == "sorting"
        assert body["current_step"] == 2

    def test_get_session_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "adt.core.session_store.ensure_adt_dir", lambda: tmp_path
        )
        res = client.get("/sessions/nonexistent")
        assert res.status_code == 200  # returns empty session
        assert res.json()["current_step"] == 0

    def test_delete_session(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "adt.core.session_store.ensure_adt_dir", lambda: tmp_path
        )
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        sf = sessions_dir / "temp.json"
        sf.write_text("{}", encoding="utf-8")
        res = client.delete("/sessions/temp")
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"
        assert not sf.exists()

    def test_delete_session_missing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "adt.core.session_store.ensure_adt_dir", lambda: tmp_path
        )
        res = client.delete("/sessions/ghost")
        assert res.status_code == 404


# ── P10-12: Stats export ──────────────────────────────────────────────


class TestStatsExport:
    """CSV, JSON, and Markdown export from exporter module."""

    def _sample_stats(self):
        from adt.analytics.stats import LearningStats

        return LearningStats(
            sessions=3,
            reviews=5,
            supervised_steps=10,
            avg_steps_per_session=3.5,
            avg_iterations_per_step=2.0,
            common_issues=[("off_by_one", 4), ("naming", 2)],
            improvement_trend=[3.0, 2.5, 1.5],
            total_tokens=1200,
            assessments={"on_track": 3, "needs_work": 2},
        )

    def test_export_json(self) -> None:
        from adt.analytics.exporter import export_json

        out = export_json(self._sample_stats())
        data = json.loads(out)
        assert data["sessions"] == 3
        assert data["reviews"] == 5
        assert data["total_tokens"] == 1200

    def test_export_csv(self) -> None:
        from adt.analytics.exporter import export_csv

        out = export_csv(self._sample_stats())
        lines = out.strip().split("\n")
        assert len(lines) == 2  # header + data
        assert "sessions" in lines[0]
        assert "3" in lines[1]

    def test_export_markdown(self) -> None:
        from adt.analytics.exporter import export_markdown

        out = export_markdown(self._sample_stats())
        assert "# Learning Stats" in out
        assert "| Sessions | 3 |" in out
        assert "off_by_one" in out
        assert "→" in out  # trend arrow

    def test_cli_export_json(self) -> None:
        result = runner.invoke(cli_app, ["stats", "--export", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "sessions" in data

    def test_cli_export_csv(self) -> None:
        result = runner.invoke(cli_app, ["stats", "--export", "csv"])
        assert result.exit_code == 0
        assert "sessions" in result.stdout

    def test_cli_export_md(self) -> None:
        result = runner.invoke(cli_app, ["stats", "--export", "md"])
        assert result.exit_code == 0
        assert "# Learning Stats" in result.stdout

    def test_cli_export_to_file(self, tmp_path: Path) -> None:
        out = tmp_path / "stats.json"
        result = runner.invoke(
            cli_app, ["stats", "--export", "json", "--out", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "sessions" in data

    def test_cli_export_invalid_format(self) -> None:
        result = runner.invoke(cli_app, ["stats", "--export", "xml"])
        assert result.exit_code == 1

    def test_cli_export_flag_exists(self) -> None:
        result = runner.invoke(cli_app, ["stats", "--help"])
        assert "--export" in _strip_ansi(result.stdout)


# ── P10-13: Config validator ──────────────────────────────────────────


class TestConfigValidator:
    """Strict validation of ``adt config set`` key-value pairs."""

    def test_unknown_key_rejected(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="Unknown"):
            validate_key_value("nonexistent_key", "value")

    def test_valid_log_level(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("log_level", "DEBUG")  # should not raise

    def test_invalid_log_level(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="Invalid log level"):
            validate_key_value("log_level", "VERBOSE")

    def test_valid_cache_ttl(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("cache_ttl_seconds", "60.5")

    def test_invalid_cache_ttl_nan(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="number"):
            validate_key_value("cache_ttl_seconds", "abc")

    def test_negative_cache_ttl(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="non-negative"):
            validate_key_value("cache_ttl_seconds", "-1")

    def test_valid_use_llm_routing(self) -> None:
        from adt.config_validator import validate_key_value

        for val in ("true", "false", "1", "0", "yes", "no"):
            validate_key_value("use_llm_routing", val)

    def test_invalid_use_llm_routing(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="boolean"):
            validate_key_value("use_llm_routing", "maybe")

    def test_valid_max_tool_iterations(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("max_tool_iterations", "10")

    def test_invalid_max_tool_iterations(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="positive integer"):
            validate_key_value("max_tool_iterations", "abc")

    def test_valid_token_budget(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("token_budget", "50000")
        validate_key_value("token_budget", "none")

    def test_invalid_token_budget(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="integer"):
            validate_key_value("token_budget", "abc")

    def test_valid_review_max_bytes(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("review_max_bytes", "200000")

    def test_review_max_bytes_too_small(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="1024"):
            validate_key_value("review_max_bytes", "512")

    def test_valid_agent_chain(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("agent_chain", "repo_agent,research_agent")

    def test_invalid_agent_chain(self) -> None:
        from adt.config_validator import ConfigValidationError, validate_key_value

        with pytest.raises(ConfigValidationError, match="Invalid agent"):
            validate_key_value("agent_chain", "repo_agent,fake_agent")

    def test_valid_default_model(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("default_model", "gpt-4o")

    def test_valid_routing_model(self) -> None:
        from adt.config_validator import validate_key_value

        validate_key_value("routing_model", "gpt-4o-mini")

    def test_cli_rejects_unknown_key(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("adt.config.adt_config_path", lambda: tmp_path / "c.toml")
        result = runner.invoke(cli_app, ["config", "set", "bogus_key", "val"])
        assert result.exit_code == 1
        assert "Unknown" in result.stdout or "Unknown" in (result.stderr or "")

    def test_cli_rejects_bad_value(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("adt.config.adt_config_path", lambda: tmp_path / "c.toml")
        result = runner.invoke(cli_app, ["config", "set", "log_level", "VERBOSE"])
        assert result.exit_code == 1
