"""Runner loads multi-root context for repo_agent."""

from __future__ import annotations

from pathlib import Path

from adt.agents.project_agent import ProjectAgent
from adt.agents.repo_agent import RepoAgent
from adt.agents.research_agent import ResearchAgent
from adt.bootstrap import register_repo_tools, register_research_tools
from adt.core.runner import Runner
from adt.core.supervisor import Supervisor
from adt.mcp.context import ContextBuilder
from adt.mcp.executor import ExecutionController
from adt.mcp.registry import ToolRegistry
from adt.models.schemas import LLMMessage, QueryRequest
from tests.fake_llm import FakeLLM


class _SpyMultiContext(ContextBuilder):
    """Counts :meth:`build_from_repos` invocations."""

    def __init__(self) -> None:
        super().__init__(use_repo_tree_cache=False)
        self.repos_calls = 0

    def build_from_repos(
        self,
        roots: dict[str, Path],
        *,
        query: str | None = None,
        use_cache: bool = True,
    ) -> str:
        self.repos_calls += 1
        return super().build_from_repos(
            roots,
            query=query,
            use_cache=use_cache,
        )


def test_runner_uses_build_from_repos_for_two_roots(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "main.py").write_text("x=1\n", encoding="utf-8")
    (b / "main.py").write_text("y=2\n", encoding="utf-8")
    reg = ToolRegistry()
    register_repo_tools(reg, {"r0": a, "r1": b})
    register_research_tools(reg)
    spy = _SpyMultiContext()
    agents = {
        "repo_agent": RepoAgent(),
        "project_agent": ProjectAgent(),
        "research_agent": ResearchAgent(),
    }
    runner = Runner(
        Supervisor(),
        FakeLLM([LLMMessage(role="assistant", content="done.")]),
        spy,
        ExecutionController(reg),
        reg,
        agents,
        repo_roots={"r0": a, "r1": b},
    )
    res = runner.run(
        QueryRequest(
            query="explain both codebases",
            repo_path=str(a),
            additional_repo_paths=[str(b)],
            force_agent="repo_agent",
        ),
    )
    assert res.answer == "done."
    assert spy.repos_calls == 1
