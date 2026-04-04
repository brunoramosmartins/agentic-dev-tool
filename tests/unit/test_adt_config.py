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


# ── from_toml_table edge cases ──────────────────────────────────────


def test_from_toml_table_invalid_cache_ttl() -> None:
    cfg = AdtConfig.from_toml_table({"cache_ttl_seconds": "not-a-number"})
    assert cfg.cache_ttl_seconds == 300.0


def test_from_toml_table_invalid_max_tool_iterations() -> None:
    cfg = AdtConfig.from_toml_table({"max_tool_iterations": "abc"})
    assert cfg.max_tool_iterations == 5


def test_from_toml_table_token_budget_empty_string() -> None:
    cfg = AdtConfig.from_toml_table({"token_budget": ""})
    assert cfg.token_budget is None


def test_from_toml_table_token_budget_none() -> None:
    cfg = AdtConfig.from_toml_table({"token_budget": None})
    assert cfg.token_budget is None


def test_from_toml_table_token_budget_invalid() -> None:
    cfg = AdtConfig.from_toml_table({"token_budget": "xyz"})
    assert cfg.token_budget is None


def test_from_toml_table_token_budget_valid() -> None:
    cfg = AdtConfig.from_toml_table({"token_budget": 4096})
    assert cfg.token_budget == 4096


def test_from_toml_table_use_llm_routing_string_true() -> None:
    cfg = AdtConfig.from_toml_table({"use_llm_routing": "yes"})
    assert cfg.use_llm_routing is True


def test_from_toml_table_use_llm_routing_string_false() -> None:
    cfg = AdtConfig.from_toml_table({"use_llm_routing": "false"})
    assert cfg.use_llm_routing is False


def test_from_toml_table_use_llm_routing_bool() -> None:
    cfg = AdtConfig.from_toml_table({"use_llm_routing": False})
    assert cfg.use_llm_routing is False


def test_from_toml_table_agent_chain_none() -> None:
    cfg = AdtConfig.from_toml_table({"agent_chain": None})
    assert cfg.agent_chain == []


def test_from_toml_table_agent_chain_single_string() -> None:
    cfg = AdtConfig.from_toml_table({"agent_chain": "repo_agent"})
    assert cfg.agent_chain == ["repo_agent"]


def test_from_toml_table_agent_chain_list() -> None:
    cfg = AdtConfig.from_toml_table({"agent_chain": ["repo_agent", "research_agent"]})
    assert cfg.agent_chain == ["repo_agent", "research_agent"]


def test_from_toml_table_custom_tools_none() -> None:
    cfg = AdtConfig.from_toml_table({"custom_tools": None})
    assert cfg.custom_tools == []


def test_from_toml_table_custom_tools_single() -> None:
    cfg = AdtConfig.from_toml_table({"custom_tools": "my_tool"})
    assert cfg.custom_tools == ["my_tool"]


# ── apply_env_overrides edge cases ──────────────────────────────────


def test_env_override_cache_ttl(monkeypatch) -> None:
    monkeypatch.setenv("ADT_CACHE_TTL", "600")
    cfg = apply_env_overrides(AdtConfig())
    assert cfg.cache_ttl_seconds == 600.0


def test_env_override_use_llm_routing_off(monkeypatch) -> None:
    monkeypatch.setenv("ADT_USE_LLM_ROUTING", "false")
    cfg = apply_env_overrides(AdtConfig())
    assert cfg.use_llm_routing is False


def test_env_override_use_llm_routing_on(monkeypatch) -> None:
    monkeypatch.setenv("ADT_USE_LLM_ROUTING", "true")
    cfg = apply_env_overrides(AdtConfig(use_llm_routing=False))
    assert cfg.use_llm_routing is True


def test_env_override_max_tool_iterations(monkeypatch) -> None:
    monkeypatch.setenv("ADT_MAX_TOOL_ITERATIONS", "10")
    cfg = apply_env_overrides(AdtConfig())
    assert cfg.max_tool_iterations == 10


def test_env_override_token_budget(monkeypatch) -> None:
    monkeypatch.setenv("ADT_TOKEN_BUDGET", "8000")
    cfg = apply_env_overrides(AdtConfig())
    assert cfg.token_budget == 8000


# ── update_config_key edge cases ────────────────────────────────────


def test_update_config_key_cache_ttl(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "cache_ttl_seconds", "120.5")
    assert cfg.cache_ttl_seconds == 120.5


def test_update_config_key_use_llm_routing(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "use_llm_routing", "false")
    assert cfg.use_llm_routing is False


def test_update_config_key_routing_model(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "routing_model", "gpt-4o")
    assert cfg.routing_model == "gpt-4o"


def test_update_config_key_max_tool_iterations(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "max_tool_iterations", "8")
    assert cfg.max_tool_iterations == 8


def test_update_config_key_token_budget(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "token_budget", "4096")
    assert cfg.token_budget == 4096


def test_update_config_key_token_budget_none(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "token_budget", "none")
    assert cfg.token_budget is None


def test_update_config_key_agent_chain(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "agent_chain", "repo_agent, research_agent")
    assert cfg.agent_chain == ["repo_agent", "research_agent"]


def test_update_config_key_custom_tools(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = update_config_key(p, "custom_tools", "tool_a, tool_b")
    assert cfg.custom_tools == ["tool_a", "tool_b"]


def test_update_config_key_unknown_raises(tmp_path, monkeypatch) -> None:
    import pytest

    from adt import config as m

    p = tmp_path / "c.toml"
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    with pytest.raises(ValueError, match="Unknown config key"):
        update_config_key(p, "no_such_key", "val")


def test_load_non_dict_section_returns_defaults(tmp_path, monkeypatch) -> None:
    from adt import config as m

    p = tmp_path / "c.toml"
    p.write_text('adt = "not a table"\n', encoding="utf-8")
    monkeypatch.setattr(m, "adt_config_path", lambda: p)
    cfg = load_config_file()
    assert cfg.default_model == "gpt-4o-mini"
