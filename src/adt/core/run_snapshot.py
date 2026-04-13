"""Serializable snapshot of a Runner tool-loop state for ``--resume``.

When a run is interrupted (Ctrl+C or max iterations), the current
conversation messages, tools used so far, and routing metadata are
persisted under ``~/.adt/runs/<trace_id>.json``. A subsequent
``adt ask --resume <trace_id>`` can reload the snapshot and re-enter
the tool loop from where it stopped.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from adt.config import ensure_adt_dir
from adt.logging.json_log import log_adt

logger = logging.getLogger(__name__)


class RunSnapshot(BaseModel):
    """Serializable state of an interrupted Runner tool loop."""

    trace_id: str
    agent_name: str
    query: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    context_summary: str = ""
    model: str = "gpt-4o-mini"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RunStore:
    """Manage run snapshot files under ``~/.adt/runs/``."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir if base_dir is not None else ensure_adt_dir() / "runs"
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: RunSnapshot) -> Path:
        """Persist a snapshot and return its file path."""
        path = self._base / f"{snapshot.trace_id}.json"
        try:
            path.write_text(
                snapshot.model_dump_json(indent=2),
                encoding="utf-8",
            )
            log_adt(
                logger,
                logging.INFO,
                event="run_snapshot_saved",
                trace_id=snapshot.trace_id,
                path=str(path),
            )
        except OSError as exc:
            log_adt(
                logger,
                logging.WARNING,
                event="run_snapshot_save_failed",
                error=str(exc),
            )
        return path

    def load(self, trace_id: str) -> RunSnapshot | None:
        """Load a snapshot by trace_id, returning None if missing."""
        path = self._base / f"{trace_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return RunSnapshot.model_validate(data)
        except (OSError, json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
            log_adt(
                logger,
                logging.WARNING,
                event="run_snapshot_load_failed",
                trace_id=trace_id,
                error=str(exc),
            )
            return None

    def list(self) -> list[str]:
        """Return sorted trace_ids of saved snapshots."""
        return sorted(p.stem for p in self._base.glob("*.json"))

    def delete(self, trace_id: str) -> None:
        """Remove a snapshot file (no-op if missing)."""
        path = self._base / f"{trace_id}.json"
        if path.exists():
            path.unlink()

    def path(self, trace_id: str) -> Path:
        """Return the file path for a trace_id."""
        return self._base / f"{trace_id}.json"
