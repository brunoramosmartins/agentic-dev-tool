"""~/.adt/config.toml load/save."""

from __future__ import annotations

from pathlib import Path

from adt.config import (
    AdtConfig,
    apply_env_overrides,
    ensure_adt_dir,
    load_config_file,
    save_config,
    update_config_key,
)


def test_ensure_adt_dir(monkeypatch, tmp_path) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    d = ensure_adt_dir()
    assert d == fake_home / ".adt"
    assert d.is_dir()


def test_load_missing_returns_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    from adt import config as m

    monkeypatch.setattr(m, "adt_config_path", lambda: tmp_path / "nope.toml")
    cfg = load_config_file()
    assert cfg.default_model == "gpt-4o-mini"
    assert cfg.use_llm_routing is True


def test_save_and_roundtrip(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    save_config(AdtConfig(default_model="gpt-4o", agent_chain=["repo_agent"]))
    cfg = load_config_file(p)
    assert cfg.default_model == "gpt-4o"
    assert cfg.agent_chain == ["repo_agent"]


def test_update_config_key(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    update_config_key(p, "log_level", "debug")
    cfg = load_config_file(p)
    assert cfg.log_level == "DEBUG"


def test_load_corrupt_toml_returns_defaults(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "bad.toml"
    p.write_text("[[[not toml", encoding="utf-8")
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = load_config_file()
    assert cfg.default_model == "gpt-4o-mini"


def test_env_override_model(monkeypatch) -> None:
    monkeypatch.setenv("ADT_DEFAULT_MODEL", "custom-model")
    cfg = apply_env_overrides(AdtConfig())
    assert cfg.default_model == "custom-model"
