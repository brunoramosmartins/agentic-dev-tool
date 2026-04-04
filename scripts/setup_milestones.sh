#!/usr/bin/env bash
# ==============================================================================
# setup_milestones.sh — Create GitHub milestones for the Agentic Dev Tool project
#
# Usage:
#   chmod +x scripts/setup_milestones.sh
#   ./scripts/setup_milestones.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Run from the repository root directory
#
# This script is idempotent: existing milestones with the same title are skipped.
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository. Are you in a git repo with a GitHub remote?"
    exit 1
fi

echo "==> Setting up milestones for repository: $REPO"
echo ""

# ------------------------------------------------------------------------------
# Helper function
# ------------------------------------------------------------------------------

create_milestone_if_not_exists() {
    local title="$1"
    local description="$2"

    # Check if milestone already exists
    if gh api "repos/$REPO/milestones" --paginate --jq '.[].title' 2>/dev/null | grep -qxF "$title"; then
        echo "  Skipping (already exists): $title"
    else
        echo "  Creating milestone: $title"
        gh api "repos/$REPO/milestones" \
            --method POST \
            -f title="$title" \
            -f description="$description" \
            -f state="open" \
            --silent 2>/dev/null
    fi
}

# ------------------------------------------------------------------------------
# Create milestones (one per phase)
# ------------------------------------------------------------------------------

echo "==> Creating phase milestones..."
echo ""

create_milestone_if_not_exists \
    "Phase 0 — Project Bootstrap" \
    "Set up repository, development environment, CI/CD, and all GitHub infrastructure. No application code — only project foundation."

create_milestone_if_not_exists \
    "Phase 1 — Core Infrastructure" \
    "Build foundational components: Pydantic schemas, LLM client, MCP layer (context builder, tool registry, execution controller), supervisor, and runner orchestrator."

create_milestone_if_not_exists \
    "Phase 2 — MVP: Repo Agent" \
    "Deliver the first usable feature: a CLI command that analyzes local repositories and answers questions about structure and code."

create_milestone_if_not_exists \
    "Phase 3 — Research Agent" \
    "Add technical research capabilities: search arXiv for papers, fetch and summarize articles from URLs."

create_milestone_if_not_exists \
    "Phase 4 — Project Agent" \
    "Add project management capabilities: read GitHub issues, milestones, and markdown docs to provide roadmap summaries."

create_milestone_if_not_exists \
    "Phase 5 — MCP Hardening" \
    "Improve MCP layer quality: context ranking, accurate token budgeting with tiktoken, structured JSON logging, and file-based context caching."

create_milestone_if_not_exists \
    "Phase 6 — Advanced Features" \
    "Add differentiating features: multi-repo support, diff-aware comparison, LLM-based supervisor routing, and configuration file support."

create_milestone_if_not_exists \
    "Phase 7 — Production Release" \
    "Package for PyPI, create FastAPI server, finalize documentation, and publish v1.0.0 portfolio release."

echo ""
echo "==> Milestones setup complete!"
echo ""
echo "Verify at: https://github.com/$REPO/milestones"
