"""Typer CLI entry point including the ``ask`` command (all agents)."""

from __future__ import annotations

import logging
import os
from importlib import metadata
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from adt.bootstrap import build_runner
from adt.config import (
    adt_config_path,
    apply_env_overrides,
    load_config_file,
    update_config_key,
)
from adt.logging.json_log import setup_adt_file_logging
from adt.models.schemas import QueryRequest
from adt.repo_spec import resolve_repo_targets

app = typer.Typer(help="Agentic Dev Tool CLI", add_completion=False)
config_app = typer.Typer(help="View or edit ~/.adt/config.toml", add_completion=False)
app.add_typer(config_app, name="config")
console = Console()

_VALID_AGENTS = frozenset({"repo_agent", "research_agent", "project_agent"})


def _version_string() -> str:
    """Return the installed distribution version, or a dev fallback."""
    try:
        return metadata.version("agentic-dev-tool")
    except metadata.PackageNotFoundError:
        return "0.7.0-dev"


def _format_ask_panel(agent_name: str, answer: str) -> None:
    """Print the model answer with formatting tuned for the routed agent."""
    if agent_name.startswith("chain:"):
        console.print(
            Panel(
                Markdown(answer),
                title="Answer",
                border_style="yellow",
                title_align="left",
            ),
        )
        return
    if agent_name == "research_agent":
        console.print(
            Panel(
                Markdown(answer),
                title="Answer",
                border_style="cyan",
                title_align="left",
            ),
        )
        return
    if agent_name == "project_agent":
        console.print(
            Panel(
                Markdown(answer),
                title="Answer",
                border_style="magenta",
                title_align="left",
            ),
        )
        return
    console.print(Panel(answer, title="Answer", border_style="green"))


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""
    typer.echo(_version_string())


@app.command("info")
def info_cmd() -> None:
    """Print short project status and feature summary."""
    typer.echo(
        "adt — Phase 6. ask: multi-repo --repo, compare_repos, LLM routing with "
        "rule fallback, ~/.adt/config.toml (adt config show|set|path), optional "
        "agent_chain. See docs/agents.md.",
    )


@config_app.command("path")
def config_path_cmd() -> None:
    """Print the config file path."""
    typer.echo(str(adt_config_path()))


@config_app.command("show")
def config_show_cmd() -> None:
    """Print effective settings (file + ADT_* env overrides)."""
    cfg = apply_env_overrides(load_config_file())
    typer.echo(f"# effective (after env): {adt_config_path()}")
    for k, v in cfg.to_toml_table().items():
        typer.echo(f"{k} = {v!r}")


@config_app.command("set")
def config_set_cmd(
    key: Annotated[str, typer.Argument(help="Setting name (e.g. default_model).")],
    value: Annotated[
        str,
        typer.Argument(help="New value (comma-list for agent_chain)."),
    ],
) -> None:
    """Persist one key under [adt] in config.toml."""
    try:
        update_config_key(None, key, value)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Saved.")


@app.command("ask")
def ask_cmd(
    query: Annotated[
        str,
        typer.Argument(
            help="Natural language question (repository, research, or project).",
        ),
    ],
    repo: Annotated[
        list[str] | None,
        typer.Option(
            "--repo",
            "-r",
            help=(
                "Local directory or owner/repo slug; repeat for multiple checkouts."
            ),
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            help="GitHub PAT for read_issues / read_milestones (or set GITHUB_TOKEN).",
        ),
    ] = None,
    agent: Annotated[
        str | None,
        typer.Option(
            "--agent",
            "-a",
            help=(
                "Force a specific agent: repo_agent, research_agent, or project_agent "
                "(skips supervisor routing and agent_chain)."
            ),
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Print debug logs and token usage."),
    ] = False,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            help="File log level: DEBUG, INFO, WARNING, ERROR (default: config).",
        ),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            help="Disable repository tree disk cache for this request.",
        ),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help="OpenAI chat model (default: config default_model).",
        ),
    ] = None,
) -> None:
    """Ask a question: supervisor picks an agent unless ``--agent`` is set."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print(
            "[red]Missing OPENAI_API_KEY.[/red] "
            "Set it in the environment or in a `.env` file.",
        )
        raise typer.Exit(code=1)

    if agent is not None and agent not in _VALID_AGENTS:
        console.print(
            "[red]Invalid --agent.[/red] "
            f"Choose one of: {', '.join(sorted(_VALID_AGENTS))}.",
        )
        raise typer.Exit(code=1)

    cfg = apply_env_overrides(load_config_file())
    eff_model = model if model is not None else cfg.default_model
    eff_log = (log_level or cfg.log_level).upper()

    repo_list = list(repo) if repo else ["."]
    try:
        resolved = resolve_repo_targets(repo_list)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    primary_path = resolved.roots[resolved.primary_key]
    extra_paths = [
        str(p) for k, p in resolved.roots.items() if k != resolved.primary_key
    ]

    lvl = getattr(logging, eff_log, logging.INFO)
    if verbose:
        lvl = logging.DEBUG
    setup_adt_file_logging(level=lvl)
    logging.getLogger("adt").setLevel(lvl)

    github_token = token.strip() if token else None
    if not github_token:
        env_gh = os.environ.get("GITHUB_TOKEN")
        github_token = env_gh.strip() if env_gh else None

    chain = cfg.agent_chain if cfg.agent_chain else None
    runner = build_runner(
        resolved.roots,
        markdown_root=primary_path,
        primary_repo_key=resolved.primary_key,
        model=eff_model,
        api_key=api_key,
        github_token=github_token,
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
        force_agent=agent,
        options=opts,
    )
    try:
        response = runner.run(request)
    except Exception as exc:  # noqa: BLE001 — last-resort CLI guard
        console.print(
            "[red]Unexpected error while running the agent.[/red] "
            f"({type(exc).__name__}: {exc})",
        )
        raise typer.Exit(code=1) from exc

    routed = response.routed_agent or agent or "supervisor"
    console.print(f"[dim]Agent:[/dim] [bold]{routed}[/bold]")
    _format_ask_panel(response.routed_agent or agent or "", response.answer)
    tools_line = ", ".join(response.tools_used) if response.tools_used else "none"
    console.print(f"[dim]Tools used:[/dim] {tools_line}")
    if verbose:
        console.print(f"[dim]Last LLM token usage:[/dim] {runner.last_token_usage}")
        ctx = response.context_summary
        console.print(f"[dim]Context summary (truncated):[/dim] {ctx!r}")
        br = getattr(runner, "last_budget_report", None)
        if br:
            console.print(f"[dim]Token budget (estimated):[/dim] {br}")


if __name__ == "__main__":
    app()
