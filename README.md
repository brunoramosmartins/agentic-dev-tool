# Agentic Dev Tool (adt)

[![CI](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoramosmartins/agentic-dev-tool/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A context-oriented AI assistant CLI built with a simplified Model Context Protocol (MCP). The project is designed for extensibility, real-world engineering use, and professional demonstration.

## Status

**Phase 3 — Research Agent:** In addition to repository analysis, `adt ask` can route to a **research agent** that searches **arXiv** and fetches public **web articles** (HTML/text). Use natural phrasing (“papers on …”, “arxiv …”) or force routing with `--agent`. See [docs/agents.md](docs/agents.md) for routing rules and tool details.

## Installation

Requires **Python 3.10+**.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# optional: pre-commit install
```

Or with Make (Unix-like shell):

```bash
make install
```

## Configuration

Copy the example env file and set your OpenAI API key:

```bash
cp .env.example .env
# Edit .env: OPENAI_API_KEY=...
```

`adt` reads `OPENAI_API_KEY` from the process environment. Load `.env` with your shell or a tool such as [direnv](https://direnv.net/) if you use one.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes, for `ask` | OpenAI API key for chat completions. |
| `GITHUB_TOKEN` | No | Reserved for future GitHub-backed agents (see `.env.example`). |
| `ADT_LIVE_MODEL` | No | Optional model override for `pytest -m live` (default `gpt-4o-mini`). |

## Usage

### Ask about a repository

```bash
adt ask "What does this project do?" --repo .
```

### Ask about papers and articles (research agent)

The supervisor sends research-like questions to `research_agent`, which can call **arXiv** and **fetch** public URLs:

```bash
adt ask "Recent papers on retrieval augmented generation" --repo .
adt ask "Summarize https://example.com/article" --repo .
```

Research answers are rendered as **Rich Markdown** (cyan panel) so titles and links are easier to scan.

### Force a specific agent

Skip supervisor routing when you know which agent you want:

```bash
adt ask "Explain src layout" --repo . --agent repo_agent
adt ask "Find arxiv papers on graph neural networks" --repo . --agent research_agent
```

### Options

- `--repo`, `-r` — repository root (default: current directory; must exist). Used for repo tools and for `repo_agent` / `project_agent` context; `research_agent` ignores repo content in the prompt.
- `--agent`, `-a` — `repo_agent`, `research_agent`, or `project_agent`.
- `--verbose`, `-v` — debug logging, last token usage, and a truncated context summary.
- `--model`, `-m` — OpenAI model name (default: `gpt-4o-mini`).

Other commands:

```bash
adt --help
adt ask --help
adt version
adt info
```

### Example session (shape of output)

With a valid key you will see an **Agent:** line, then an **Answer** panel (green for repo-style answers, cyan Markdown for research), then **Tools used** (for example `read_repo_tree`, `search_papers`, `fetch_article`). With `--verbose`, extra debug lines follow.

## Development

```bash
make lint      # ruff check
make format    # ruff format
make test      # pytest with coverage (excludes live LLM tests by default)
make typecheck # mypy src/
```

Default pytest runs exclude tests marked `@pytest.mark.live` (real API calls). To exercise live OpenAI (and real arXiv) locally:

```bash
export OPENAI_API_KEY=...   # Windows PowerShell: $env:OPENAI_API_KEY="..."
pytest -m live
```

## GitHub automation (optional)

If you use the [GitHub CLI](https://cli.github.com/) (`gh`) and want to provision **labels**, **milestones**, and **issues** (Phases 0–7) in one go, run from the repository root (Git Bash, WSL, or macOS/Linux):

```bash
chmod +x scripts/*.sh
./scripts/setup_all.sh
```

- Scripts live only under `scripts/` and are **idempotent** (safe to re-run).
- To remove GitHub’s default labels before creating the project set, run `setup_labels.sh` with `ADT_DELETE_DEFAULT_LABELS=1` (optional; can affect existing issues).

## License

MIT — see [LICENSE](LICENSE).
