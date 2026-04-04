"""Parse ``--repo`` values as a local directory or ``owner/repo`` GitHub slug."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_GITHUB_SLUG = re.compile(r"^[\w.-]+/[\w.-]+$")


@dataclass(frozen=True)
class ResolvedRepoTarget:
    """Result of parsing ``--repo`` (local dir and optional ``owner/repo``)."""

    local_root: Path
    github_owner: str | None
    github_repo: str | None


@dataclass(frozen=True)
class MultiRepoResolution:
    """Stable keys and paths for one or more ``--repo`` values."""

    roots: dict[str, Path]
    primary_key: str
    github_owner: str | None
    github_repo: str | None


def resolve_repo_target(value: str) -> ResolvedRepoTarget:
    """Return a local root path and optional ``owner``/``repo`` for GitHub API tools.

    If ``value`` is an existing directory, it is used as ``local_root`` and no
    GitHub slug is set. If it matches ``owner/repo`` (and is not an existing
    path), ``local_root`` defaults to the current working directory for
    :func:`~adt.tools.project.read_markdown` and related local reads.

    Args:
        value: Raw ``--repo`` string from the CLI.

    Returns:
        Frozen dataclass with ``local_root`` and optional GitHub owner/repo.

    Raises:
        ValueError: When ``value`` is neither a directory nor a valid slug.
    """
    v = value.strip()
    if not v:
        msg = "Repository path or owner/repo slug is empty."
        raise ValueError(msg)
    expanded = Path(v).expanduser()
    if expanded.exists() and expanded.is_dir():
        return ResolvedRepoTarget(
            local_root=expanded.resolve(),
            github_owner=None,
            github_repo=None,
        )
    if _GITHUB_SLUG.fullmatch(v):
        owner, _, repo = v.partition("/")
        return ResolvedRepoTarget(
            local_root=Path.cwd().resolve(),
            github_owner=owner,
            github_repo=repo,
        )
    msg = (
        f"Not a directory and not a valid owner/repo slug "
        f"(expected e.g. myorg/my-repo): {value!r}"
    )
    raise ValueError(msg)


def resolve_repo_targets(values: list[str]) -> MultiRepoResolution:
    """Parse several ``--repo`` strings into unique local roots and optional GitHub.

    Keys are ``r0``, ``r1``, … in first-seen order. The first ``owner/repo`` slug
    that appears sets ``github_owner`` / ``github_repo`` for project tools.

    Args:
        values: Raw ``--repo`` arguments (empty list treated as ``["."]``).

    Returns:
        Mapping of repo keys to resolved directories plus GitHub defaults.
    """
    raw = [v.strip() for v in values if v.strip()]
    if not raw:
        raw = ["."]
    targets = [resolve_repo_target(v) for v in raw]
    github_owner: str | None = None
    github_repo: str | None = None
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for t in targets:
        if t.github_owner and t.github_repo and github_owner is None:
            github_owner = t.github_owner
            github_repo = t.github_repo
        p = t.local_root.resolve()
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)
    if not unique_paths:
        unique_paths = [Path.cwd().resolve()]
    roots = {f"r{i}": path for i, path in enumerate(unique_paths)}
    return MultiRepoResolution(
        roots=roots,
        primary_key="r0",
        github_owner=github_owner,
        github_repo=github_repo,
    )
