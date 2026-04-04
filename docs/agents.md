# Agents

This document summarizes built-in agents, their tools, and how routing works.

## Supervisor routing

The supervisor inspects the user query (lowercased) with simple substring rules, in order:

1. **Project** — keywords such as `issue`, `milestone`, `roadmap`, `project`, `sprint`, `backlog` → `project_agent` (stub until Phase 4).
2. **Research** — keywords such as `paper`, `papers`, `arxiv`, `article`, `research`, `literature`, `survey`, `publication`, `journal`, `preprint`, `doi`, and the phrase `literature review` → `research_agent`.
3. **Repository** — keywords such as `repo`, `code`, `codebase`, `architecture`, `explain`, `file`, `function`, `implementation`, and **`search`** → `repo_agent`. Including `search` under the repo bucket avoids sending generic “search the codebase” questions to the research agent.
4. **Default** — if nothing matches, the query is handled by **`repo_agent`**.

You can bypass routing with:

```bash
adt ask "your question" --repo . --agent research_agent
```

Valid values: `repo_agent`, `research_agent`, `project_agent`.

## `repo_agent`

**Purpose:** Understand a local checkout (layout, files, symbols).

**Tools:**

- `read_repo_tree` — directory tree respecting `.gitignore`.
- `read_file` — bounded read of a text file.
- `search_code` — regex search across text files.

**Context:** The runner attaches repository-derived context for this agent (unless you force another agent).

## `research_agent`

**Purpose:** Discover academic papers and read public web articles to support technical study.

**Tools:**

- `search_papers` — queries the public **arXiv Atom API** (`http://export.arxiv.org/api/query`) with `search_query=all:{query}` and returns titles, authors, abstract snippets, and abstract URLs. No API key is required. Results are clamped to at most 50 items per call; the CLI uses a descriptive `User-Agent` string.
- `fetch_article` — downloads an `http` or `https` URL with `httpx`, enforces a response size cap, and extracts visible text from HTML (scripts/styles skipped) or returns plain text bodies. **Local and non-global hosts are rejected** (basic SSRF mitigation).

**Context:** The runner does **not** load the repository tree for `research_agent`, even if `--repo` is set, so prompts stay focused on external sources. Use `--agent repo_agent` (or a repo-oriented question) when you need both codebase and papers in one session.

## `project_agent`

**Purpose:** Placeholder for GitHub-centric workflows (Phase 4+). No tools yet.
