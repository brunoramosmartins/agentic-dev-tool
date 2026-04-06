"""Wire default services for the ``ask`` command and integration tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from adt.agents.base import BaseAgent

if TYPE_CHECKING:
    from adt.tracing.context import TraceContext
from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.hybrid_supervisor import HybridSupervisor
from adt.core.llm import LLMClient
from adt.core.runner import Runner
from adt.mcp.context import ContextBuilder, default_cache_ttl
from adt.mcp.executor import ExecutionController
from adt.mcp.registry import ToolDefinition, ToolRegistry
from adt.tools import compare as compare_tools
from adt.tools import project as project_tools
from adt.tools import repo as repo_tools
from adt.tools import research as research_tools


def register_repo_tools(
    registry: ToolRegistry,
    repo_roots: dict[str, Path],
    *,
    primary_repo_key: str | None = None,
) -> None:
    """Register repo tools scoped to one or more roots keyed by ``repo_key``.

    Args:
        registry: Registry without conflicting tool names.
        repo_roots: Map of session ids (e.g. ``r0``) to repository roots.
        primary_repo_key: Default ``repo_key`` when the model omits it.
    """
    roots = {k: v.resolve() for k, v in repo_roots.items()}
    if not roots:
        msg = "repo_roots must not be empty"
        raise ValueError(msg)
    keys = list(roots.keys())
    default_key = (
        primary_repo_key
        if primary_repo_key is not None and primary_repo_key in roots
        else keys[0]
    )
    key_list = ", ".join(keys)

    def _root(repo_key: str) -> Path:
        k = repo_key.strip() if repo_key else default_key
        if k not in roots:
            msg = f"unknown repo_key {k!r} (known: {key_list})"
            raise ValueError(msg)
        return roots[k]

    def read_repo_tree(
        repo_key: str | None = None,
        path: str = ".",
        max_depth: int = 3,
    ) -> str:
        """Tree listing for the chosen repository session id."""
        try:
            root = _root(repo_key or default_key)
        except ValueError as exc:
            return f"error: {exc}"
        return repo_tools.read_repo_tree(root, path=path, max_depth=max_depth)

    def read_file(
        path: str,
        repo_key: str | None = None,
        max_lines: int = 200,
    ) -> str:
        """Read a file under the chosen repository root."""
        try:
            root = _root(repo_key or default_key)
        except ValueError as exc:
            return f"error: {exc}"
        return repo_tools.read_file(root, path, max_lines=max_lines)

    def search_code(
        pattern: str,
        path: str = ".",
        repo_key: str | None = None,
        max_results: int = 20,
    ) -> str:
        """Search under the chosen repository root."""
        try:
            root = _root(repo_key or default_key)
        except ValueError as exc:
            return f"error: {exc}"
        return repo_tools.search_code(
            root,
            path,
            pattern,
            max_results=max_results,
        )

    def compare_repos(repo_a: str, repo_b: str) -> str:
        """Structured diff between two registered repository keys."""
        return compare_tools.compare_repos(roots, repo_a.strip(), repo_b.strip())

    repo_key_prop: dict[str, Any] = {
        "type": "string",
        "description": (
            f"Repository session id ({key_list}). Defaults to {default_key!r}."
        ),
        "enum": keys,
    }

    registry.register(
        ToolDefinition(
            name="read_repo_tree",
            description=(
                "Return a text tree of files and directories under a path, "
                "respecting .gitignore and skipping common build/venv folders. "
                f"Session repos: {key_list}."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_key": repo_key_prop,
                    "path": {
                        "type": "string",
                        "description": "Directory relative to repo root (default '.').",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth below path (default 3, max 20).",
                        "minimum": 0,
                        "maximum": 20,
                    },
                },
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=read_repo_tree,
        ),
    )
    registry.register(
        ToolDefinition(
            name="read_file",
            description=(
                "Read a UTF-8 text file under the repo with line numbers; "
                "truncates after max_lines."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_key": repo_key_prop,
                    "path": {
                        "type": "string",
                        "description": "File path relative to repository root.",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Max lines from start of file (default 200).",
                        "minimum": 1,
                        "maximum": 2000,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=read_file,
        ),
    )
    registry.register(
        ToolDefinition(
            name="search_code",
            description=(
                "Regex search across text files under a directory; "
                "skips gitignored paths and binary files."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_key": repo_key_prop,
                    "path": {
                        "type": "string",
                        "description": "Directory relative to repo root (default '.').",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression (Python re syntax).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum matching lines to return (default 20).",
                        "minimum": 1,
                        "maximum": 200,
                    },
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=search_code,
        ),
    )
    registry.register(
        ToolDefinition(
            name="compare_repos",
            description=(
                "Compare two registered local repositories: file sets, overlap, "
                f"and key manifest files. Valid keys: {key_list}."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "repo_a": {
                        "type": "string",
                        "description": "First repo_key.",
                        "enum": keys,
                    },
                    "repo_b": {
                        "type": "string",
                        "description": "Second repo_key.",
                        "enum": keys,
                    },
                },
                "required": ["repo_a", "repo_b"],
                "additionalProperties": False,
            },
            allowed_agents=["repo_agent"],
            handler=compare_repos,
        ),
    )


def register_research_tools(registry: ToolRegistry) -> None:
    """Register arXiv search and article fetch tools for ``research_agent``.

    Handlers are stateless and open short-lived HTTP clients per call.

    Args:
        registry: Registry that must not already define ``search_papers`` or
            ``fetch_article``.
    """
    registry.register(
        ToolDefinition(
            name="search_papers",
            description=(
                "Search arXiv for academic papers by keywords or phrases. "
                "Returns titles, authors, abstract snippets, and abstract URLs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms (mapped to arXiv all: query).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max papers to return (1–50, default 10).",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            allowed_agents=["research_agent"],
            handler=research_tools.search_papers,
        ),
    )
    registry.register(
        ToolDefinition(
            name="fetch_article",
            description=(
                "Fetch a public http(s) web page and return extracted plain text. "
                "Use for HTML or text articles; local and private hosts are blocked."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Absolute http or https URL to download.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": (
                            "Maximum characters of extracted text (default 80000)."
                        ),
                        "minimum": 1000,
                        "maximum": 500000,
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            allowed_agents=["research_agent"],
            handler=research_tools.fetch_article,
        ),
    )


def register_project_tools(
    registry: ToolRegistry,
    markdown_root: Path,
    *,
    token: str | None = None,
) -> None:
    """Register GitHub and local markdown tools for ``project_agent``.

    Handlers for issues and milestones pass through ``token`` for authenticated
    GitHub API access (higher rate limits). ``read_markdown`` is confined to
    ``markdown_root``.

    Args:
        registry: Registry without conflicting tool names.
        markdown_root: Base path for :func:`~adt.tools.project.read_markdown`.
        token: Optional GitHub PAT (or ``GITHUB_TOKEN`` supplied by the caller).
    """
    root = markdown_root.resolve()

    def read_issues(
        owner: str,
        repo: str,
        state: str = "open",
        labels: str = "",
        max_results: int = 30,
    ) -> str:
        """List issues via :func:`adt.tools.project.read_issues` with shared token."""
        return project_tools.read_issues(
            owner,
            repo,
            state=state,
            labels=labels,
            max_results=max_results,
            token=token,
        )

    def read_milestones(
        owner: str,
        repo: str,
        state: str = "open",
        max_results: int = 20,
    ) -> str:
        """List milestones via :func:`adt.tools.project.read_milestones`."""
        return project_tools.read_milestones(
            owner,
            repo,
            state=state,
            max_results=max_results,
            token=token,
        )

    def read_markdown(path: str, max_chars: int = 120_000) -> str:
        """Read markdown under the configured root."""
        return project_tools.read_markdown(root, path, max_chars=max_chars)

    registry.register(
        ToolDefinition(
            name="read_issues",
            description=(
                "List GitHub issues for a repository (pull requests excluded). "
                "Unauthenticated calls are rate-limited (~60/hour per IP); "
                "prefer a token for private repos or heavier use."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "GitHub user or organization login.",
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name.",
                    },
                    "state": {
                        "type": "string",
                        "description": "open, closed, or all (default open).",
                        "enum": ["open", "closed", "all"],
                    },
                    "labels": {
                        "type": "string",
                        "description": "Comma-separated label filters (optional).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max issues to return (1–100, default 30).",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["owner", "repo"],
                "additionalProperties": False,
            },
            allowed_agents=["project_agent"],
            handler=read_issues,
        ),
    )
    registry.register(
        ToolDefinition(
            name="read_milestones",
            description=(
                "List GitHub milestones for a repository with open/closed counts."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Owner login."},
                    "repo": {"type": "string", "description": "Repository name."},
                    "state": {
                        "type": "string",
                        "description": "open, closed, or all (default open).",
                        "enum": ["open", "closed", "all"],
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max milestones (1–50, default 20).",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["owner", "repo"],
                "additionalProperties": False,
            },
            allowed_agents=["project_agent"],
            handler=read_milestones,
        ),
    )
    registry.register(
        ToolDefinition(
            name="read_markdown",
            description=(
                "Read a local .md or .markdown file relative to the session root; "
                "YAML front matter is stripped when present."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the markdown file.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters of body text (default 120000).",
                        "minimum": 1000,
                        "maximum": 500000,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            allowed_agents=["project_agent"],
            handler=read_markdown,
        ),
    )


def build_runner(
    repo_roots: Path | dict[str, Path],
    *,
    markdown_root: Path | None = None,
    primary_repo_key: str | None = None,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    github_token: str | None = None,
    max_tool_iterations: int = 5,
    use_context_cache: bool = True,
    context_cache_ttl: float | None = None,
    token_budget_total: int | None = None,
    use_llm_routing: bool = True,
    routing_model: str | None = None,
    agent_chain: list[str] | None = None,
    trace: TraceContext | None = None,
) -> Runner:
    """Construct a :class:`~adt.core.runner.Runner` for the full agent/tool set.

    Args:
        repo_roots: Single path or map of session ids (``r0``, …) to repo roots.
        markdown_root: Base for ``read_markdown`` (defaults to primary repo root).
        primary_repo_key: Default repo id for tools (defaults to first key).
        model: OpenAI chat model name.
        api_key: Optional API key (falls back to ``OPENAI_API_KEY`` in the client).
        github_token: Optional token forwarded to GitHub REST tools.
        max_tool_iterations: Upper bound on LLM/tool round-trips.
        use_context_cache: When True, cache repository tree listings on disk.
        context_cache_ttl: Override tree cache TTL (seconds).
        token_budget_total: Override logical token window for context budgeting.
        use_llm_routing: When True, classify intent with a small JSON LLM call first.
        routing_model: Model name for routing (defaults to ``model``).
        agent_chain: When non-empty and ``force_agent`` is unset, run this sequence.

    Returns:
        A runner with repo, research, and project tools registered.
    """
    if isinstance(repo_roots, Path):
        roots_map: dict[str, Path] = {"r0": repo_roots.resolve()}
        pk = "r0"
    else:
        roots_map = {k: v.resolve() for k, v in repo_roots.items()}
        if not roots_map:
            msg = "repo_roots mapping must not be empty"
            raise ValueError(msg)
        if primary_repo_key is not None and primary_repo_key in roots_map:
            pk = primary_repo_key
        else:
            pk = next(iter(roots_map))
    md = markdown_root.resolve() if markdown_root is not None else roots_map[pk]

    registry = ToolRegistry()
    register_repo_tools(registry, roots_map, primary_repo_key=pk)
    register_research_tools(registry)
    register_project_tools(registry, md, token=github_token)
    llm = LLMClient(model=model, api_key=api_key)
    supervisor = HybridSupervisor(
        llm=llm,
        use_llm_routing=use_llm_routing,
        routing_model=routing_model,
        trace=trace,
    )
    ttl = context_cache_ttl if context_cache_ttl is not None else default_cache_ttl()
    context = ContextBuilder(
        tiktoken_model=model,
        use_repo_tree_cache=use_context_cache,
        cache_ttl_seconds=ttl,
        total_token_budget=token_budget_total,
        trace=trace,
    )
    executor = ExecutionController(registry)
    agents: dict[str, BaseAgent] = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    return Runner(
        supervisor,
        llm,
        context,
        executor,
        registry,
        agents,
        max_tool_iterations=max_tool_iterations,
        repo_roots=roots_map,
        agent_chain=list(agent_chain or []),
        trace=trace,
    )


def build_runner_for_repo(
    repo_root: Path,
    *,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    github_token: str | None = None,
    max_tool_iterations: int = 5,
    use_context_cache: bool = True,
    context_cache_ttl: float | None = None,
    token_budget_total: int | None = None,
    use_llm_routing: bool = True,
    routing_model: str | None = None,
    agent_chain: list[str] | None = None,
) -> Runner:
    """Backward-compatible alias for :func:`build_runner` with a repository path."""
    return build_runner(
        repo_root,
        model=model,
        api_key=api_key,
        github_token=github_token,
        max_tool_iterations=max_tool_iterations,
        use_context_cache=use_context_cache,
        context_cache_ttl=context_cache_ttl,
        token_budget_total=token_budget_total,
        use_llm_routing=use_llm_routing,
        routing_model=routing_model,
        agent_chain=agent_chain,
    )
