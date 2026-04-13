"""Unit tests for Phase 10.4 — Pedagogy & Intelligence.

Covers:
- P10-14: Embedding-based issue classifier
- P10-15: ``adt ask --resume`` and run snapshots
- P10-16: Plugin system for skills and tools
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from adt.cli.app import app

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── P10-14: Classifier ────────────────────────────────────────────────


class TestKeywordClassifier:
    """Keyword classifier extracted to classifier module."""

    def test_off_by_one(self) -> None:
        from adt.analytics.classifier import keyword_classify
        from adt.models.schemas import CodeIssue

        issue = CodeIssue(severity="warning", description="off-by-one in loop")
        assert keyword_classify(issue) == "off_by_one"

    def test_empty_description(self) -> None:
        from adt.analytics.classifier import keyword_classify
        from adt.models.schemas import CodeIssue

        issue = CodeIssue(severity="suggestion", description="")
        assert keyword_classify(issue) == "other"

    def test_fallback_to_other(self) -> None:
        from adt.analytics.classifier import keyword_classify
        from adt.models.schemas import CodeIssue

        issue = CodeIssue(severity="suggestion", description="some random thing xyzzy")
        assert keyword_classify(issue) == "other"


class TestEmbeddingClassifier:
    """Embedding classifier with mocked backend."""

    def _make_backend(self):
        """Create a mock embedding backend returning deterministic vectors."""

        class FakeBackend:
            def __init__(self):
                self.call_count = 0

            def embed(self, texts: list[str]) -> list[list[float]]:
                self.call_count += 1
                # Return a simple hash-based vector for each text
                result = []
                for text in texts:
                    h = hash(text) % 1000
                    vec = [float(h % (i + 1)) / 100.0 for i in range(8)]
                    result.append(vec)
                return result

        return FakeBackend()

    def test_classify_returns_category(self) -> None:
        from adt.analytics.classifier import EmbeddingClassifier
        from adt.models.schemas import CodeIssue

        backend = self._make_backend()
        clf = EmbeddingClassifier(backend)
        issue = CodeIssue(
            severity="warning",
            description="boundary error in loop index",
        )
        result = clf.classify(issue)
        # Should return some category (not necessarily off_by_one with fake embeddings)
        assert isinstance(result, str)
        assert backend.call_count >= 1

    def test_classify_empty_description(self) -> None:
        from adt.analytics.classifier import EmbeddingClassifier
        from adt.models.schemas import CodeIssue

        backend = self._make_backend()
        clf = EmbeddingClassifier(backend)
        assert clf.classify(CodeIssue(severity="error", description="")) == "other"

    def test_classify_falls_back_on_error(self) -> None:
        from adt.analytics.classifier import EmbeddingClassifier
        from adt.models.schemas import CodeIssue

        class FailBackend:
            def embed(self, texts: list[str]) -> list[list[float]]:
                raise RuntimeError("API down")

        clf = EmbeddingClassifier(FailBackend())
        issue = CodeIssue(
            severity="warning",
            description="off-by-one boundary error",
        )
        # Falls back to keyword classifier
        result = clf.classify(issue)
        assert result == "off_by_one"

    def test_cache_prototypes(self, tmp_path: Path) -> None:
        from adt.analytics.classifier import EmbeddingClassifier
        from adt.models.schemas import CodeIssue

        backend = self._make_backend()
        clf = EmbeddingClassifier(backend)

        # Force prototype computation
        issue = CodeIssue(severity="error", description="test")
        clf.classify(issue)

        # Should have computed prototypes
        assert clf._initialized
        assert len(clf._proto_embeddings) > 0


class TestCosineHelper:
    def test_identical_vectors(self) -> None:
        from adt.analytics.classifier import _cosine_similarity

        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        from adt.analytics.classifier import _cosine_similarity

        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector(self) -> None:
        from adt.analytics.classifier import _cosine_similarity

        assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


class TestClassifierCLI:
    def test_stats_classifier_flag_exists(self) -> None:
        result = runner.invoke(app, ["stats", "--help"])
        assert "--classifier" in _strip_ansi(result.stdout)


# ── P10-15: Run snapshots and --resume ─────────────────────────────────


class TestRunSnapshot:
    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        from adt.core.run_snapshot import RunSnapshot, RunStore

        store = RunStore(base_dir=tmp_path)
        snap = RunSnapshot(
            trace_id="abc123",
            agent_name="repo_agent",
            query="what is this?",
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What is this?"},
            ],
            tools_used=["read_repo_tree"],
            iteration=2,
            max_iterations=5,
        )
        store.save(snap)
        loaded = store.load("abc123")
        assert loaded is not None
        assert loaded.trace_id == "abc123"
        assert loaded.agent_name == "repo_agent"
        assert len(loaded.messages) == 2
        assert loaded.tools_used == ["read_repo_tree"]
        assert loaded.iteration == 2

    def test_list(self, tmp_path: Path) -> None:
        from adt.core.run_snapshot import RunSnapshot, RunStore

        store = RunStore(base_dir=tmp_path)
        for tid in ["zzz", "aaa", "mmm"]:
            store.save(RunSnapshot(trace_id=tid, agent_name="x", query="q"))
        assert store.list() == ["aaa", "mmm", "zzz"]

    def test_delete(self, tmp_path: Path) -> None:
        from adt.core.run_snapshot import RunSnapshot, RunStore

        store = RunStore(base_dir=tmp_path)
        store.save(RunSnapshot(trace_id="del", agent_name="x", query="q"))
        assert "del" in store.list()
        store.delete("del")
        assert "del" not in store.list()

    def test_load_missing(self, tmp_path: Path) -> None:
        from adt.core.run_snapshot import RunStore

        store = RunStore(base_dir=tmp_path)
        assert store.load("nonexistent") is None

    def test_delete_missing_noop(self, tmp_path: Path) -> None:
        from adt.core.run_snapshot import RunStore

        RunStore(base_dir=tmp_path).delete("ghost")  # should not raise


class TestRunnerSnapshotRestore:
    """Runner.snapshot() and Runner.restore_messages()."""

    def test_snapshot_creates_serializable_object(self) -> None:
        from unittest.mock import MagicMock

        from adt.core.runner import Runner
        from adt.models.schemas import LLMMessage, ToolCall

        runner_obj = Runner(
            supervisor=MagicMock(),
            llm=MagicMock(model="gpt-4o-mini"),
            context_builder=MagicMock(),
            executor=MagicMock(),
            registry=MagicMock(),
            agents={},
        )
        messages = [
            LLMMessage(role="system", content="sys"),
            LLMMessage(role="user", content="hello"),
            LLMMessage(
                role="assistant",
                content="",
                tool_calls=[
                    ToolCall(id="c1", name="read_file", arguments={"path": "x"}),
                ],
            ),
            LLMMessage(role="tool", content="file contents", tool_call_id="c1"),
        ]
        snap = runner_obj.snapshot(
            trace_id="t1",
            agent_name="repo_agent",
            query="test",
            messages=messages,
            tools_used=["read_file"],
            iteration=1,
        )
        assert snap.trace_id == "t1"
        assert len(snap.messages) == 4
        # Should be JSON-serializable
        json.loads(snap.model_dump_json())

    def test_restore_messages(self) -> None:
        from adt.core.run_snapshot import RunSnapshot
        from adt.core.runner import Runner

        snap = RunSnapshot(
            trace_id="t2",
            agent_name="repo_agent",
            query="test",
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "hello"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": "c1", "name": "read_file", "arguments": {"path": "x"}},
                    ],
                },
                {"role": "tool", "content": "data", "tool_call_id": "c1"},
            ],
        )
        messages = Runner.restore_messages(snap)
        assert len(messages) == 4
        assert messages[0].role == "system"
        assert messages[2].tool_calls is not None
        assert messages[2].tool_calls[0].name == "read_file"
        assert messages[3].tool_call_id == "c1"


class TestResumeCLI:
    def test_resume_flag_exists(self) -> None:
        result = runner.invoke(app, ["ask", "--help"])
        assert "--resume" in _strip_ansi(result.stdout)

    def test_resume_missing_snapshot(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("adt.core.run_snapshot.ensure_adt_dir", lambda: tmp_path)
        result = runner.invoke(app, ["ask", "test", "--resume", "nonexistent"])
        assert result.exit_code == 1

    def test_runs_list_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("adt.core.run_snapshot.ensure_adt_dir", lambda: tmp_path)
        result = runner.invoke(app, ["runs", "list"])
        assert result.exit_code == 0
        assert "No saved runs" in result.stdout


# ── P10-16: Plugin system ──────────────────────────────────────────────


class TestPluginSkills:
    def test_discover_skills_empty(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_skills

        assert discover_skills(tmp_path) == []

    def test_discover_skills_with_skill(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_skills

        skill_dir = tmp_path / "skills" / "my_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "<!-- version: 1 -->\n# My Skill\nContent here.",
            encoding="utf-8",
        )
        results = discover_skills(tmp_path)
        assert len(results) == 1
        assert results[0]["name"] == "my_skill"
        assert "My Skill" in results[0]["markdown"]

    def test_discover_skills_missing_md(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_skills

        (tmp_path / "skills" / "broken").mkdir(parents=True)
        # No SKILL.md
        assert discover_skills(tmp_path) == []

    def test_load_plugin_skills(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import load_plugin_skills

        skill_dir = tmp_path / "skills" / "test_skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "<!-- version: 3 -->\n# Test\n",
            encoding="utf-8",
        )
        contexts = load_plugin_skills(tmp_path)
        assert len(contexts) == 1
        assert contexts[0].name == "test_skill"
        assert contexts[0].version == "3"


class TestPluginTools:
    def test_discover_tools_empty(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_tools

        assert discover_tools(tmp_path) == []

    def test_discover_tools_with_tool(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_tools

        tool_dir = tmp_path / "tools" / "my_tool"
        tool_dir.mkdir(parents=True)
        (tool_dir / "tool.py").write_text(
            "def register(registry): pass\n",
            encoding="utf-8",
        )
        results = discover_tools(tmp_path)
        assert len(results) == 1
        assert results[0]["name"] == "my_tool"

    def test_discover_tools_with_manifest(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_tools

        tool_dir = tmp_path / "tools" / "my_tool"
        tool_dir.mkdir(parents=True)
        (tool_dir / "tool.py").write_text("def register(r): pass\n", encoding="utf-8")
        (tool_dir / "manifest.json").write_text(
            json.dumps({"description": "My tool"}),
            encoding="utf-8",
        )
        results = discover_tools(tmp_path)
        assert results[0]["manifest"]["description"] == "My tool"

    def test_discover_tools_missing_py(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import discover_tools

        (tmp_path / "tools" / "broken").mkdir(parents=True)
        assert discover_tools(tmp_path) == []

    def test_load_plugin_tool(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import load_plugin_tool

        tool_dir = tmp_path / "my_tool"
        tool_dir.mkdir()
        (tool_dir / "tool.py").write_text(
            "def register(registry):\n    registry.registered = True\n",
            encoding="utf-8",
        )
        module = load_plugin_tool({"name": "my_tool", "path": tool_dir / "tool.py"})
        assert module is not None
        assert hasattr(module, "register")

    def test_load_plugin_tool_no_register(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import load_plugin_tool

        tool_dir = tmp_path / "bad_tool"
        tool_dir.mkdir()
        (tool_dir / "tool.py").write_text("x = 1\n", encoding="utf-8")
        module = load_plugin_tool({"name": "bad_tool", "path": tool_dir / "tool.py"})
        assert module is None

    def test_register_plugin_tools(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        from adt.core.plugin_loader import register_plugin_tools

        tool_dir = tmp_path / "tools" / "my_tool"
        tool_dir.mkdir(parents=True)
        (tool_dir / "tool.py").write_text(
            "def register(registry):\n    registry.plugin_loaded = True\n",
            encoding="utf-8",
        )
        registry = MagicMock()
        loaded = register_plugin_tools(registry, tmp_path)
        assert loaded == ["my_tool"]


class TestPluginValidation:
    def test_valid_skill_plugin(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import validate_plugin

        plugin_dir = tmp_path / "valid"
        plugin_dir.mkdir()
        (plugin_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
        assert validate_plugin(plugin_dir) == []

    def test_valid_tool_plugin(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import validate_plugin

        plugin_dir = tmp_path / "valid"
        plugin_dir.mkdir()
        (plugin_dir / "tool.py").write_text("def register(r): pass\n", encoding="utf-8")
        assert validate_plugin(plugin_dir) == []

    def test_invalid_empty_dir(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import validate_plugin

        plugin_dir = tmp_path / "empty"
        plugin_dir.mkdir()
        errors = validate_plugin(plugin_dir)
        assert len(errors) >= 1
        assert "SKILL.md" in errors[0] or "tool.py" in errors[0]

    def test_invalid_not_dir(self, tmp_path: Path) -> None:
        from adt.core.plugin_loader import validate_plugin

        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        errors = validate_plugin(f)
        assert "Not a directory" in errors[0]


class TestPluginsCLI:
    def test_plugins_list_empty(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("adt.core.plugin_loader.ensure_adt_dir", lambda: tmp_path)
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "No plugins" in result.stdout

    def test_plugins_validate_valid(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "valid"
        plugin_dir.mkdir()
        (plugin_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
        result = runner.invoke(app, ["plugins", "validate", str(plugin_dir)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_plugins_validate_invalid(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "empty"
        plugin_dir.mkdir()
        result = runner.invoke(app, ["plugins", "validate", str(plugin_dir)])
        assert result.exit_code == 1
