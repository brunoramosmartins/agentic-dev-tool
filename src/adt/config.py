"""Load and persist user settings in ``~/.adt/config.toml``."""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any

import tomli
import tomli_w

_ADT_SECTION = "adt"


def adt_config_path() -> Path:
    """Return the path to ``~/.adt/config.toml``."""
    return Path.home() / ".adt" / "config.toml"


def ensure_adt_dir() -> Path:
    """Create ``~/.adt`` if needed and return its path."""
    d = Path.home() / ".adt"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class AdtConfig:
    """Persistent CLI defaults (overridable by environment and flags)."""

    default_model: str = "gpt-4o-mini"
    log_level: str = "INFO"
    cache_ttl_seconds: float = 300.0
    use_llm_routing: bool = True
    routing_model: str = "gpt-4o-mini"
    max_tool_iterations: int = 5
    token_budget: int | None = None
    review_max_bytes: int = 200_000
    agent_chain: list[str] = field(default_factory=list)
    custom_tools: list[str] = field(default_factory=list)
    lang: str = "en"

    def to_toml_table(self) -> dict[str, Any]:
        """Serialize the ``adt`` table for writing."""
        d: dict[str, Any] = {
            "default_model": self.default_model,
            "log_level": self.log_level,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "use_llm_routing": self.use_llm_routing,
            "routing_model": self.routing_model,
            "max_tool_iterations": self.max_tool_iterations,
            "review_max_bytes": self.review_max_bytes,
            "agent_chain": self.agent_chain,
            "custom_tools": self.custom_tools,
            "lang": self.lang,
        }
        if self.token_budget is not None:
            d["token_budget"] = self.token_budget
        return d

    @classmethod
    def from_toml_table(cls, data: dict[str, Any]) -> AdtConfig:
        """Build from a decoded ``[adt]`` mapping."""
        kwargs: dict[str, Any] = {}
        known = {f.name for f in fields(cls)}
        for key, default in [
            ("default_model", "gpt-4o-mini"),
            ("log_level", "INFO"),
            ("cache_ttl_seconds", 300.0),
            ("use_llm_routing", True),
            ("routing_model", "gpt-4o-mini"),
            ("max_tool_iterations", 5),
            ("token_budget", None),
            ("review_max_bytes", 200_000),
            ("agent_chain", []),
            ("custom_tools", []),
            ("lang", "en"),
        ]:
            if key not in known:
                continue
            raw = data.get(key, default)
            if key == "cache_ttl_seconds":
                try:
                    kwargs[key] = float(raw)
                except (TypeError, ValueError):
                    kwargs[key] = 300.0
            elif key == "max_tool_iterations":
                try:
                    kwargs[key] = int(raw)
                except (TypeError, ValueError):
                    kwargs[key] = 5
            elif key == "review_max_bytes":
                try:
                    kwargs[key] = int(raw)
                except (TypeError, ValueError):
                    kwargs[key] = 200_000
            elif key == "token_budget":
                if raw is None or raw == "":
                    kwargs[key] = None
                else:
                    try:
                        kwargs[key] = int(raw)
                    except (TypeError, ValueError):
                        kwargs[key] = None
            elif key in ("use_llm_routing",):
                if isinstance(raw, str):
                    kwargs[key] = raw.strip().lower() in ("1", "true", "yes", "on")
                else:
                    kwargs[key] = bool(raw)
            elif key in ("agent_chain", "custom_tools"):
                if raw is None:
                    kwargs[key] = []
                elif isinstance(raw, list):
                    kwargs[key] = [str(x) for x in raw]
                else:
                    kwargs[key] = [str(raw)]
            else:
                kwargs[key] = str(raw) if raw is not None else default
        return cls(**kwargs)


def load_config_file(path: Path | None = None) -> AdtConfig:
    """Read ``config.toml``; return defaults if missing or invalid."""
    cfg_path = path or adt_config_path()
    if not cfg_path.is_file():
        return AdtConfig()
    try:
        raw = cfg_path.read_bytes()
        doc = tomli.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomli.TOMLDecodeError):
        return AdtConfig()
    section = doc.get(_ADT_SECTION, {})
    if not isinstance(section, dict):
        return AdtConfig()
    return AdtConfig.from_toml_table(section)


