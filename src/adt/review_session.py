"""Shared logic for running one ``review`` turn (CLI and tests).

A review submits a code file to the supervised reviewer LLM and returns a
parsed :class:`ReviewFeedback`. The previous supervised session (if any) is
loaded so the reviewer can reference the current step the user is on.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from adt.config import apply_env_overrides, load_config_file
from adt.core.llm import LLMClient
from adt.core.runner import LLMBackend
from adt.core.session import SessionContext
from adt.core.supervised_supervisor import (
    build_review_system_prompt,
    build_review_user_prompt,
    parse_review_feedback,
)
from adt.logging.json_log import log_adt, setup_adt_file_logging
from adt.models.schemas import LLMMessage, ReviewFeedback

logger = logging.getLogger(__name__)

_MAX_FILE_BYTES = 200_000


class ReviewConfigurationError(ValueError):
    """Raised when the environment or arguments prevent a review run."""


@dataclass(frozen=True)
class ReviewExecution:
    """Outcome of a review run: parsed feedback + raw answer + session snapshot."""

    feedback: ReviewFeedback | None
    raw_answer: str
    session: SessionContext


def run_review(
    *,
    file: str | Path,
    extra_context: str | None = None,
    level: str = "intermediate",
    model: str | None = None,
    verbose: bool = False,
    log_level: str | None = None,
    configure_logging: bool = True,
    llm: LLMBackend | None = None,
    session: SessionContext | None = None,
) -> ReviewExecution:
    """Read ``file``, send it to the reviewer LLM, return parsed feedback.

    Args:
        file: Path to the source file to review.
        extra_context: Optional description of what the code should do.
        level: Difficulty level for the reviewer prompt.
        model: OpenAI chat model override; otherwise from config.
        verbose: When True and ``configure_logging`` is True, raise log to DEBUG.
        log_level: File log level name.
        configure_logging: When True, set up the JSON file logger.
        llm: Inject an LLM client (used by tests). When None, build a real
            :class:`LLMClient` from environment + config.
        session: Inject a session context. When None, load from disk.

    Raises:
        ReviewConfigurationError: When the file is missing, unreadable, too
            large, or when the API key is required but absent.
    """
    path = Path(file).expanduser()
    if not path.exists() or not path.is_file():
        msg = f"File not found: {path}"
        raise ReviewConfigurationError(msg)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ReviewConfigurationError(f"Cannot stat {path}: {exc}") from exc
    if size > _MAX_FILE_BYTES:
        msg = (
            f"File {path.name} is {size} bytes; review limit is "
            f"{_MAX_FILE_BYTES} bytes."
        )
        raise ReviewConfigurationError(msg)
    try:
        code = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReviewConfigurationError(f"Cannot read {path}: {exc}") from exc

    cfg = apply_env_overrides(load_config_file())
    eff_model = model if model is not None else cfg.default_model
    eff_log = (log_level or cfg.log_level).upper()

    if configure_logging:
        lvl = getattr(logging, eff_log, logging.INFO)
        if verbose:
            lvl = logging.DEBUG
        setup_adt_file_logging(level=lvl)
        logging.getLogger("adt").setLevel(lvl)

    sess = session if session is not None else SessionContext.load()

    if llm is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            msg = "Missing OPENAI_API_KEY. Set it in the environment or in a .env file."
            raise ReviewConfigurationError(msg)
        llm = LLMClient(model=eff_model, api_key=api_key)

    system_prompt = build_review_system_prompt(level)
    user_prompt = build_review_user_prompt(
        file_path=str(path),
        code=code,
        extra_context=extra_context,
        step_context=sess.as_step_context() or None,
    )
    messages: list[LLMMessage] = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    log_adt(
        logger,
        logging.INFO,
        event="review_started",
        file=str(path),
        size_bytes=size,
        supervised_level=level,
    )

    try:
        reply = llm.chat(messages, None)
    except Exception as exc:  # noqa: BLE001
        log_adt(
            logger,
            logging.ERROR,
            event="review_llm_failure",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return ReviewExecution(
            feedback=None,
            raw_answer=(
                f"Reviewer LLM request failed ({type(exc).__name__}: {exc}). "
                "Check OPENAI_API_KEY, network, and quota."
            ),
            session=sess,
        )

    raw_answer = reply.content or ""
    feedback = parse_review_feedback(raw_answer)
    if feedback is not None:
        sess.record_feedback(feedback.overall_assessment)
        sess.save()

    log_adt(
        logger,
        logging.INFO,
        event="review_completed",
        parsed=feedback is not None,
        assessment=feedback.overall_assessment if feedback else None,
        issue_count=len(feedback.issues) if feedback else 0,
    )

    return ReviewExecution(feedback=feedback, raw_answer=raw_answer, session=sess)
