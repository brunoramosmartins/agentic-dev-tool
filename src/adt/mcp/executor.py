"""Validate and execute tool calls through a registry."""

from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Any

import jsonschema
from jsonschema import ValidationError

from adt.mcp.registry import ToolRegistry
from adt.models.schemas import ToolCall, ToolResult

logger = logging.getLogger(__name__)


class ExecutionController:
    """Runs tools registered in a ``ToolRegistry`` with schema checks and logging."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """Resolve ``tool_call.name``, validate args, invoke handler, return result."""
        start = time.perf_counter()
        try:
            definition = self._registry.get(tool_call.name)
        except KeyError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            self._log(
                tool_call.name,
                tool_call.arguments,
                duration_ms,
                False,
                str(exc),
            )
            return ToolResult(
                name=tool_call.name,
                output="",
                success=False,
                error=str(exc),
            )

        try:
            jsonschema.validate(
                instance=tool_call.arguments,
                schema=definition.parameters,
            )
        except ValidationError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            err = f"argument validation failed: {exc.message}"
            self._log(
                tool_call.name,
                tool_call.arguments,
                duration_ms,
                False,
                err,
            )
            return ToolResult(
                name=tool_call.name,
                output="",
                success=False,
                error=err,
            )

        try:
            bound = self._bind_arguments(definition.handler, tool_call.arguments)
            raw = definition.handler(**bound)
            out = raw if isinstance(raw, str) else json.dumps(raw, default=str)
            duration_ms = (time.perf_counter() - start) * 1000
            self._log(tool_call.name, tool_call.arguments, duration_ms, True, None)
            return ToolResult(name=tool_call.name, output=out, success=True)
        except Exception as exc:  # noqa: BLE001 — tools must never crash the runner
            duration_ms = (time.perf_counter() - start) * 1000
            err = f"{type(exc).__name__}: {exc}"
            self._log(
                tool_call.name,
                tool_call.arguments,
                duration_ms,
                False,
                err,
            )
            return ToolResult(
                name=tool_call.name,
                output="",
                success=False,
                error=err,
            )

    def _bind_arguments(
        self,
        handler: Any,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Pass only keys the callable accepts (variadic-safe)."""
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError):
            return dict(arguments)
        params = sig.parameters
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            return dict(arguments)
        allowed = {
            name
            for name, p in params.items()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }
        return {k: v for k, v in arguments.items() if k in allowed}

    def _log(
        self,
        name: str,
        arguments: dict[str, Any],
        duration_ms: float,
        success: bool,
        error: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": "tool_execution",
            "tool": name,
            "arguments": arguments,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
        if error is not None:
            payload["error"] = error
        logger.info("%s", json.dumps(payload, default=str))
