#!/usr/bin/env bash
# ==============================================================================
# setup_extension.sh — Run all extension setup scripts (Phases 8–9)
#
# Usage:
#   chmod +x scripts/setup_extension.sh
#   ./scripts/setup_extension.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Original roadmap setup already executed (Phases 0–7)
#   - Phase 8 milestone and issues (#47–#52) already exist
#   - Run from the repository root directory
#
# This script creates:
#   1. Extension labels (phase-8, phase-9) — if missing
#   2. Phase 9 milestone
#   3. All Phase 9 issues (12 issues)
#
# Phase 8 is NOT recreated — it already exists with issues #47–#52.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "  Agentic Dev Tool — Extension Setup (Phases 8–9)"
echo "============================================================"
echo ""

# Check prerequisites
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) is not installed."
    echo "Install it: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "ERROR: GitHub CLI is not authenticated."
    echo "Run: gh auth login"
    exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)
if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository."
    echo "Make sure you are in a git repo with a GitHub remote."
    exit 1
fi

echo "Repository: $REPO"
echo ""

# Verify Phase 8 milestone exists
if gh api "repos/$REPO/milestones" --paginate --jq '.[].title' 2>/dev/null | grep -qxF "Phase 8 — Agent Observability & Tracing"; then
    echo "✓ Phase 8 milestone found (already exists)"
else
    echo "⚠ Phase 8 milestone not found. Create it manually or check your setup."
fi
echo ""

# Step 1: Labels
echo "============================================================"
echo "  Step 1/3: Setting up extension labels"
echo "============================================================"
bash "$SCRIPT_DIR/setup_labels_ext.sh"
echo ""

# Step 2: Milestones
echo "============================================================"
echo "  Step 2/3: Setting up Phase 9 milestone"
echo "============================================================"
bash "$SCRIPT_DIR/setup_milestones_ext.sh"
echo ""

# Step 3: Issues
echo "============================================================"
echo "  Step 3/3: Setting up Phase 9 issues"
echo "============================================================"
bash "$SCRIPT_DIR/setup_issues_ext.sh"
echo ""

# Summary
echo "============================================================"
echo "  Extension setup complete!"
echo "============================================================"
echo ""
echo "  Phase 8 (existing):  6 issues (#47–#52)"
echo "  Phase 9 (new):      12 issues"
echo ""
echo "  Labels:     https://github.com/$REPO/labels"
echo "  Milestones: https://github.com/$REPO/milestones"
echo "  Issues:     https://github.com/$REPO/issues"
echo ""
echo "  Next step: Complete Phase 8 issues, then start Phase 9!"
echo "============================================================"
