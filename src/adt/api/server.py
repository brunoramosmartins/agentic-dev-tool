"""FastAPI application exposing ``/healthz`` and ``/ask``."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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


class AskResponse(BaseModel):
    """Structured agent result."""

    answer: str
    routed_agent: str
    tools_used: list[str]
    context_summary: str
    token_usage: dict[str, int] = Field(default_factory=dict)


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
    return AskResponse(
        answer=r.answer,
        routed_agent=r.routed_agent,
        tools_used=list(r.tools_used),
        context_summary=r.context_summary,
        token_usage={k: int(v) for k, v in tok.items() if isinstance(v, int)},
    )


def create_app() -> FastAPI:
    """Return the FastAPI application (useful for ASGI servers and tests)."""
    return app
