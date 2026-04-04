# Agents

This document summarizes built-in agents, their tools, and how routing works.

## `--repo`: local path vs `owner/repo`

- **Existing directory:** used as the root for **repo tools** (`repo_agent`) and **markdown reads** (`project_agent`). `QueryRequest.repo_path` is that directory; no default GitHub slug is implied.
- **`owner/repo` slug** (only when that string is **not** an existing path): `repo_path` is set to the **current working directory** (markdown root), and `github_owner` / `github_repo` are filled for session hints. The runner defaults ambiguous queries to **`project_agent`** (see below).

## Supervisor routing

The supervisor inspects the user query (lowercased) with simple substring rules, in order:

1. **Project** — keywords such as `issue`, `issues`, `milestone`, `roadmap`, `project`, `sprint`, `backlog`, `github`, `epic`, `ticket`, `release`, `kanban`, `board`, `assignee`, `pull request`, `triaged` → `project_agent`.
2. **Research** — keywords such as `paper`, `papers`, `arxiv`, `article`, `research`, `literature`, `survey`, `publication`, `journal`, `preprint`, `doi`, and the phrase `literature review` → `research_agent`.
3. **Repository** — keywords such as `repo`, `code`, `codebase`, `architecture`, `explain`, `file`, `function`, `implementation`, and **`search`** → `repo_agent`.
4. **Default** — if nothing matches: **`project_agent`** when `github_owner` / `github_repo` are set (remote `--repo`); otherwise **`repo_agent`**.

You can bypass routing with:

```bash
adt ask "your question" --repo . --agent project_agent
```

Valid values: `repo_agent`, `research_agent`, `project_agent`.

## MCP context (Phase 5)

When the runner builds repository context for `repo_agent` (and related paths), it:

- **Ranks** candidate files by query keywords, extension priority, and size, then packs text until a **tiktoken** budget is reached (split: system 20%, context 50%, tools 10%, completion 20% of `ADT_TOKEN_BUDGET`, default 16384).
- **Caches** `read_repo_tree` results under `~/.adt/cache/` keyed by repo path and current `git` HEAD, with TTL `ADT_CACHE_TTL` (default 300s). Use CLI **`--no-cache`** to bypass.
- **Logs** structured JSON lines to `~/.adt/logs/adt.jsonl` with **`--log-level`** (`DEBUG` / `INFO` / `WARNING` / `ERROR`).

## `repo_agent`

**Purpose:** Understand a local checkout (layout, files, symbols).

**Tools:** `read_repo_tree`, `read_file`, `search_code`.

**Context:** Repository-derived context from `repo_path`.

## `research_agent`

**Purpose:** Discover academic papers and read public web articles.

**Tools:**

- `search_papers` — arXiv Atom API (`http://export.arxiv.org/api/query`).
- `fetch_article` — public HTTP(S) pages with basic SSRF blocking.

**Context:** Empty repository blob; external sources only.

## `project_agent`

**Purpose:** Roadmap and delivery status via **GitHub** and **local markdown**.

**Tools:**

- `read_issues` — `GET /repos/{owner}/{repo}/issues` (pull requests filtered out). Optional `state` (`open` / `closed` / `all`), `labels`, `max_results`.
- `read_milestones` — `GET /repos/{owner}/{repo}/milestones`.
- `read_markdown` — read `.md` / `.markdown` under the session markdown root; strips optional YAML front matter (`---` … `---`).

**GitHub authentication:** Handlers receive a token from the CLI (`--token`) or environment **`GITHUB_TOKEN`**. Without a token, expect about **60 requests/hour** per IP; **403** responses include rate-limit hints when GitHub provides headers.

**Context:** If a GitHub slug was passed on the CLI, the user message includes the default `owner/repo`. If only a local path was used, the runner adds repo tree context plus the markdown root path. Remote slug sessions skip the full tree (only short session hints) to avoid dumping unrelated `cwd` files.
