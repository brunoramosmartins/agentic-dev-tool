"""Smoke tests for package import and version."""

from __future__ import annotations

import adt


def test_package_version() -> None:
    assert adt.__version__ == "0.2.0"
