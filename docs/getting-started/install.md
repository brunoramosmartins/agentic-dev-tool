# Installation

## From PyPI

```bash
pip install agentic-dev-tool
```

## With API extras (FastAPI server)

```bash
pip install "agentic-dev-tool[api]"
```

## Development mode

```bash
git clone https://github.com/brunoramosmartins/agentic-dev-tool.git
cd agentic-dev-tool
pip install -e ".[dev]"
```

## Global install via pipx

```bash
pipx install agentic-dev-tool
```

Or from a local checkout (editable):

```bash
pipx install -e .
```

## Required environment

```bash
export OPENAI_API_KEY="sk-..."      # required
export GITHUB_TOKEN="ghp_..."       # optional, higher rate limits
```

!!! tip
    On Windows, use `setx` to persist environment variables:
    ```powershell
    [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-...", "User")
    ```
