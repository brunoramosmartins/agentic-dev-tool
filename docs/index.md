# Agentic Dev Tool (`adt`)

**Portfolio-grade CLI** and optional **HTTP API** that routes natural-language
questions to **specialized agents** — repository analysis, GitHub project
context, and technical research — backed by **OpenAI tool calling** and an
**MCP-style** in-process layer.

## Features

- **Multi-agent routing** — supervisor picks the best agent for your question
- **Supervised learning mode** — step-by-step teaching with difficulty levels
- **Code review** — structured feedback with severity, hints, and verdicts
- **Request tracing** — full visibility into routing, tools, and cost estimates
- **Learning analytics** — track your progress with `adt stats`
- **Plugin system** — extend with community skills and tools
- **HTTP API** — same capabilities as the CLI via FastAPI

## Quick Start

```bash
pip install agentic-dev-tool
export OPENAI_API_KEY="sk-..."
adt ask "What does this project do?" --repo .
```

See the [Installation](getting-started/install.md) and
[Quick Start](getting-started/quickstart.md) guides for details.
