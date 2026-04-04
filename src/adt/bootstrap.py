"""Wire default services for the ``ask`` command and integration tests."""

from __future__ import annotations

from pathlib import Path

from adt.agents.base import BaseAgent
from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.core.llm import LLMClient
from adt.core.runner import Runner
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.mcp.registry import ToolDefinition, ToolRegistry
from adt.tools import repo as repo_tools


def register_repo_tools(registry: ToolRegistry, repo_root: Path) -> None:
    """Register repo tools (tree, file read, search) scoped to ``repo_root``.

    Handlers resolve paths strictly under ``repo_root`` to avoid path traversal.

    Args:
        registry: Empty or partially filled tool registry (must not already define
            these three names).
        repo_root: Filesystem root passed to ``--repo`` for the current run.
    """
    root = repo_root.resolve()

    def read_repo_tree(path: str = ".", max_depth: int = 3) -> str:
        """Delegate to :func:`adt.tools.repo.read_repo_tree` with a fixed root."""
        return repo_tools.read_repo_tree(root, path=path, max_depth=max_depth)

    def read_file(path: str, max_lines: int = 200) -> str:
        """Delegate to :func:`adt.tools.repo.read_file` with a fixed root."""
        return repo_tools.read_file(root, path, max_lines=max_lines)

    def search_code(pattern: str, path: str = ".", max_results: int = 20) -> str:
        """Delegate to :func:`adt.tools.repo.search_code` with a fixed root."""
        return repo_tools.search_code(
            root,
            path,
            pattern,
            max_results=max_results,
        )

    registry.register(
        ToolDefinition(
            name="read_repo_tree",
            description=(
                "Return a text tree of files and directories under a path, "
                "respecting .gitignore and skipping common build/venv folders."
            ),
            parameters={
                "type": "object",
                "properties": {
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


def build_runner_for_repo(
    repo_root: Path,
    *,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    max_tool_iterations: int = 5,
) -> Runner:
    """Construct a :class:`~adt.core.runner.Runner` scoped to one repository path.

    Args:
        repo_root: Local repository directory for tools and context.
        model: OpenAI chat model name.
        api_key: Optional API key (falls back to ``OPENAI_API_KEY`` in the client).
        max_tool_iterations: Upper bound on LLM/tool round-trips.

    Returns:
        A fully wired runner with repo tools registered for ``repo_agent``.
    """
    registry = ToolRegistry()
    register_repo_tools(registry, repo_root)
    supervisor = Supervisor()
    llm = LLMClient(model=model, api_key=api_key)
    context = ContextBuilder()
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
    )
