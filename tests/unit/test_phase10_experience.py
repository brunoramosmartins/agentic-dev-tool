"""Tests for Phase 10.5 — Product Experience (P10-17, P10-18, P10-19)."""

from __future__ import annotations

from pathlib import Path

import pytest

# ── P10-17: MkDocs site ──────────────────────────────────────────────

_DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


def test_mkdocs_config_exists() -> None:
    """mkdocs.yml must be present in the docs directory."""
    assert (_DOCS_DIR / "mkdocs.yml").is_file()


def test_mkdocs_index_exists() -> None:
    """docs/index.md must be present."""
    assert (_DOCS_DIR / "index.md").is_file()


def test_mkdocs_getting_started_pages() -> None:
    assert (_DOCS_DIR / "getting-started" / "install.md").is_file()
    assert (_DOCS_DIR / "getting-started" / "quickstart.md").is_file()


def test_mkdocs_guide_pages() -> None:
    for page in ("supervised", "tracing", "analytics", "plugins"):
        path = _DOCS_DIR / "guides" / f"{page}.md"
        assert path.is_file(), f"missing guides/{page}.md"


def test_mkdocs_reference_pages() -> None:
    for page in ("architecture", "agents", "mcp", "skills"):
        path = _DOCS_DIR / "reference" / f"{page}.md"
        assert path.is_file(), f"missing reference/{page}.md"


def test_mkdocs_api_pages() -> None:
    for page in ("cli", "http"):
        assert (_DOCS_DIR / "api" / f"{page}.md").is_file(), f"missing api/{page}.md"


def test_github_workflow_docs_exists() -> None:
    wf = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "docs.yml"
    assert wf.is_file()


# ── P10-18: HTML dashboard ───────────────────────────────────────────


def test_html_export_contains_expected_sections() -> None:
    from adt.analytics.html_export import export_html
    from adt.analytics.stats import LearningStats

    stats = LearningStats(
        sessions=3,
        reviews=5,
        supervised_steps=10,
        avg_steps_per_session=3.3,
        avg_iterations_per_step=2.1,
        common_issues=[("naming", 4), ("complexity", 2)],
        assessments={"excellent": 2, "needs_work": 1, "on_track": 2},
        improvement_trend=[3.0, 2.5, 2.0],
        total_tokens=12345,
    )
    html = export_html(stats)
    assert "<!DOCTYPE html>" in html
    assert "Learning Stats Dashboard" in html
    assert "Sessions" in html
    assert "12,345" in html  # formatted token count
    assert "naming" in html
    assert "complexity" in html
    assert "excellent" in html
    assert "needs_work" in html


def test_html_export_sparkline_svg() -> None:
    from adt.analytics.html_export import _build_sparkline_svg

    svg = _build_sparkline_svg([1.0, 2.0, 3.0])
    assert "<svg" in svg
    assert "polyline" in svg
    assert 'class="sparkline"' in svg


def test_html_export_sparkline_empty() -> None:
    from adt.analytics.html_export import _build_sparkline_svg

    assert _build_sparkline_svg([]) == ""
    assert _build_sparkline_svg([1.0]) == ""


def test_html_export_empty_stats() -> None:
    from adt.analytics.html_export import export_html
    from adt.analytics.stats import LearningStats

    stats = LearningStats(
        sessions=0,
        reviews=0,
        supervised_steps=0,
        avg_steps_per_session=0.0,
        avg_iterations_per_step=0.0,
        common_issues=[],
        assessments={},
        improvement_trend=[],
        total_tokens=0,
    )
    html = export_html(stats)
    assert "<!DOCTYPE html>" in html
    # No sparkline when no trend
    assert "sparkline" not in html or "polyline" not in html


