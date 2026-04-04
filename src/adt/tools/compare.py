"""Compare two local repository roots (structure, key files, dependency hints)."""

from __future__ import annotations

import os
from pathlib import Path

from adt.tools import repo as repo_tools
from adt.tools._paths import SKIP_DIR_NAMES

_KEY_FILES = (
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "package.json",
    "requirements.txt",
    "requirements-dev.txt",
    "Cargo.toml",
    "go.mod",
    "poetry.lock",
    "Pipfile",
)


def _collect_paths(root: Path, *, max_entries: int) -> set[str]:
    """Relative POSIX paths for files under root (bounded walk)."""
    root = root.resolve()
    spec = repo_tools._load_gitignore_spec(root)
    out: set[str] = set()
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIR_NAMES and not d.endswith(".egg-info")
        ]
        current = Path(dirpath)
        try:
            rel_dir = current.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel_dir != "." and repo_tools._is_ignored(
            rel_dir,
            spec=spec,
            is_dir=True,
        ):
            dirnames[:] = []
            continue
        for d in list(dirnames):
            child = current / d
            cr = child.relative_to(root).as_posix()
            if repo_tools._is_ignored(cr, spec=spec, is_dir=True):
                dirnames.remove(d)

        for name in filenames:
            if count >= max_entries:
                return out
            fp = current / name
            rel = fp.relative_to(root).as_posix()
            if repo_tools._is_ignored(rel, spec=spec, is_dir=False):
                continue
            if fp.is_file():
                out.add(rel)
                count += 1
    return out


def compare_repos(
    roots: dict[str, Path],
    repo_a: str,
    repo_b: str,
    *,
    max_tree_entries: int = 400,
) -> str:
    """Return a structured text summary comparing two registered repo keys.

    Args:
        roots: Map of stable repo keys to absolute roots (from the session).
        repo_a: First key in ``roots``.
        repo_b: Second key in ``roots``.
        max_tree_entries: Cap on indexed file paths per side.

    Returns:
        Human-readable diff sections or an error line.
    """
    ra = repo_a.strip()
    rb = repo_b.strip()
    if ra not in roots or rb not in roots:
        known = ", ".join(sorted(roots)) or "(none)"
        return f"error: unknown repo_key (known: {known})"
    if ra == rb:
        return "error: repo_a and repo_b must differ"

    pa = roots[ra].resolve()
    pb = roots[rb].resolve()
    if not pa.is_dir() or not pb.is_dir():
        return "error: one or both roots are not directories"

    set_a = _collect_paths(pa, max_entries=max_tree_entries)
    set_b = _collect_paths(pb, max_entries=max_tree_entries)

    only_a = sorted(set_a - set_b)
    only_b = sorted(set_b - set_a)
    common = sorted(set_a & set_b)

    lines: list[str] = [
        f"compare_repos: {ra} ({pa}) vs {rb} ({pb})",
        f"indexed_files: {len(set_a)} vs {len(set_b)} (cap={max_tree_entries})",
        "",
        "[structure]",
        f"only_in_{ra}: {len(only_a)}",
        f"only_in_{rb}: {len(only_b)}",
        f"in_both: {len(common)}",
    ]
    if only_a[:30]:
        lines.append(f"sample_only_{ra}: {', '.join(only_a[:30])}")
    if only_b[:30]:
        lines.append(f"sample_only_{rb}: {', '.join(only_b[:30])}")

    lines.extend(["", "[key_files]"])
    for name in _KEY_FILES:
        fa = pa / name
        fb = pb / name
        sa = fa.is_file()
        sb = fb.is_file()
        if not sa and not sb:
            continue
        if sa != sb:
            lines.append(f"{name}: only in {ra}" if sa else f"{name}: only in {rb}")
            continue
        try:
            ta = fa.read_text(encoding="utf-8", errors="replace")
            tb = fb.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            lines.append(f"{name}: read_error {exc}")
            continue
        if ta == tb:
            lines.append(f"{name}: identical ({len(ta)} chars)")
        else:
            lines.append(
                f"{name}: differ (chars {len(ta)} vs {len(tb)}); "
                "see read_file on each side for details",
            )

    lines.extend(["", "[dependency_hints]"])
    for label, base in (ra, pa), (rb, pb):
        req = base / "requirements.txt"
        if req.is_file():
            try:
                n = len(
                    [
                        ln
                        for ln in req.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        ).splitlines()
                        if ln.strip() and not ln.lstrip().startswith("#")
                    ],
                )
                lines.append(f"{label} requirements.txt: ~{n} non-comment lines")
            except OSError:
                lines.append(f"{label} requirements.txt: (unreadable)")
        pp = base / "pyproject.toml"
        if pp.is_file():
            try:
                text = pp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                lines.append(f"{label} pyproject.toml: (unreadable)")
            else:
                has_proj = "[project]" in text
                has_poetry = "[tool.poetry]" in text
                lines.append(
                    f"{label} pyproject.toml: "
                    f"[project]={has_proj} [tool.poetry]={has_poetry}",
                )

    return "\n".join(lines)
