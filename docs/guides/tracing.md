# Request Tracing

Pass `--trace` to see the full request lifecycle: routing decisions,
context building, LLM calls, tool invocations, and cost estimates.

```bash
adt ask "Explain the MCP layer" --repo . --trace
```

The trace output shows:

- **Routing** — which agent was selected and why
- **Context** — token budget allocation across system, user, tools, response
- **LLM calls** — iteration count, token usage per call
- **Tool calls** — name, duration, success/failure
- **Cost estimate** — based on model pricing and total tokens

## HTTP API

```bash
curl -X POST http://localhost:8765/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "explain tracing", "trace": true}'
```

The response includes a `trace_events` array when `trace: true`.
