# Quick Start

## Ask a question about your code

```bash
adt ask "What does this project do?" --repo .
```

## Use supervised learning mode

```bash
adt ask "Implement binary search" --mode supervised --level beginner
```

## Review a file

```bash
adt review src/main.py --level intermediate
```

## View learning stats

```bash
adt stats
adt stats --export json
adt stats --export md --out report.md
```

## Run the HTTP API

```bash
pip install "agentic-dev-tool[api]"
adt serve --port 8765
# Open http://127.0.0.1:8765/docs
```

## Configuration

```bash
adt config show
adt config set default_model gpt-4o
adt config set log_level DEBUG
```

## Quick reference

```bash
adt guide
```
