"""Tests for Phase 10.6 — Interactive Terminal Experience (P10-20..P10-25)."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

# ── P10-20: StatusReporter ────────────────────────────────────────────


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=120)


def test_status_reporter_records_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    """StatusReporter should record phase labels even when disabled."""
    monkeypatch.setenv("ADT_NO_PROGRESS", "1")
    from adt.cli.status import StatusReporter

    c = _make_console()
    sr = StatusReporter(c)
    with sr.live():
        sr.routing()
        sr.calling_agent("repo_agent")
        sr.running_tool("read_file")
        sr.iteration(2, 5)

    assert "Routing..." in sr.phases
    assert "Calling repo_agent..." in sr.phases
    assert "Running tool: read_file" in sr.phases
    assert "Iteration 2/5..." in sr.phases


def test_status_disabled_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.status import _progress_enabled

    monkeypatch.setenv("ADT_NO_PROGRESS", "1")
    assert not _progress_enabled()


def test_status_disabled_no_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.status import _progress_enabled

    monkeypatch.delenv("ADT_NO_PROGRESS", raising=False)
    # StringIO has no isatty — non-tty
    import sys

    orig = sys.stdout
    sys.stdout = StringIO()
    try:
        assert not _progress_enabled()
    finally:
        sys.stdout = orig


def test_status_building_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADT_NO_PROGRESS", "1")
    from adt.cli.status import StatusReporter

    sr = StatusReporter(_make_console())
    with sr.live():
        sr.building_context()

    assert "Building context..." in sr.phases


# ── P10-21: Streaming ────────────────────────────────────────────────


def test_run_chunk_dataclass() -> None:
    from adt.cli.streaming import RunChunk

    chunk = RunChunk(kind="token", text="Hello")
    assert chunk.kind == "token"
    assert chunk.text == "Hello"
    assert chunk.tool_name == ""


def test_run_chunk_tool_events() -> None:
    from adt.cli.streaming import RunChunk

    start = RunChunk(kind="tool_call_start", tool_name="read_file")
    end = RunChunk(kind="tool_call_end", tool_name="read_file")
    assert start.tool_name == "read_file"
    assert end.kind == "tool_call_end"


def test_stream_renderer_accumulates(monkeypatch: pytest.MonkeyPatch) -> None:
    """StreamRenderer should accumulate token chunks into final text."""
    from adt.cli.streaming import RunChunk, StreamRenderer

    # Use non-tty console so Live doesn't actually render
    monkeypatch.setenv("ADT_NO_PROGRESS", "1")
    c = Console(file=StringIO(), force_terminal=False, width=80)
    renderer = StreamRenderer(c)

    chunks = iter(
        [
            RunChunk(kind="token", text="Hello "),
            RunChunk(kind="token", text="world"),
            RunChunk(kind="final", text=""),
        ]
    )
    result = renderer.render_stream(chunks)
    assert result == "Hello world"


def test_stream_renderer_final_override() -> None:
    """When final chunk has text, it replaces the buffer."""
    from adt.cli.streaming import RunChunk, StreamRenderer

    c = Console(file=StringIO(), force_terminal=False, width=80)
    renderer = StreamRenderer(c)

    chunks = iter(
        [
            RunChunk(kind="token", text="partial "),
            RunChunk(kind="final", text="Complete answer"),
        ]
    )
    result = renderer.render_stream(chunks)
    assert result == "Complete answer"


# ── P10-22: Progress bars ────────────────────────────────────────────


def test_null_progress_reporter_records_calls() -> None:
    from adt.cli.progress import NullProgressReporter

    p = NullProgressReporter()
    p.start("Reading files", 10)
    for i in range(1, 4):
        p.step(i, 10)
    p.finish()
    assert len(p.calls) == 3
    assert p.calls[0] == (1, 10)


def test_rich_progress_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADT_NO_PROGRESS", "1")
    from adt.cli.progress import RichProgressReporter

    p = RichProgressReporter(_make_console())
    p.start("test", 5)
    p.step(1, 5)
    p.finish()
    assert p.calls == [(1, 5)]


def test_progress_callback_protocol() -> None:
    """ProgressCallback should accept (int, int) -> None."""
    from adt.cli.progress import NullProgressReporter, ProgressCallback

    p = NullProgressReporter()
    # Should satisfy the protocol
    cb: ProgressCallback = p.step
    cb(1, 5)
    assert p.calls == [(1, 5)]


# ── P10-23: Cost confirmation ────────────────────────────────────────


def test_should_confirm_below_threshold() -> None:
    from adt.cli.cost_confirm import _should_confirm

    assert not _should_confirm(0.01, 0.05)


def test_should_confirm_above_threshold() -> None:
    from adt.cli.cost_confirm import _should_confirm

    assert _should_confirm(0.10, 0.05)


def test_should_confirm_yes_flag_bypasses() -> None:
    from adt.cli.cost_confirm import _should_confirm

    assert not _should_confirm(0.10, 0.05, yes_flag=True)


def test_should_confirm_env_var_bypasses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from adt.cli.cost_confirm import _should_confirm

    monkeypatch.setenv("ADT_NO_CONFIRM", "1")
    assert not _should_confirm(0.10, 0.05)


def test_estimate_upper_bound() -> None:
    from adt.cli.cost_confirm import estimate_upper_bound

    cost = estimate_upper_bound("gpt-4o-mini", 1000, 500)
    assert cost > 0
    assert isinstance(cost, float)


def test_confirm_cost_below_threshold() -> None:
    from adt.cli.cost_confirm import confirm_cost

    c = _make_console()
    # Low cost → should pass without prompt
    result = confirm_cost(c, "gpt-4o-mini", 100, 100, threshold=1.0)
    assert result is True


def test_confirm_cost_yes_flag() -> None:
    from adt.cli.cost_confirm import confirm_cost

    c = _make_console()
    # High cost but --yes flag
    result = confirm_cost(c, "gpt-4o", 100000, 50000, threshold=0.001, yes_flag=True)
    assert result is True


def test_config_cost_confirm_threshold() -> None:
    from adt.config import AdtConfig

    cfg = AdtConfig()
    assert cfg.cost_confirm_threshold == 0.05

    cfg2 = AdtConfig(cost_confirm_threshold=0.10)
    table = cfg2.to_toml_table()
    assert table["cost_confirm_threshold"] == 0.10

    restored = AdtConfig.from_toml_table(table)
    assert restored.cost_confirm_threshold == 0.10


def test_config_update_cost_threshold(tmp_path: Path) -> None:
    from adt.config import (
        AdtConfig,
        load_config_file,
        save_config,
        update_config_key,
    )

    cfg_path = tmp_path / "config.toml"
    save_config(AdtConfig(), cfg_path)
    updated = update_config_key(cfg_path, "cost_confirm_threshold", "0.25")
    assert updated.cost_confirm_threshold == 0.25
    reloaded = load_config_file(cfg_path)
    assert reloaded.cost_confirm_threshold == 0.25


def test_config_validator_cost_threshold() -> None:
    from adt.config_validator import ConfigValidationError, validate_key_value

    validate_key_value("cost_confirm_threshold", "0.05")
    validate_key_value("cost_confirm_threshold", "0")

    with pytest.raises(ConfigValidationError, match="number"):
        validate_key_value("cost_confirm_threshold", "abc")

    with pytest.raises(ConfigValidationError, match="non-negative"):
        validate_key_value("cost_confirm_threshold", "-0.01")


# ── P10-24: Shell commands ───────────────────────────────────────────


def test_shell_state_defaults() -> None:
    from adt.cli.shell_commands import ShellState

    s = ShellState()
    assert s.active_session == "default"
    assert s.active_agent is None
    assert s.trace_enabled is False
    assert s.cost_threshold == 0.05


def test_dispatch_help() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    assert dispatch("/help", s, c) is True


def test_dispatch_version() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    assert dispatch("/version", s, c) is True


def test_dispatch_trace_on_off() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    dispatch("/trace on", s, c)
    assert s.trace_enabled is True
    dispatch("/trace off", s, c)
    assert s.trace_enabled is False


def test_dispatch_agent_force_and_clear() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    dispatch("/agent repo_agent", s, c)
    assert s.active_agent == "repo_agent"
    dispatch("/agent clear", s, c)
    assert s.active_agent is None


def test_dispatch_agent_invalid() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    s = ShellState()
    dispatch("/agent bogus_agent", s, c)
    assert s.active_agent is None  # not changed


def test_dispatch_cost() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    s = ShellState(cost_threshold=0.10)
    dispatch("/cost", s, c)
    output = buf.getvalue()
    assert "0.10" in output


def test_dispatch_exit() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    with pytest.raises(SystemExit):
        dispatch("/exit", s, c)


def test_dispatch_unknown_command() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    s = ShellState()
    assert dispatch("/bogus", s, c) is True  # handled (error printed)
    assert "Unknown command" in buf.getvalue()


def test_dispatch_non_slash_returns_false() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    assert dispatch("explain this code", s, c) is False


def test_dispatch_clear() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    # clear should not raise
    assert dispatch("/clear", s, c) is True


def test_dispatch_session_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    s = ShellState()

    monkeypatch.setattr(
        "adt.core.session_store.ensure_adt_dir",
        lambda: tmp_path,
    )
    dispatch("/session list", s, c)
    output = buf.getvalue()
    assert "No sessions" in output or "default" in output


def test_dispatch_session_switch() -> None:
    from adt.cli.shell_commands import ShellState, dispatch

    c = _make_console()
    s = ShellState()
    dispatch("/session switch my-session", s, c)
    assert s.active_session == "my-session"


def test_command_names_sorted() -> None:
    from adt.cli.shell_commands import COMMAND_NAMES

    assert sorted(COMMAND_NAMES) == COMMAND_NAMES
    assert "/help" in COMMAND_NAMES
    assert "/exit" in COMMAND_NAMES
    assert "/shell" not in COMMAND_NAMES


# ── P10-24: Shell REPL scaffold ──────────────────────────────────────


def test_shell_module_importable() -> None:
    import adt.cli.shell

    assert hasattr(adt.cli.shell, "run_shell")


def test_shell_history_path() -> None:
    from adt.cli.shell import _HISTORY_PATH

    assert _HISTORY_PATH.name == "shell_history"
    assert ".adt" in str(_HISTORY_PATH)


def test_build_completer_returns_object() -> None:
    from adt.cli.shell import _build_completer

    comp = _build_completer()
    assert comp is not None


# ── P10-25: CLI flags on ask_cmd ─────────────────────────────────────


def test_ask_cmd_accepts_yes_and_no_stream() -> None:
    """Verify --yes and --no-stream flags exist on ask_cmd."""
    from typer.testing import CliRunner

    from adt.cli.app import app

    runner = CliRunner()
    # Just check --help mentions them
    result = runner.invoke(app, ["ask", "--help"])
    assert "--yes" in result.output
    assert "--no-stream" in result.output


def test_shell_cmd_in_app() -> None:
    """Verify 'shell' is registered as a command."""
    from typer.testing import CliRunner

    from adt.cli.app import app

    runner = CliRunner()
    result = runner.invoke(app, ["shell", "--help"])
    assert result.exit_code == 0
    assert "interactive REPL" in result.output


# ── P10-20/P10-24: i18n locale keys ─────────────────────────────────


def test_all_en_keys_present_in_pt_br_phase10_6() -> None:
    """Every key in en.toml must also exist in pt_BR.toml."""
    from adt.cli.i18n import _load_locale

    _load_locale.cache_clear()
    en = _load_locale("en")
    pt = _load_locale("pt_BR")
    missing = set(en.keys()) - set(pt.keys())
    assert not missing, f"Keys missing from pt_BR.toml: {missing}"


# ── pyproject.toml ───────────────────────────────────────────────────


def test_shell_extra_in_pyproject() -> None:
    """pyproject.toml should define a [shell] extra with prompt-toolkit."""
    import tomli

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomli.loads(pyproject.read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]
    assert "shell" in extras
    shell_deps = " ".join(extras["shell"])
    assert "prompt-toolkit" in shell_deps
