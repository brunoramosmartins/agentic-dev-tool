# CLI Reference

## Global commands

| Command | Description |
|---------|-------------|
| `adt ask <query>` | Ask a question — supervisor picks an agent |
| `adt review <file>` | Review a source file in supervised mode |
| `adt stats` | Summarize learning progress |
| `adt guide` | Print quick-reference cheat sheet |
| `adt version` | Print installed version |
| `adt info` | Print project status summary |
| `adt serve` | Run the HTTP API server |

## `adt ask` options

| Flag | Description |
|------|-------------|
| `--repo, -r` | Local directory or owner/repo slug (repeatable) |
| `--agent, -a` | Force a specific agent |
| `--mode` | `execution` (default) or `supervised` |
| `--level` | `beginner`, `intermediate`, `advanced` |
| `--session` | Named session for supervised mode |
| `--resume` | Resume an interrupted run by trace ID |
| `--trace` | Show request trace |
| `--model, -m` | Override OpenAI model |
| `--token` | GitHub PAT |
| `--no-cache` | Disable repo tree cache |
| `--verbose, -v` | Debug logs and token usage |
| `--log-level` | File log level |

## `adt review` options

| Flag | Description |
|------|-------------|
| `--context, -c` | Description of what the code should do |
| `--level` | Difficulty level |
| `--model, -m` | Override OpenAI model |
| `--max-bytes` | Maximum file size override |
| `--session` | Named session |

## `adt stats` options

| Flag | Description |
|------|-------------|
| `--last` | Aggregate only N most recent sessions |
| `--export` | Export format: `csv`, `json`, or `md` |
| `--out` | Write export to file |
| `--html` | Generate HTML dashboard |
| `--classifier` | `keyword` (default) or `embedding` |

## Subcommands

### `adt config`

| Command | Description |
|---------|-------------|
| `adt config show` | Print effective settings |
| `adt config set <key> <value>` | Persist one config key |
| `adt config path` | Print config file path |

### `adt session`

| Command | Description |
|---------|-------------|
| `adt session show` | Show current session |
| `adt session list` | List all sessions |
| `adt session clear` | Delete a session |
| `adt session export` | Export session JSON |

### `adt runs`

| Command | Description |
|---------|-------------|
| `adt runs list` | List saved run snapshots |
| `adt runs show <id>` | Show run details |
| `adt runs delete <id>` | Delete a snapshot |

### `adt plugins`

| Command | Description |
|---------|-------------|
| `adt plugins list` | List installed plugins |
| `adt plugins validate <path>` | Validate a plugin directory |
