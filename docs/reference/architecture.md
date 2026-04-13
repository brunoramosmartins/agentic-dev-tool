# Architecture

This document summarizes how **agentic-dev-tool** (`adt`) is structured and why key choices were made. It complements the user-facing [README](../README.md) and the MCP-focused [mcp.md](mcp.md).

## High-level flow

1. **Input** — User question plus optional repo roots (`--repo`, repeatable), GitHub slug, or forced agent.
2. **Configuration** — Defaults from `~/.adt/config.toml` and `ADT_*` environment variables; CLI flags override where applicable.
3. **Routing** — `HybridSupervisor` tries a small **JSON LLM classification** (`LLMClient.complete_json_object`); on failure or when disabled, **keyword rules** (`Supervisor`) select `repo_agent`, `project_agent`, or `research_agent`.
4. **Context** — `ContextBuilder` assembles bounded text: ranked files, tree listings, **tiktoken** budgets, optional **disk cache** for trees (`~/.adt/cache`). Multi-repo sessions use **labeled blocks** (`r0`, `r1`, …).
5. **Execution** — `Runner` runs an OpenAI chat loop with **tools** from `ToolRegistry`; `ExecutionController` validates arguments (JSON Schema) and dispatches handlers.
6. **Output** — `AgentResponse` (answer, tools used, routed agent, context summary). The CLI prints a Rich panel; the optional **FastAPI** layer returns JSON.

Shared orchestration for CLI and HTTP lives in **`adt.ask_session.run_ask`**.

## Major components

| Module / area | Role |
|---------------|------|
| `adt.cli.app` | Typer entrypoint: `ask`, `config`, `serve`, `version`, `info`. |
| `adt.ask_session` | Single-turn `run_ask` used by CLI and API. |
| `adt.bootstrap` | Registers tools, builds `Runner`, wires `HybridSupervisor` + `LLMClient`. |
| `adt.core.runner` | Budget allocation, context assembly per agent, tool loop, optional **agent_chain**. |
| `adt.core.supervisor` | Deterministic keyword routing. |
| `adt.core.hybrid_supervisor` | LLM routing with fallback to `Supervisor`. |
| `adt.mcp.*` | Registry, executor, context builder, token budget, ranking, tree cache. |
| `adt.tools.*` | Repo, project (GitHub + markdown), research (arXiv + HTTP fetch), `compare_repos`. |
| `adt.api.server` | FastAPI: `/healthz`, `/ask` (optional extra `[api]`). |

## Design decisions

- **MCP-style, not a full MCP server** — Tools are described as JSON Schema and invoked in-process, which keeps deployment simple and avoids a long-running MCP host for the default CLI use case.
- **Single OpenAI client** — One `LLMClient` for both chat and routing; routing uses `response_format: json_object` for a tiny payload.
- **Multi-repo via explicit keys** — Session ids (`r0`, `r1`) avoid ambiguous path resolution and make `compare_repos` well-defined.
- **Config file + env** — `toml` for persistent preferences; `ADT_*` for CI and shells without editing files.
- **Optional API** — FastAPI and uvicorn are **not** core dependencies so `pip install agentic-dev-tool` stays lean for CLI-only users.

## Extension points

- **New tools** — Register `ToolDefinition` in `bootstrap.py` (or future plugin loading via `custom_tools` in config, reserved).
- **New agents** — Subclass `BaseAgent`, add to `Runner` agent map and routing (LLM + keyword lists).
- **Stricter API auth** — The stock server binds to `127.0.0.1` by default; add API keys or OAuth in front for public exposure.
