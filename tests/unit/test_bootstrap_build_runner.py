"""Smoke-test :func:`adt.bootstrap.build_runner` wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from adt.bootstrap import build_runner


@patch("adt.core.llm.OpenAI")
def test_build_runner_multi_root_registers(
    mock_openai: MagicMock,
    tmp_path: Path,
) -> None:
    mock_openai.return_value = MagicMock()
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    runner = build_runner(
        {"r0": a, "r1": b},
        api_key="sk-test",
        use_llm_routing=False,
    )
    assert len(runner._repo_roots) == 2
    assert "compare_repos" in {
        t["function"]["name"] for t in runner._registry.to_openai_format("repo_agent")
    }
