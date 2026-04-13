"""FastAPI application exposing ask, review, stats, and session endpoints."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from adt import __version__
from adt.ask_session import AskConfigurationError, run_ask
from adt.logging.json_log import setup_adt_file_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure JSON file logging once at process start."""
    setup_adt_file_logging(level=logging.INFO)
    logging.getLogger("adt").setLevel(logging.INFO)
    yield


app = FastAPI(
    title="Agentic Dev Tool API",
    description="HTTP wrapper around the same ``ask`` pipeline as the CLI.",
    version=__version__,
    lifespan=_lifespan,
)


# ── /ask models ────────────────────────────────────────────────────────


class AskRequest(BaseModel):
    """JSON body for ``POST /ask``."""

    query: str = Field(..., min_length=1, description="Natural language question.")
    repo: list[str] | None = Field(
        default=None,
        description="Repository paths or owner/repo slugs (same as CLI ``--repo``).",
    )
    github_token: str | None = Field(
        default=None,
        description="Optional GitHub PAT for this request only.",
    )
    agent: str | None = Field(
        default=None,
        description="Force ``repo_agent``, ``project_agent``, or ``research_agent``.",
    )
    no_cache: bool = Field(default=False, description="Disable repo tree disk cache.")
    model: str | None = Field(default=None, description="OpenAI model override.")
    mode: str = Field(
        default="execution",
        description="Operational mode: 'execution' or 'supervised'.",
    )
    level: str = Field(
        default="intermediate",
        description="Difficulty for supervised mode: beginner, intermediate, advanced.",
    )
    trace: bool = Field(
        default=False,
        description="When true, return trace events in the response.",
    )
    session: str = Field(
        default="default",
        description="Named session for supervised mode.",
    )


class AskResponse(BaseModel):
    """Structured agent result."""

    answer: str
    routed_agent: str
    tools_used: list[str]
    context_summary: str
    token_usage: dict[str, int] = Field(default_factory=dict)
    supervised_response: dict[str, Any] | None = Field(
        default=None,
        description="Parsed SupervisedResponse when mode=supervised.",
    )
    trace_events: list[dict[str, Any]] | None = Field(
        default=None,
        description="Serialized trace events when trace=true.",
    )


# ── /review models ─────────────────────────────────────────────────────


class ReviewRequest(BaseModel):
    """JSON body for ``POST /review``."""

    file_content: str = Field(
        ...,
        min_length=1,
        description="Full source code to review.",
    )
    file_path: str = Field(
        default="submitted_code.py",
        description="Display name for the file being reviewed.",
    )
    context: str | None = Field(
        default=None,
        description="Optional description of what the code should do.",
    )
    level: str = Field(
        default="intermediate",
        description="Difficulty: beginner, intermediate, advanced.",
    )
    model: str | None = Field(default=None, description="OpenAI model override.")
    session: str = Field(
        default="default",
        description="Named session for review context.",
    )
    max_bytes: int | None = Field(
        default=None,
        description="Override the maximum file size for review (in bytes).",
    )


class ReviewResponse(BaseModel):
    """Structured review result."""

    feedback: dict[str, Any] | None = Field(
        default=None,
        description="Parsed ReviewFeedback or null on parse failure.",
    )
    raw_answer: str
    session: dict[str, Any]


# ── /stats and /sessions models ────────────────────────────────────────


class StatsResponse(BaseModel):
    """Aggregated learning statistics."""

    sessions: int = 0
    reviews: int = 0
    supervised_steps: int = 0
    avg_steps_per_session: float = 0.0
    avg_iterations_per_step: float = 0.0
    common_issues: list[list[Any]] = Field(default_factory=list)
    improvement_trend: list[float] = Field(default_factory=list)
    total_tokens: int = 0
    assessments: dict[str, int] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Serialized SessionContext."""

    problem_summary: str = ""
    current_step: int = 0
    total_steps: int = 0
    previous_feedback: list[str] = Field(default_factory=list)
    iteration_count: int = 0


# ── endpoints ──────────────────────────────────────────────────────────


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Liveness probe; does not call external APIs."""
    return {"status": "ok", "version": __version__}


