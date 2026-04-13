"""Loader utility that reads ``SKILL.md`` from the installed package.

The skill is shipped as a data file inside ``adt.skills.supervised_engineering``.
It is resolved via :mod:`importlib.resources` so the loader works both in an
editable install and from a built wheel. The content is cached after the first
read so repeated supervisor initializations do not touch the filesystem.
"""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from adt.logging.json_log import log_adt

if TYPE_CHECKING:
    from adt.skills.context import SkillContext

logger = logging.getLogger(__name__)

SKILL_NAME = "supervised_engineering"
SKILL_FILENAME = "SKILL.md"

_FALLBACK_SKILL = (
    "# Supervised Engineering Skill (fallback)\n\n"
    "Skill file could not be loaded. Behavior falls back to the built-in "
    "system prompt. Check the package installation.\n"
)

_cache: str | None = None


def _read_packaged_skill() -> str:
    """Read the bundled ``SKILL.md`` via :mod:`importlib.resources`.

    Raises:
        FileNotFoundError: When the resource is missing from the package.
    """
    package = "adt.skills.supervised_engineering"
    try:
        ref = resources.files(package).joinpath(SKILL_FILENAME)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise FileNotFoundError(f"skill package not importable: {exc}") from exc
    if not ref.is_file():
        raise FileNotFoundError(f"{SKILL_FILENAME} missing from {package}")
    return ref.read_text(encoding="utf-8")


def load_skill_content(
    *,
    path: Path | None = None,
    use_cache: bool = True,
) -> str:
    """Return the ``SKILL.md`` content for the supervised engineering skill.

    Args:
        path: Optional override pointing to a ``SKILL.md`` file on disk. When
            set, the cache is bypassed so tests can inject alternative content.
        use_cache: Cache the packaged content after the first successful read.
            Ignored when ``path`` is supplied.

    Returns:
        The raw Markdown body of the skill document. On any read failure a
        short fallback notice is returned so callers can still build a prompt.
    """
    global _cache

    if path is not None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            log_adt(
                logger,
                logging.WARNING,
                event="skill_load_failed",
                skill=SKILL_NAME,
                source=str(path),
                error=str(exc),
            )
            return _FALLBACK_SKILL

    if use_cache and _cache is not None:
        return _cache

    try:
        content = _read_packaged_skill()
    except FileNotFoundError as exc:
        log_adt(
            logger,
            logging.WARNING,
            event="skill_load_failed",
            skill=SKILL_NAME,
            source="package",
            error=str(exc),
        )
        return _FALLBACK_SKILL

    if use_cache:
        _cache = content
    return content


def load_skill_context(
    *,
    path: Path | None = None,
    use_cache: bool = True,
) -> SkillContext:
    """Return a :class:`~adt.skills.context.SkillContext` for this skill.

    Wraps :func:`load_skill_content` and parses the version comment
    from the Markdown header.
    """
    from adt.skills.context import SkillContext, parse_version

    markdown = load_skill_content(path=path, use_cache=use_cache)
    return SkillContext(
        name=SKILL_NAME,
        markdown=markdown,
        version=parse_version(markdown),
    )


def reset_cache() -> None:
    """Clear the in-memory cache (used by tests)."""
    global _cache
    _cache = None