def test_stats_cmd_html_flag(tmp_path: Path) -> None:
    """--html flag should create an index.html file."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from adt.analytics.stats import LearningStats
    from adt.cli.app import app

    runner = CliRunner()
    fake_stats = LearningStats(
        sessions=1,
        reviews=1,
        supervised_steps=2,
        avg_steps_per_session=2.0,
        avg_iterations_per_step=1.0,
        common_issues=[],
        assessments={},
        improvement_trend=[],
        total_tokens=100,
    )
    with (
        patch("adt.analytics.read_learning_events", return_value=[]),
        patch("adt.analytics.compute_stats", return_value=fake_stats),
    ):
        html_dir = tmp_path / "dash"
        result = runner.invoke(app, ["stats", "--html", str(html_dir)])
    assert result.exit_code == 0
    assert (html_dir / "index.html").is_file()
    content = (html_dir / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


# ── P10-19: i18n ─────────────────────────────────────────────────────


def test_locale_en_loads() -> None:
    from adt.cli.i18n import _load_locale

    _load_locale.cache_clear()
    table = _load_locale("en")
    assert "stats.title" in table
    assert table["stats.title"] == "Learning Stats"


def test_locale_pt_br_loads() -> None:
    from adt.cli.i18n import _load_locale

    _load_locale.cache_clear()
    table = _load_locale("pt_BR")
    assert "stats.title" in table
    assert table["stats.title"] == "Estatísticas de Aprendizado"


def test_t_returns_english_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.i18n import reload_locale, t

    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()
    assert t("stats.title") == "Learning Stats"


def test_t_returns_portuguese_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.i18n import reload_locale, t

    monkeypatch.setenv("ADT_LANG", "pt_BR")
    reload_locale()
    result = t("stats.title")
    assert result == "Estatísticas de Aprendizado"
    # Restore
    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()


def test_t_fallback_to_en_for_unknown_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.i18n import reload_locale, t

    monkeypatch.setenv("ADT_LANG", "zz_ZZ")
    reload_locale()
    result = t("stats.title")
    assert result == "Learning Stats"
    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()


def test_t_fallback_to_key_for_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.i18n import reload_locale, t

    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()
    assert t("nonexistent.key.abc") == "nonexistent.key.abc"


def test_t_format_substitution(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.i18n import reload_locale, t

    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()
    result = t("session.cleared", name="test")
    assert result == "Session 'test' cleared."


def test_t_format_substitution_pt_br(monkeypatch: pytest.MonkeyPatch) -> None:
    from adt.cli.i18n import reload_locale, t

    monkeypatch.setenv("ADT_LANG", "pt_BR")
    reload_locale()
    result = t("session.cleared", name="teste")
    assert result == "Sessão 'teste' limpa."
    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()


def test_reload_locale_clears_cache() -> None:
    from adt.cli.i18n import _load_locale, reload_locale

    _load_locale("en")
    assert _load_locale.cache_info().currsize > 0
    reload_locale()
    assert _load_locale.cache_info().currsize == 0


def test_stats_renderer_uses_i18n(monkeypatch: pytest.MonkeyPatch) -> None:
    """StatsRenderer should use t() for labels — check pt_BR output."""
    from io import StringIO

    from rich.console import Console

    from adt.analytics.stats import LearningStats
    from adt.cli.i18n import reload_locale
    from adt.cli.stats_renderer import StatsRenderer

    monkeypatch.setenv("ADT_LANG", "pt_BR")
    reload_locale()

    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    stats = LearningStats(
        sessions=2,
        reviews=3,
        supervised_steps=5,
        avg_steps_per_session=2.5,
        avg_iterations_per_step=1.5,
        common_issues=[("naming", 2)],
        assessments={"excellent": 1},
        improvement_trend=[2.0, 1.5],
        total_tokens=500,
    )
    StatsRenderer(c).render(stats)
    output = buf.getvalue()
    # Panel title should be in Portuguese
    assert "Estatísticas de Aprendizado" in output
    # Labels should be in Portuguese
    assert "Sessões" in output
    assert "Revisões" in output

    monkeypatch.delenv("ADT_LANG", raising=False)
    reload_locale()


def test_config_lang_field() -> None:
    """AdtConfig should have a lang field defaulting to 'en'."""
    from adt.config import AdtConfig

    cfg = AdtConfig()
    assert cfg.lang == "en"

    cfg2 = AdtConfig(lang="pt_BR")
    assert cfg2.lang == "pt_BR"


def test_config_lang_round_trip() -> None:
    """lang should survive to_toml_table / from_toml_table."""
    from adt.config import AdtConfig

    cfg = AdtConfig(lang="pt_BR")
    table = cfg.to_toml_table()
    assert table["lang"] == "pt_BR"

    restored = AdtConfig.from_toml_table(table)
    assert restored.lang == "pt_BR"


def test_config_update_lang(tmp_path: Path) -> None:
    """update_config_key should persist lang changes."""
    from adt.config import AdtConfig, load_config_file, save_config, update_config_key

    cfg_path = tmp_path / "config.toml"
    save_config(AdtConfig(), cfg_path)

    updated = update_config_key(cfg_path, "lang", "pt_BR")
    assert updated.lang == "pt_BR"

    reloaded = load_config_file(cfg_path)
    assert reloaded.lang == "pt_BR"


def test_config_validator_accepts_lang() -> None:
    from adt.config_validator import validate_key_value

    # Should not raise
    validate_key_value("lang", "en")
    validate_key_value("lang", "pt_BR")


def test_config_validator_rejects_empty_lang() -> None:
    from adt.config_validator import ConfigValidationError, validate_key_value

    with pytest.raises(ConfigValidationError, match="non-empty"):
        validate_key_value("lang", "")

    with pytest.raises(ConfigValidationError, match="non-empty"):
        validate_key_value("lang", "   ")


def test_all_en_keys_present_in_pt_br() -> None:
    """Every key in en.toml must also exist in pt_BR.toml."""
    from adt.cli.i18n import _load_locale

    _load_locale.cache_clear()
    en = _load_locale("en")
    pt = _load_locale("pt_BR")
    missing = set(en.keys()) - set(pt.keys())
    assert not missing, f"Keys missing from pt_BR.toml: {missing}"
