"""Strict validator for ``adt config set`` key-value pairs.

Validates key names against the known :class:`~adt.config.AdtConfig` fields
and checks value formats before persisting, producing actionable error
messages on rejection.
"""

from __future__ import annotations

from dataclasses import fields as dc_fields

from adt.config import AdtConfig

_KNOWN_KEYS: set[str] = {f.name for f in dc_fields(AdtConfig)}

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

_VALID_AGENTS = {"repo_agent", "research_agent", "project_agent"}


class ConfigValidationError(ValueError):
    """Raised when a config key or value is invalid."""


def validate_key_value(key: str, raw: str) -> None:
    """Validate a ``key=value`` pair for ``adt config set``.

    Raises:
        ConfigValidationError: When the key is unknown or the value is
            malformed for the expected type.
    """
    k = key.strip().lower().replace("-", "_")

    if k not in _KNOWN_KEYS:
        known = ", ".join(sorted(_KNOWN_KEYS))
        raise ConfigValidationError(f"Unknown config key: {key!r}. Valid keys: {known}")

    if k == "log_level":
        if raw.upper() not in _VALID_LOG_LEVELS:
            raise ConfigValidationError(
                f"Invalid log level {raw!r}. "
                f"Choose one of: {', '.join(sorted(_VALID_LOG_LEVELS))}."
            )

    elif k == "cache_ttl_seconds":
        try:
            val = float(raw)
        except ValueError:
            raise ConfigValidationError(
                f"cache_ttl_seconds must be a number, got {raw!r}."
            ) from None
        if val < 0:
            raise ConfigValidationError(
                f"cache_ttl_seconds must be non-negative, got {val}."
            )

    elif k == "use_llm_routing":
        if raw.lower() not in ("0", "1", "true", "false", "yes", "no"):
            raise ConfigValidationError(
                f"use_llm_routing must be a boolean-like value, got {raw!r}. "
                "Use: true/false, yes/no, or 1/0."
            )

    elif k == "max_tool_iterations":
        if not raw.strip().isdigit():
            raise ConfigValidationError(
                f"max_tool_iterations must be a positive integer, got {raw!r}."
            )
        if int(raw) < 1:
            raise ConfigValidationError("max_tool_iterations must be at least 1.")

    elif k == "token_budget":
        if raw.lower() not in ("none", ""):
            try:
                val_int = int(raw)
            except ValueError:
                raise ConfigValidationError(
                    f"token_budget must be an integer or 'none', got {raw!r}."
                ) from None
            if val_int < 0:
                raise ConfigValidationError(
                    f"token_budget must be non-negative, got {val_int}."
                )

    elif k == "review_max_bytes":
        if not raw.strip().isdigit():
            raise ConfigValidationError(
                f"review_max_bytes must be a positive integer, got {raw!r}."
            )
        if int(raw) < 1024:
            raise ConfigValidationError(
                f"review_max_bytes must be at least 1024, got {raw}."
            )

    elif k == "lang":
        if not raw.strip():
            raise ConfigValidationError(
                "lang must be a non-empty locale code (e.g. 'en', 'pt_BR')."
            )

    elif k == "agent_chain":
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for part in parts:
            if part not in _VALID_AGENTS:
                raise ConfigValidationError(
                    f"Invalid agent in agent_chain: {part!r}. "
                    f"Valid agents: {', '.join(sorted(_VALID_AGENTS))}."
                )
