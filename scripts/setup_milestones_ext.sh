#!/usr/bin/env bash
# ==============================================================================
# setup_milestones_ext.sh — Create Phase 9 milestone (Phase 8 already exists)
#
# Usage:
#   chmod +x scripts/setup_milestones_ext.sh
#   ./scripts/setup_milestones_ext.sh
#
# Idempotent: existing milestones are skipped.
# ==============================================================================

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository. Are you in a git repo with a GitHub remote?"
    exit 1
fi

echo "==> Setting up extension milestones for: $REPO"
echo ""

create_milestone_if_not_exists() {
    local title="$1"
    local description="$2"

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

create_milestone_if_not_exists \
    "Phase 9 — Supervised Mode" \
    "Introduce supervised learning mode: step-by-step teaching, code review feedback loop, skill integration, difficulty levels, and learning analytics. Transforms the tool from an execution assistant into a skill-building system."

echo ""
echo "==> Extension milestones setup complete!"
echo "Verify at: https://github.com/$REPO/milestones"
