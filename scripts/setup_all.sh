#!/usr/bin/env bash
# ==============================================================================
# setup_all.sh — Run all GitHub setup scripts in the correct order
#
# Usage:
#   chmod +x scripts/setup_all.sh
#   ./scripts/setup_all.sh
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated: gh auth login
#   - Run from the repository root directory
#   - Repository must exist on GitHub with a remote configured
#
# Order of execution:
#   1. Labels  — must exist before issues can reference them
#   2. Milestones — must exist before issues can be assigned to them
#   3. Issues — references labels and milestones
#
# All scripts are idempotent: safe to run multiple times.
#
# NOTE: If you already ran an older copy of these scripts from the repository
# root before they were consolidated under scripts/, you do not need to undo
# anything on GitHub—just run this file again; existing labels, milestones, and
# issues are detected and skipped.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "  Agentic Dev Tool — GitHub Setup"
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

# Step 1: Labels
echo "============================================================"
echo "  Step 1/3: Setting up labels"
echo "============================================================"
bash "$SCRIPT_DIR/setup_labels.sh"
echo ""

# Step 2: Milestones
echo "============================================================"
echo "  Step 2/3: Setting up milestones"
echo "============================================================"
bash "$SCRIPT_DIR/setup_milestones.sh"
echo ""

# Step 3: Issues
echo "============================================================"
echo "  Step 3/3: Setting up issues"
echo "============================================================"
bash "$SCRIPT_DIR/setup_issues.sh"
echo ""

# Summary
echo "============================================================"
echo "  Setup complete!"
echo "============================================================"
echo ""
echo "  Labels:     https://github.com/$REPO/labels"
echo "  Milestones: https://github.com/$REPO/milestones"
echo "  Issues:     https://github.com/$REPO/issues"
echo ""
echo "  Next: confirm CI on main, tag v0.1.0-bootstrap (Phase 0), start Phase 1."
echo "============================================================"
