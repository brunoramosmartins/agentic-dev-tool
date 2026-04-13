"""Formal context model for loaded skills.

Each skill is represented by a :class:`SkillContext` carrying the parsed
Markdown body, a version string, and an optional variables dict that
prompt builders can substitute via ``str.format(**variables)``.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_VERSION_RE = re.compile(r"<!--\s*version:\s*(\S+)\s*-->")


class SkillContext(BaseModel):
    """Typed envelope for a loaded skill document."""

    name: str
    markdown: str
    variables: dict[str, str] = {}  # noqa: RUF012
    version: str = "0"

    model_config = ConfigDict(extra="forbid")


def parse_version(markdown: str) -> str:
    """Extract version from a ``<!-- version: X -->`` HTML comment.

    Returns ``"0"`` when no version comment is found.
    """
    match = _VERSION_RE.search(markdown)
    return match.group(1) if match else "0"
