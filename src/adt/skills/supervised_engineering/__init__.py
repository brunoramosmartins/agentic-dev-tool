"""Supervised engineering skill: teaching heuristics for the supervised mode.

This package bundles :data:`SKILL.md` with a small loader. The Markdown file
is the source of truth for how the supervised supervisor decomposes problems
and how the reviewer formulates feedback. Importing this package only exposes
the loader; the content is read lazily so test fixtures can override the path.
"""

from adt.skills.supervised_engineering.loader import (
    SKILL_FILENAME,
    SKILL_NAME,
    load_skill_content,
)

__all__ = ["SKILL_FILENAME", "SKILL_NAME", "load_skill_content"]