@app.post("/ask", response_model=AskResponse, tags=["ask"])
def post_ask(body: AskRequest) -> AskResponse:
    """Run one agent turn (same orchestration as ``adt ask``)."""
    try:
        exe = run_ask(
            query=body.query,
            repo=body.repo,
            github_token=body.github_token,
            force_agent=body.agent,
            verbose=False,
            log_level=None,
            no_cache=body.no_cache,
            model=body.model,
            configure_logging=False,
            trace=body.trace,
            mode=body.mode,
            level=body.level,
            session_name=body.session,
        )
    except AskConfigurationError as exc:
        detail: Any = str(exc)
        code = 503 if "OPENAI_API_KEY" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("ask failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    r = exe.response
    usage = getattr(exe.runner, "last_token_usage", None)
    tok = usage if isinstance(usage, dict) else {}

    supervised = None
    if exe.supervised_response is not None:
        supervised = exe.supervised_response.model_dump(mode="json")

    trace_events = None
    if exe.trace_context is not None:
        trace_events = [ev.model_dump(mode="json") for ev in exe.trace_context.events]

    return AskResponse(
        answer=r.answer,
        routed_agent=r.routed_agent,
        tools_used=list(r.tools_used),
        context_summary=r.context_summary,
        token_usage={k: int(v) for k, v in tok.items() if isinstance(v, int)},
        supervised_response=supervised,
        trace_events=trace_events,
    )


@app.post("/review", response_model=ReviewResponse, tags=["review"])
def post_review(body: ReviewRequest) -> ReviewResponse:
    """Review source code via the supervised reviewer LLM.

    Accepts ``file_content`` directly (no filesystem access needed).
    """
    import tempfile

    from adt.review_session import ReviewConfigurationError, run_review

    # Write content to a temp file so run_review can read it.
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(body.file_content)
            tmp_path = tmp.name
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"temp file: {exc}") from exc

    try:
        result = run_review(
            file=tmp_path,
            extra_context=body.context,
            level=body.level,
            model=body.model,
            verbose=False,
            configure_logging=False,
            max_bytes=body.max_bytes,
            session_name=body.session,
        )
    except ReviewConfigurationError as exc:
        detail_str: Any = str(exc)
        code = 503 if "OPENAI_API_KEY" in detail_str else 400
        raise HTTPException(status_code=code, detail=detail_str) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("review failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        import os

        with _suppress_os():
            os.unlink(tmp_path)

    fb = result.feedback.model_dump(mode="json") if result.feedback else None
    return ReviewResponse(
        feedback=fb,
        raw_answer=result.raw_answer,
        session=asdict(result.session),
    )


@app.get("/stats", response_model=StatsResponse, tags=["analytics"])
def get_stats(last: int | None = None) -> StatsResponse:
    """Return aggregated learning statistics."""
    from adt.analytics import compute_stats, read_learning_events

    events = read_learning_events()
    stats = compute_stats(events, last_n=last)
    return StatsResponse(
        sessions=stats.sessions,
        reviews=stats.reviews,
        supervised_steps=stats.supervised_steps,
        avg_steps_per_session=stats.avg_steps_per_session,
        avg_iterations_per_step=stats.avg_iterations_per_step,
        common_issues=[list(pair) for pair in stats.common_issues],
        improvement_trend=list(stats.improvement_trend),
        total_tokens=stats.total_tokens,
        assessments=dict(stats.assessments),
    )


@app.get("/sessions", tags=["sessions"])
def list_sessions() -> list[str]:
    """Return sorted list of named session names."""
    from adt.core.session_store import SessionStore

    return SessionStore().list()


@app.get("/sessions/{name}", response_model=SessionResponse, tags=["sessions"])
def get_session(name: str) -> SessionResponse:
    """Return a named session's state."""
    from adt.core.session_store import SessionStore

    ctx = SessionStore().load(name)
    return SessionResponse(
        problem_summary=ctx.problem_summary,
        current_step=ctx.current_step,
        total_steps=ctx.total_steps,
        previous_feedback=list(ctx.previous_feedback),
        iteration_count=ctx.iteration_count,
    )


@app.delete("/sessions/{name}", tags=["sessions"])
def delete_session(name: str) -> dict[str, str]:
    """Delete a named session."""
    from adt.core.session_store import SessionStore

    store = SessionStore()
    if not store.path(name).exists():
        raise HTTPException(status_code=404, detail=f"Session '{name}' not found.")
    store.delete(name)
    return {"status": "deleted", "session": name}


def _suppress_os() -> contextlib.AbstractContextManager[None]:
    """Context manager that suppresses :class:`OSError`."""
    return contextlib.suppress(OSError)


def create_app() -> FastAPI:
    """Return the FastAPI application (useful for ASGI servers and tests)."""
    return app
