"""Named session store backed by ``~/.adt/sessions/<slug>.json``.

Replaces the global ``session.json`` with per-name files so multiple
terminals (or problems) can each maintain their own supervised state.
On first access the store migrates the legacy ``session.json`` into
``sessions/default.json`` (best-effort, non-destructive).
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from adt.config import ensure_adt_dir
from adt.core.session import SessionContext
from adt.logging.json_log import log_adt

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def _sanitize_slug(name: str) -> str:
    """Return a safe filename slug or raise :class:`ValueError`."""
    slug = name.strip().lower().replace(" ", "-")
    if not slug:
        msg = "Session name must not be empty."
        raise ValueError(msg)
    if ".." in slug or "/" in slug or "\\" in slug:
        msg = f"Session name {name!r} contains path traversal characters."
        raise ValueError(msg)
    if not _SLUG_RE.match(slug):
        msg = (
            f"Session name {name!r} is invalid. "
            "Use alphanumeric characters, hyphens, or underscores (1-64 chars)."
        )
        raise ValueError(msg)
    return slug


class SessionStore:
    """Manage per-name session files under ``~/.adt/sessions/``."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir if base_dir is not None else ensure_adt_dir() / "sessions"
        self._base.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy()

    # ── public API ──────────────────────────────────────────────────────

    def list(self) -> list[str]:
        """Return sorted session names (stem of each ``.json`` file)."""
        return sorted(p.stem for p in self._base.glob("*.json"))

    def load(self, name: str = "default") -> SessionContext:
        """Load a session by name; return empty context if missing."""
        return SessionContext.load(self.path(name))

    def save(self, ctx: SessionContext, name: str = "default") -> None:
        """Persist *ctx* under the given name."""
        ctx.save(self.path(name))

    def delete(self, name: str) -> None:
        """Remove a named session file (no-op if missing)."""
        p = self.path(name)
        if p.exists():
            p.unlink()

    def path(self, name: str) -> Path:
        """Return the file path for a named session."""
        slug = _sanitize_slug(name)
        return self._base / f"{slug}.json"

    # ── migration ───────────────────────────────────────────────────────

    def _migrate_legacy(self) -> None:
        """Move ``~/.adt/session.json`` → ``sessions/default.json`` once."""
        legacy = self._base.parent / "session.json"
        target = self._base / "default.json"
        if not legacy.exists() or target.exists():
            return
        try:
            # Keep a backup of the original file
            backup = legacy.with_suffix(".json.bak")
            shutil.copy2(legacy, backup)
            shutil.move(str(legacy), str(target))
            log_adt(
                logger,
                logging.INFO,
                event="session_migrated",
                source=str(legacy),
                target=str(target),
            )
        except OSError as exc:
            log_adt(
                logger,
                logging.WARNING,
                event="session_migration_failed",
                error=str(exc),
            )
