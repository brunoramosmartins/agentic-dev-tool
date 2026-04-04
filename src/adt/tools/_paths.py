"""Shared path-safety utilities and constants for tool implementations."""

from __future__ import annotations

from pathlib import Path

SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".eggs",
    },
)


def safe_resolve_under(root: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``root``; reject path-traversal attempts.

    Args:
        root: Directory that acts as the sandbox boundary.
        relative: User- or model-supplied relative path (POSIX-style ok).

    Returns:
        An absolute, resolved path guaranteed to be inside ``root``.

    Raises:
        ValueError: If the resolved path would escape ``root``.
    """
    base = root.resolve()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        msg = "path escapes root directory"
        raise ValueError(msg) from exc
    return candidate
