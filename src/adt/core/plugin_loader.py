"""Discover and load community skills and tools from ``~/.adt/plugins/``.

Directory layout::

    ~/.adt/plugins/
        skills/
            my_skill/
                SKILL.md          # required — loaded as SkillContext
        tools/
            my_tool/
                tool.py           # required — must define ``register(registry)``
                manifest.json     # optional — name, description, allowed_agents

Safety: plugin tools are registered through the same
:class:`~adt.mcp.registry.ToolRegistry` and validated by the same
:class:`~adt.mcp.executor.ExecutionController` as built-ins.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any

from adt.config import ensure_adt_dir
from adt.logging.json_log import log_adt

logger = logging.getLogger(__name__)


def _plugins_dir() -> Path:
    return ensure_adt_dir() / "plugins"


# ── skill discovery ────────────────────────────────────────────────────


def discover_skills(
    base: Path | None = None,
) -> list[dict[str, Any]]:
    """Return metadata dicts for each skill found under ``plugins/skills/``.

    Each dict has keys ``name`` (directory name), ``path`` (Path to SKILL.md),
    and ``markdown`` (file contents).
    """
    root = (base or _plugins_dir()) / "skills"
    if not root.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            log_adt(
                logger,
                logging.WARNING,
                event="plugin_skill_missing_md",
                skill=entry.name,
            )
            continue
        try:
            markdown = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            log_adt(
                logger,
                logging.WARNING,
                event="plugin_skill_read_failed",
                skill=entry.name,
                error=str(exc),
            )
            continue
        results.append(
            {
                "name": entry.name,
                "path": skill_md,
                "markdown": markdown,
            }
        )
    return results


def load_plugin_skills(
    base: Path | None = None,
) -> list[Any]:
    """Load plugin skills as :class:`~adt.skills.context.SkillContext` objects."""
    from adt.skills.context import SkillContext, parse_version

    raw = discover_skills(base)
    contexts = []
    for item in raw:
        ctx = SkillContext(
            name=item["name"],
            markdown=item["markdown"],
            version=parse_version(item["markdown"]),
        )
        contexts.append(ctx)
    return contexts


# ── tool discovery ─────────────────────────────────────────────────────


def discover_tools(
    base: Path | None = None,
) -> list[dict[str, Any]]:
    """Return metadata dicts for each tool found under ``plugins/tools/``.

    Each dict has keys ``name``, ``path`` (to tool.py), and optionally
    ``manifest`` (parsed manifest.json contents).
    """
    root = (base or _plugins_dir()) / "tools"
    if not root.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        tool_py = entry / "tool.py"
        if not tool_py.is_file():
            log_adt(
                logger,
                logging.WARNING,
                event="plugin_tool_missing_py",
                tool=entry.name,
            )
            continue
        manifest: dict[str, Any] | None = None
        manifest_path = entry / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log_adt(
                    logger,
                    logging.WARNING,
                    event="plugin_tool_manifest_invalid",
                    tool=entry.name,
                    error=str(exc),
                )
        results.append(
            {
                "name": entry.name,
                "path": tool_py,
                "manifest": manifest,
            }
        )
    return results


def load_plugin_tool(tool_meta: dict[str, Any]) -> Any | None:
    """Import a plugin's ``tool.py`` and return the loaded module.

    The module must define a ``register(registry)`` function that adds
    :class:`~adt.mcp.registry.ToolDefinition` instances to the registry.

    Returns ``None`` on import failure.
    """
    tool_path: Path = tool_meta["path"]
    name: str = tool_meta["name"]
    spec = importlib.util.spec_from_file_location(f"adt_plugin_{name}", tool_path)
    if spec is None or spec.loader is None:
        log_adt(
            logger,
            logging.WARNING,
            event="plugin_tool_import_failed",
            tool=name,
            error="spec is None",
        )
        return None
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        log_adt(
            logger,
            logging.WARNING,
            event="plugin_tool_import_failed",
            tool=name,
            error=str(exc),
        )
        return None
    if not hasattr(module, "register"):
        log_adt(
            logger,
            logging.WARNING,
            event="plugin_tool_no_register",
            tool=name,
        )
        return None
    return module


def register_plugin_tools(
    registry: Any,
    base: Path | None = None,
) -> list[str]:
    """Discover and register all plugin tools into *registry*.

    Returns the list of successfully registered tool names.
    """
    loaded: list[str] = []
    for meta in discover_tools(base):
        module = load_plugin_tool(meta)
        if module is None:
            continue
        try:
            module.register(registry)
            loaded.append(meta["name"])
            log_adt(
                logger,
                logging.INFO,
                event="plugin_tool_registered",
                tool=meta["name"],
            )
        except Exception as exc:  # noqa: BLE001
            log_adt(
                logger,
                logging.WARNING,
                event="plugin_tool_register_failed",
                tool=meta["name"],
                error=str(exc),
            )
    return loaded


# ── validation ─────────────────────────────────────────────────────────


def validate_plugin(path: Path) -> list[str]:
    """Return a list of validation errors for a plugin directory.

    An empty list means the plugin is valid.
    """
    errors: list[str] = []
    if not path.is_dir():
        errors.append(f"Not a directory: {path}")
        return errors
    has_skill = (path / "SKILL.md").is_file()
    has_tool = (path / "tool.py").is_file()
    if not has_skill and not has_tool:
        errors.append("Plugin must contain SKILL.md or tool.py (or both).")
    if has_tool:
        module = load_plugin_tool({"name": path.name, "path": path / "tool.py"})
        if module is None:
            errors.append("tool.py failed to import.")
        elif not hasattr(module, "register"):
            errors.append("tool.py must define a register(registry) function.")
    return errors
