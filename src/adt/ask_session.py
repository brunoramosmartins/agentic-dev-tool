"""Shared logic for running one ``ask`` turn (CLI, HTTP API, tests)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from adt.bootstrap import build_runner
from adt.config import apply_env_overrides, load_config_file
from adt.core.runner import Runner
from adt.logging.json_log import setup_adt_file_logging
from adt.models.schemas import AgentResponse, QueryRequest
from adt.repo_spec import resolve_repo_targets

_VALID_AGENTS = frozenset({"repo_agent", "research_agent", "project_agent"})


class AskConfigurationError(ValueError):
    """Raised when the environment or arguments prevent a run (e.g. missing API key)."""


@dataclass(frozen=True)
class AskExecution:
    """Outcome of a single agent run plus the runner for metrics."""

    response: AgentResponse
    runner: Runner


def run_ask(
    *,
    query: str,
    repo: list[str] | None = None,
    github_token: str | None = None,
    force_agent: str | None = None,
    verbose: bool = False,
    log_level: str | None = None,
    no_cache: bool = False,
    model: str | None = None,
    configure_logging: bool = True,
) -> AskExecution:
    """Resolve repos, build a :class:`~adt.core.runner.Runner`, and run the query.

    Args:
        query: User natural-language question.
        repo: ``--repo`` values (dirs or ``owner/repo`` slugs); default ``["."]``.
        github_token: Optional PAT; falls back to ``GITHUB_TOKEN`` in the environment.
        force_agent: When set, skip supervisor routing and ``agent_chain``.
        verbose: When True and ``configure_logging`` is True, set log level to DEBUG.
        log_level: File log level name if ``configure_logging`` is True.
        no_cache: Disable repository tree disk cache for this request.
        model: OpenAI model override; otherwise config / default.
        configure_logging: When True, call ``setup_adt_file_logging`` (JSON file logs).

    Returns:
        :class:`AskExecution` with the response and runner (token usage, budget).

    Raises:
        AskConfigurationError: Missing API key, invalid ``force_agent``, or bad repos.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "Missing OPENAI_API_KEY. Set it in the environment or in a `.env` file."
        raise AskConfigurationError(msg)

    if force_agent is not None and force_agent not in _VALID_AGENTS:
        known = ", ".join(sorted(_VALID_AGENTS))
        msg = f"Invalid agent {force_agent!r}. Choose one of: {known}."
        raise AskConfigurationError(msg)

    cfg = apply_env_overrides(load_config_file())
    eff_model = model if model is not None else cfg.default_model
    eff_log = (log_level or cfg.log_level).upper()

    repo_list = list(repo) if repo else ["."]
    try:
        resolved = resolve_repo_targets(repo_list)
    except ValueError as exc:
        raise AskConfigurationError(str(exc)) from exc

    primary_path = resolved.roots[resolved.primary_key]
    extra_paths = [
        str(p) for k, p in resolved.roots.items() if k != resolved.primary_key
    ]

    if configure_logging:
        lvl = getattr(logging, eff_log, logging.INFO)
        if verbose:
            lvl = logging.DEBUG
        setup_adt_file_logging(level=lvl)
        logging.getLogger("adt").setLevel(lvl)

    tok = github_token.strip() if github_token else None
    if not tok:
        env_gh = os.environ.get("GITHUB_TOKEN")
        tok = env_gh.strip() if env_gh else None

    chain = cfg.agent_chain if cfg.agent_chain else None
    runner = build_runner(
        resolved.roots,
        markdown_root=primary_path,
        primary_repo_key=resolved.primary_key,
        model=eff_model,
        api_key=api_key,
        github_token=tok,
        use_context_cache=not no_cache,
        context_cache_ttl=cfg.cache_ttl_seconds,
        token_budget_total=cfg.token_budget,
        use_llm_routing=cfg.use_llm_routing,
        routing_model=cfg.routing_model,
        agent_chain=chain,
        max_tool_iterations=cfg.max_tool_iterations,
    )
    opts: dict[str, Any] = {}
    if no_cache:
        opts["no_cache"] = True
    request = QueryRequest(
        query=query,
        repo_path=str(primary_path),
        additional_repo_paths=extra_paths,
        github_owner=resolved.github_owner,
        github_repo=resolved.github_repo,
        force_agent=force_agent,
        options=opts,
    )
    response = runner.run(request)
    return AskExecution(response=response, runner=runner)