def apply_env_overrides(cfg: AdtConfig) -> AdtConfig:
    """Return a copy with ``ADT_*`` environment variables applied."""
    c = AdtConfig(
        default_model=os.environ.get("ADT_DEFAULT_MODEL", cfg.default_model),
        log_level=os.environ.get("ADT_LOG_LEVEL", cfg.log_level),
        cache_ttl_seconds=cfg.cache_ttl_seconds,
        use_llm_routing=cfg.use_llm_routing,
        routing_model=os.environ.get("ADT_ROUTING_MODEL", cfg.routing_model),
        max_tool_iterations=cfg.max_tool_iterations,
        token_budget=cfg.token_budget,
        agent_chain=list(cfg.agent_chain),
        custom_tools=list(cfg.custom_tools),
        lang=os.environ.get("ADT_LANG", cfg.lang),
    )
    if os.environ.get("ADT_CACHE_TTL", "").strip():
        with contextlib.suppress(ValueError):
            c.cache_ttl_seconds = max(1.0, float(os.environ["ADT_CACHE_TTL"]))
    ur = os.environ.get("ADT_USE_LLM_ROUTING", "").strip().lower()
    if ur in ("0", "false", "no", "off"):
        c.use_llm_routing = False
    elif ur in ("1", "true", "yes", "on"):
        c.use_llm_routing = True
    mi = os.environ.get("ADT_MAX_TOOL_ITERATIONS", "").strip()
    if mi.isdigit():
        c.max_tool_iterations = max(1, int(mi))
    tb = os.environ.get("ADT_TOKEN_BUDGET", "").strip()
    if tb.isdigit():
        c.token_budget = int(tb)
    rmb = os.environ.get("ADT_REVIEW_MAX_BYTES", "").strip()
    if rmb.isdigit():
        c.review_max_bytes = max(1024, int(rmb))
    return c


def save_config(cfg: AdtConfig, path: Path | None = None) -> None:
    """Write the full document with an ``[adt]`` table."""
    cfg_path = path or adt_config_path()
    ensure_adt_dir()
    doc = {_ADT_SECTION: cfg.to_toml_table()}
    cfg_path.write_text(tomli_w.dumps(doc), encoding="utf-8")


def update_config_key(path: Path | None, key: str, value: str) -> AdtConfig:
    """Load config, set one ``adt`` key (string form), save, return merged config."""
    cfg_path = path or adt_config_path()
    cfg = load_config_file(cfg_path)
    key_norm = key.strip().lower().replace("-", "_")
    if key_norm == "default_model":
        cfg = replace(cfg, default_model=value)
    elif key_norm == "log_level":
        cfg = replace(cfg, log_level=value.upper())
    elif key_norm == "cache_ttl_seconds":
        cfg = replace(cfg, cache_ttl_seconds=float(value))
    elif key_norm == "use_llm_routing":
        cfg = replace(
            cfg,
            use_llm_routing=value.lower() in ("1", "true", "yes"),
        )
    elif key_norm == "routing_model":
        cfg = replace(cfg, routing_model=value)
    elif key_norm == "max_tool_iterations":
        cfg = replace(cfg, max_tool_iterations=max(1, int(value)))
    elif key_norm == "token_budget":
        cfg = replace(
            cfg,
            token_budget=None if value.lower() in ("none", "") else int(value),
        )
    elif key_norm == "agent_chain":
        parts = [p.strip() for p in value.split(",") if p.strip()]
        cfg = replace(cfg, agent_chain=parts)
    elif key_norm == "review_max_bytes":
        cfg = replace(cfg, review_max_bytes=max(1024, int(value)))
    elif key_norm == "custom_tools":
        parts = [p.strip() for p in value.split(",") if p.strip()]
        cfg = replace(cfg, custom_tools=parts)
    elif key_norm == "lang":
        cfg = replace(cfg, lang=value.strip())
    else:
        msg = f"Unknown config key: {key!r}"
        raise ValueError(msg)
    save_config(cfg, cfg_path)
    return cfg
