# MCP layer specification

This project uses a **simplified Model Context Protocol (MCP)**-style layer: tools are **declarative** (name, JSON Schema parameters, handler) and **executed in-process** against a `ToolRegistry`. It is **not** a network MCP server by default.

## Concepts

- **ToolRegistry** — Maps unique tool names to `ToolDefinition` (description, `parameters` schema, `allowed_agents`, Python `handler`).
- **ExecutionController** — Validates tool call arguments with **jsonschema**, binds only parameters the handler accepts, runs the handler, returns `ToolResult` (text output, success flag).
- **OpenAI tool format** — `registry.to_openai_format(agent_name)` filters tools by `allowed_agents` and emits `{"type":"function","function":{...}}` blocks for the chat API.
- **ToolCall / ToolResult** — Pydantic models for assistant-proposed calls and normalized outcomes.

## Context packing (not MCP wire format)

Repository context is **plain text** embedded in the user message, not MCP resources:

- Delimited blocks: `[context:repo label=r0 path=…]`, `[tree]`, `[file:rel/path]`, closing tags for budget trimming.
- **Ranking** — Keyword overlap on paths, extension priority, smaller files preferred before packing.
- **Budgeting** — `tiktoken` counts; `allocate_budget` splits a logical window (system / context / tools schema / completion).
- **Cache** — Optional JSON cache files under `~/.adt/cache/` keyed by repo path and `git` HEAD, TTL configurable.

## Logging

Structured **JSON lines** append to `~/.adt/logs/adt.jsonl` (when file logging is configured): events such as `agent_selected`, `tool_called`, `request_completed`, `llm_failure`.

## Relation to “full” MCP

A full MCP deployment could expose the same tool set over stdio/WebSocket; this codebase optimizes for **CLI + optional HTTP** and **direct OpenAI tool calling** instead.
