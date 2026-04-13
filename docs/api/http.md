# HTTP API Reference

Start the server:

```bash
pip install "agentic-dev-tool[api]"
adt serve --port 8765
```

OpenAPI docs: `http://127.0.0.1:8765/docs`

## Endpoints

### `GET /healthz`

Liveness probe.

```json
{"status": "ok", "version": "1.2.0"}
```

### `POST /ask`

Run one agent turn.

**Request:**

```json
{
  "query": "What does this project do?",
  "repo": ["."],
  "mode": "execution",
  "level": "intermediate",
  "trace": false,
  "session": "default"
}
```

**Response:**

```json
{
  "answer": "This project is...",
  "routed_agent": "repo_agent",
  "tools_used": ["read_repo_tree"],
  "context_summary": "...",
  "token_usage": {"prompt_tokens": 500, "completion_tokens": 200},
  "supervised_response": null,
  "trace_events": null
}
```

### `POST /review`

Review source code.

**Request:**

```json
{
  "file_content": "def foo(): pass",
  "context": "should return 1",
  "level": "beginner"
}
```

**Response:**

```json
{
  "feedback": {
    "issues": [],
    "improvements": [],
    "strengths": [],
    "next_step": "...",
    "overall_assessment": "on_track"
  },
  "raw_answer": "...",
  "session": {"problem_summary": "", "current_step": 0}
}
```

### `GET /stats?last=N`

Aggregated learning statistics.

### `GET /sessions`

List named session names.

### `GET /sessions/{name}`

Return a session's state.

### `DELETE /sessions/{name}`

Delete a named session (404 if missing).
