"""Unit tests for ModeRouter."""

from __future__ import annotations

from adt.core.mode_router import ModeRouter
from adt.models.schemas import QueryRequest


def test_execution_mode_is_not_supervised() -> None:
    req = QueryRequest(query="x", mode="execution")
    assert ModeRouter.is_supervised(req) is False


def test_supervised_mode_detected() -> None:
    req = QueryRequest(query="x", mode="supervised")
    assert ModeRouter.is_supervised(req) is True


def test_default_mode_is_execution() -> None:
    req = QueryRequest(query="x")
    assert ModeRouter.is_supervised(req) is False
