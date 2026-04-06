#!/usr/bin/env bash
# ==============================================================================
# setup_labels_ext.sh — Add phase-8 and phase-9 labels if they don't exist
#
# Usage:
#   chmod +x scripts/setup_labels_ext.sh
#   ./scripts/setup_labels_ext.sh
#
# Idempotent: safe to run multiple times.
# ==============================================================================

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository. Are you in a git repo with a GitHub remote?"
    exit 1
fi

echo "==> Setting up extension labels for: $REPO"
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

# Phase labels (phase-8 may already exist)
create_or_update_label "phase-8" "C5DEF5" "Phase 8 — Agent Observability & Tracing"
create_or_update_label "phase-9" "C5DEF5" "Phase 9 — Supervised Mode"

echo ""
echo "==> Extension labels setup complete!"
echo "Verify at: https://github.com/$REPO/labels"
