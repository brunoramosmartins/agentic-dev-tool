"""File-backed cache for repository tree listings."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def _git_head_hex(root: Path) -> str:
    """Return ``git rev-parse HEAD`` output or a stable non-git fallback."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        ns = root.stat().st_mtime_ns
    except OSError:
        ns = 0
    return f"nogit-{ns}"


def _cache_key(root: Path, max_depth: int) -> str:
    """Build a filesystem-safe cache key from repo path, revision, and depth."""
    raw = f"{root.resolve()}|{_git_head_hex(root)}|{max_depth}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:56]
    return digest


class RepoTreeCache:
    """JSON files under ``cache_dir`` storing tree line lists with TTL."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        ttl_seconds: float = 300.0,
    ) -> None:
        """Create a cache using ``cache_dir`` (created on demand).

        Args:
            cache_dir: Base directory (e.g. ``~/.adt/cache``).
            ttl_seconds: Time-to-live for entries (default five minutes).
        """
        self._dir = cache_dir
        self._ttl = max(1.0, float(ttl_seconds))

    def get_or_build(
        self,
        root: Path,
        max_depth: int,
        build: Callable[[], list[str]],
    ) -> list[str]:
        """Return cached tree lines or call ``build`` and persist when fresh."""
        self._dir.mkdir(parents=True, exist_ok=True)
        key = _cache_key(root, max_depth)
        path = self._dir / f"tree_{key}.json"
        now = time.time()
        if path.is_file():
            try:
                raw = path.read_text(encoding="utf-8")
                data = json.loads(raw)
                ts = float(data.get("saved_at", 0))
                lines = data.get("lines")
                if now - ts <= self._ttl and isinstance(lines, list):
                    logger.debug("repo_tree_cache_hit path=%s", path.name)
                    return [str(x) for x in lines]
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
        lines = build()
        try:
            path.write_text(
                json.dumps({"saved_at": now, "lines": lines}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("repo_tree_cache_write_failed: %s", exc)
        return lines
