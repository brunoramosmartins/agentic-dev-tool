#!/usr/bin/env bash
# ==============================================================================
# setup_labels.sh — Create GitHub labels for the Agentic Dev Tool project
#
# Usage (from repository root):
#   chmod +x scripts/setup_labels.sh
#   ./scripts/setup_labels.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - A git repository with a GitHub remote (gh detects the target repo)
#
# Idempotent: creates missing labels and refreshes color/description for existing
# labels with the same name.
#
# Optional: remove GitHub’s stock labels before creating the project set (can
# break existing issues that still use those names). Opt in with:
#   ADT_DELETE_DEFAULT_LABELS=1 ./scripts/setup_labels.sh
# ==============================================================================

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository. Are you in a git repo with a GitHub remote?"
    exit 1
fi

echo "==> Setting up labels for repository: $REPO"
echo ""

create_or_update_label() {
    local name="$1"
    local color="$2"
    local description="$3"

    if gh label list --repo "$REPO" --json name -q '.[].name' | grep -qx "$name"; then
        echo "  Updating existing label: $name"
        gh label edit "$name" \
            --repo "$REPO" \
            --color "$color" \
            --description "$description" \
            2>/dev/null || true
    else
        echo "  Creating label: $name"
        gh label create "$name" \
            --repo "$REPO" \
            --color "$color" \
            --description "$description" \
            2>/dev/null || true
    fi
}

if [[ "${ADT_DELETE_DEFAULT_LABELS:-0}" == "1" ]]; then
    echo "==> Removing default GitHub labels (ADT_DELETE_DEFAULT_LABELS=1)..."
    DEFAULT_LABELS=(
        "bug"
        "documentation"
        "duplicate"
        "enhancement"
        "good first issue"
        "help wanted"
        "invalid"
        "question"
        "wontfix"
    )

    for label in "${DEFAULT_LABELS[@]}"; do
        if gh label list --repo "$REPO" --json name -q '.[].name' | grep -qx "$label"; then
            echo "  Deleting default label: $label"
            gh label delete "$label" --repo "$REPO" --yes 2>/dev/null || true
        fi
    done
    echo ""
else
    echo "==> Skipping removal of default GitHub labels (set ADT_DELETE_DEFAULT_LABELS=1 to enable)."
    echo ""
fi

echo "==> Creating project labels..."

create_or_update_label "feature" "0E8A16" "New feature or capability"
create_or_update_label "bug" "D73A4A" "Something is broken"
create_or_update_label "chore" "FBCA04" "Maintenance, tooling, dependencies"
create_or_update_label "docs" "0075CA" "Documentation improvements"
create_or_update_label "refactor" "E4E669" "Code restructuring without behavior change"
create_or_update_label "test" "BFD4F2" "Test additions or improvements"

echo ""
echo "==> Creating phase labels..."

create_or_update_label "phase-0" "C5DEF5" "Phase 0 — Project Bootstrap"
create_or_update_label "phase-1" "C5DEF5" "Phase 1 — Core Infrastructure"
create_or_update_label "phase-2" "C5DEF5" "Phase 2 — MVP: Repo Agent"
create_or_update_label "phase-3" "C5DEF5" "Phase 3 — Research Agent"
create_or_update_label "phase-4" "C5DEF5" "Phase 4 — Project Agent"
create_or_update_label "phase-5" "C5DEF5" "Phase 5 — MCP Hardening"
create_or_update_label "phase-6" "C5DEF5" "Phase 6 — Advanced Features"
create_or_update_label "phase-7" "C5DEF5" "Phase 7 — Production Release"

echo ""
echo "==> Creating priority and status labels..."

create_or_update_label "priority:high" "B60205" "Must be addressed before phase completion"
create_or_update_label "priority:low" "0E8A16" "Nice to have, can be deferred"
create_or_update_label "blocked" "D93F0B" "Blocked by another issue or external dependency"
create_or_update_label "good first issue" "7057FF" "Good for newcomers or contributors"
create_or_update_label "wontfix" "FFFFFF" "Will not be addressed"

echo ""
echo "==> Labels setup complete!"
echo ""
echo "Verify at: https://github.com/$REPO/labels"
