"""Repository tools: directory tree, file reads, and regex search."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pathspec

from adt.tools._paths import SKIP_DIR_NAMES as _ALWAYS_SKIP_DIR_NAMES
from adt.tools._paths import safe_resolve_under as _safe_resolve_under


def _load_gitignore_spec(repo_root: Path) -> pathspec.PathSpec | None:
    """Load and compile ``.gitignore`` patterns from the repository root, if present.

    Args:
        repo_root: Absolute or resolved repository root directory.

    Returns:
        A :class:`pathspec.PathSpec` in ``gitwildmatch`` mode, or ``None`` when
        no ``.gitignore`` file exists.
    """
    gitignore = repo_root / ".gitignore"
    if not gitignore.is_file():
        return None
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    if not lines:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def _posix_relative_to(repo_root: Path, path: Path) -> str:
    """Return ``path`` relative to ``repo_root`` using forward slashes.

    Args:
        repo_root: Resolved repository root.
        path: A path under ``repo_root``.

    Returns:
        A POSIX-style relative path string.
    """
    return path.relative_to(repo_root).as_posix()


def _is_ignored(
    rel_posix: str,
    *,
    spec: pathspec.PathSpec | None,
    is_dir: bool,
) -> bool:
    """Return whether a path should be skipped according to gitignore rules.

    Args:
        rel_posix: Path relative to repo root, POSIX separators.
        spec: Compiled gitignore spec, or ``None`` to skip pattern checks.
        is_dir: Whether this entry is a directory (affects trailing-slash rules).

    Returns:
        ``True`` if the entry matches an ignore pattern.
    """
    if spec is None:
        return False
    paths_to_try = [rel_posix]
    if is_dir and not rel_posix.endswith("/"):
        paths_to_try.append(f"{rel_posix}/")
    return any(spec.match_file(p) for p in paths_to_try)


def read_repo_tree(
    repo_root: Path,
    path: str = ".",
    max_depth: int = 3,
) -> str:
    """Build a printable directory tree under ``repo_root``.

    Respects ``.gitignore`` when present. Always skips common bulky directories
    (``.git``, ``node_modules``, virtualenvs, caches).

    Args:
        repo_root: Root of the repository on disk.
        path: Subdirectory relative to ``repo_root`` to start the tree (default ``.``).
        max_depth: Maximum directory depth below the start path (0 = start only).

    Returns:
        Indented tree as a single string. On missing directory, returns an error line.
    """
    try:
        start = _safe_resolve_under(repo_root, path)
    except ValueError as exc:
        return f"error: {exc}"

    if not start.exists():
        return f"error: path does not exist: {path}"
    if not start.is_dir():
        return f"error: not a directory: {path}"

    spec = _load_gitignore_spec(repo_root.resolve())
    lines: list[str] = []

    def walk(current: Path, depth: int, prefix: str) -> None:
        """Recursively append tree lines for ``current``."""
        if depth > max_depth:
            return
        rel = _posix_relative_to(repo_root.resolve(), current)
        if rel != "." and _is_ignored(rel, spec=spec, is_dir=current.is_dir()):
            return
        name = "." if rel == "." else current.name
        lines.append(f"{prefix}{name}/" if current.is_dir() else f"{prefix}{name}")
        if not current.is_dir():
            return
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return
        for child in children:
            if child.name in _ALWAYS_SKIP_DIR_NAMES:
                continue
            child_rel = _posix_relative_to(repo_root.resolve(), child)
            if _is_ignored(child_rel, spec=spec, is_dir=child.is_dir()):
                continue
            walk(child, depth + 1, prefix + "  ")

    walk(start, 0, "")
    header = f"tree: {path} (max_depth={max_depth})\n"
    return header + ("\n".join(lines) if lines else "(empty)")


def read_file(
    repo_root: Path,
    path: str,
    max_lines: int = 200,
) -> str:
    """Read a text file under the repository with line numbers and a line cap.

    Args:
        repo_root: Repository root used to resolve ``path`` safely.
        path: File path relative to ``repo_root``.
        max_lines: Maximum number of lines to return (from the start of the file).

    Returns:
        Numbered file contents, or an error message string.
    """
    try:
        target = _safe_resolve_under(repo_root, path)
    except ValueError as exc:
        return f"error: {exc}"

    if not target.is_file():
        return f"error: not a file: {path}"

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"error: cannot read file: {exc}"

    out_lines = text.splitlines()
    trimmed = out_lines[:max_lines]
    numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(trimmed)]
    body = "\n".join(numbered)
    if len(out_lines) > max_lines:
        body += f"\n... ({len(out_lines) - max_lines} more lines omitted)"
    return f"file: {path}\n{body}"


def _is_probably_binary(chunk: bytes) -> bool:
    """Return ``True`` if ``chunk`` looks like binary data.

    Args:
        chunk: First bytes of a file.

    Returns:
        ``True`` when null bytes are present (heuristic for binary files).
    """
    return b"\0" in chunk


def search_code(
    repo_root: Path,
    path: str,
    pattern: str,
    max_results: int = 20,
) -> str:
    """Search for a regex ``pattern`` in text files under ``path``.

    Skips gitignored paths and binary files. Collects up to ``max_results`` hits.

    Args:
        repo_root: Repository root for safe resolution and ignore rules.
        path: Directory relative to ``repo_root`` to search within.
        pattern: Regular expression (Python ``re`` syntax).
        max_results: Maximum match lines to return across all files.

    Returns:
        Formatted search results or an error description.
    """
    try:
        start = _safe_resolve_under(repo_root, path)
    except ValueError as exc:
        return f"error: {exc}"

    if not start.is_dir():
        return f"error: not a directory: {path}"

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"error: invalid regex: {exc}"

    root_resolved = repo_root.resolve()
    spec = _load_gitignore_spec(root_resolved)
    results: list[str] = []
    count = 0

    for dirpath, dirnames, filenames in os.walk(start, topdown=True):
        current = Path(dirpath)
        dirnames[:] = [
            d
            for d in dirnames
            if d not in _ALWAYS_SKIP_DIR_NAMES and not d.endswith(".egg-info")
        ]
        rel_dir = _posix_relative_to(root_resolved, current)
        if rel_dir != "." and _is_ignored(rel_dir, spec=spec, is_dir=True):
            dirnames[:] = []
            continue
        for d in list(dirnames):
            child = current / d
            cr = _posix_relative_to(root_resolved, child)
            if _is_ignored(cr, spec=spec, is_dir=True):
                dirnames.remove(d)

        for name in filenames:
            if count >= max_results:
                break
            fp = current / name
            rel_file = _posix_relative_to(root_resolved, fp)
            if _is_ignored(rel_file, spec=spec, is_dir=False):
                continue
            if not fp.is_file():
                continue
            try:
                raw = fp.read_bytes()[:8192]
            except OSError:
                continue
            if _is_probably_binary(raw):
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if count >= max_results:
                    break
                if regex.search(line):
                    results.append(f"{rel_file}:{lineno}:{line.rstrip()}")
                    count += 1
        if count >= max_results:
            break

    if not results:
        return f"search: no matches for pattern {pattern!r} under {path}"
    header = f"search: pattern={pattern!r} path={path} (max_results={max_results})\n"
    return header + "\n".join(results)
