"""Minimal gettext-style i18n backed by TOML locale files.

Locale files live under ``src/adt/locales/<lang>.toml`` and are shipped
inside the wheel. The active locale is resolved from:

1. ``ADT_LANG`` environment variable
2. ``lang`` key in ``~/.adt/config.toml``
3. Fallback to ``"en"``
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import tomli

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"


def _resolve_lang() -> str:
    """Determine the active language code."""
    env = os.environ.get("ADT_LANG", "").strip()
    if env:
        return env

    try:
        from adt.config import load_config_file

        cfg = load_config_file()
        cfg_lang = getattr(cfg, "lang", None)
        if cfg_lang:
            return str(cfg_lang)
    except Exception:  # noqa: BLE001
        pass

    return "en"


@lru_cache(maxsize=4)
def _load_locale(lang: str) -> dict[str, str]:
    """Load a single TOML locale file into a flat ``{key: translation}`` dict."""
    path = _LOCALES_DIR / f"{lang}.toml"
    if not path.is_file():
        if lang != "en":
            logger.debug("locale file not found: %s, falling back to en", path)
        return _load_locale("en") if lang != "en" else {}
    try:
        raw: dict[str, Any] = tomli.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomli.TOMLDecodeError) as exc:
        logger.warning("failed to load locale %s: %s", lang, exc)
        return _load_locale("en") if lang != "en" else {}

    flat: dict[str, str] = {}
    for section, entries in raw.items():
        if isinstance(entries, dict):
            for key, value in entries.items():
                flat[f"{section}.{key}"] = str(value)
        else:
            flat[section] = str(entries)
    return flat


def t(key: str, **kwargs: Any) -> str:
    """Translate *key* using the active locale, with ``str.format`` substitution.

    Falls back to the English translation, then to *key* itself.
    """
    lang = _resolve_lang()
    table = _load_locale(lang)
    template = table.get(key)
    if template is None:
        if lang != "en":
            en = _load_locale("en")
            template = en.get(key)
        if template is None:
            return key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def reload_locale() -> None:
    """Clear the locale cache (useful after config change or in tests)."""
    _load_locale.cache_clear()
