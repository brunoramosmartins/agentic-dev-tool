#!/usr/bin/env bash
# ==============================================================================
# setup_issues_ext.sh — Create Phase 9 issues for the Supervised Mode
#
# Usage:
#   chmod +x scripts/setup_issues_ext.sh
#   ./scripts/setup_issues_ext.sh
#
# Prerequisites:
#   - Labels must exist (run setup_labels_ext.sh first)
#   - Phase 9 milestone must exist (run setup_milestones_ext.sh first)
#   - Run from the repository root directory
#
# Idempotent: issues with the same title are skipped.
# ==============================================================================

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null)

if [[ -z "$REPO" ]]; then
    echo "ERROR: Could not detect repository. Are you in a git repo with a GitHub remote?"
    exit 1
fi

echo "==> Setting up Phase 9 issues for: $REPO"
echo ""

create_issue_if_not_exists() {
    local title="$1"
    local body="$2"
    local labels="$3"
    local milestone="$4"

    if gh issue list --repo "$REPO" --state all --json title -q '.[].title' 2>/dev/null | grep -qxF "$title"; then
        echo "  Skipping (already exists): $title"
    else
        echo "  Creating issue: $title"
        gh issue create \
            --repo "$REPO" \
            --title "$title" \
            --body "$body" \
            --label "$labels" \
            --milestone "$milestone" \
            2>/dev/null
    fi
}

MILESTONE="Phase 9 — Supervised Mode"

# ==============================================================================
# PHASE 9.1 — Supervised Mode MVP
# ==============================================================================

echo "==> Creating Phase 9.1 issues (Supervised Mode MVP)..."
echo ""

create_issue_if_not_exists \
    "feat(models): add mode, level, and supervised response schemas" \
    "## Context

The supervised mode introduces new data structures: mode and level fields on
QueryRequest, a SupervisedStep model for step-by-step guidance, and a
SupervisedResponse model for structured output. These schemas must be defined
before any supervised functionality can be built.

## Tasks

- [ ] Extend \`QueryRequest\` with \`mode: Literal[\"execution\", \"supervised\"]\` and \`level: Literal[\"beginner\", \"intermediate\", \"advanced\"]\`
- [ ] Create \`SupervisedStep\` Pydantic model (step_number, goal, requirements, hints, questions)
- [ ] Create \`SupervisedResponse\` Pydantic model (problem_summary, current_step, total_steps, encouragement)
- [ ] Add field validators for mode and level values
- [ ] Add comprehensive docstrings to all new models
- [ ] Write unit tests for validation

## Definition of Done

- [ ] All models validate correctly with valid data
- [ ] Invalid mode/level values raise \`ValidationError\`
- [ ] \`SupervisedResponse\` serializes to clean JSON
- [ ] 100% test coverage on new models

## References

- Phase 9 in roadmap extension
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/)" \
    "feature,phase-9" \
    "$MILESTONE"

create_issue_if_not_exists \
    "feat(cli): add --mode flag for execution vs supervised mode" \
    "## Context

The \`--mode\` flag is the user-facing entry point to supervised mode. It extends
the existing \`adt ask\` command to support a teaching-oriented interaction model.

## Tasks

- [ ] Add \`--mode\` option to \`adt ask\` (choices: \`execution\`, \`supervised\`; default: \`execution\`)
- [ ] Validate allowed values with clear error messages
- [ ] Pass mode into \`QueryRequest\`
- [ ] Update \`--help\` text with supervised mode description
- [ ] Write unit tests for flag parsing

## Definition of Done

- [ ] \`adt ask \"query\" --mode supervised\` is accepted
- [ ] \`adt ask \"query\" --mode invalid\` shows clear error
- [ ] Help text explains both modes
- [ ] All tests pass

## References

- [Typer options docs](https://typer.tiangolo.com/tutorial/options/)" \
    "feature,phase-9" \
    "$MILESTONE"

create_issue_if_not_exists \
    "feat(core): implement ModeRouter for execution vs supervised dispatch" \
    "## Context

The ModeRouter sits between the CLI and the supervisor, selecting the correct
operational mode. Execution mode uses the existing supervisor; supervised mode
uses a new SupervisedSupervisor.

## Tasks

- [ ] Create \`src/adt/core/mode_router.py\`
- [ ] Implement \`ModeRouter\` class with \`route(request) -> str\`
- [ ] \`execution\` → existing Supervisor flow
- [ ] \`supervised\` → SupervisedSupervisor
- [ ] Default fallback to execution for unrecognized modes
- [ ] Add docstrings
- [ ] Write unit tests in \`tests/unit/test_mode_router.py\`

## Definition of Done

- [ ] Execution mode routes to existing supervisor
- [ ] Supervised mode routes to SupervisedSupervisor
- [ ] Unknown modes fall back to execution with warning
- [ ] All tests pass

## References

- Architecture Changes section in roadmap extension" \
    "feature,phase-9" \
    "$MILESTONE"

create_issue_if_not_exists \
    "feat(agent): implement SupervisedSupervisor with teaching prompt" \
    "## Context

The SupervisedSupervisor is the core of the teaching mode. It receives a problem,
decomposes it into steps, and returns structured guidance — never providing full
solutions. It uses a carefully crafted system prompt that enforces pedagogical
behavior.

## Tasks

- [ ] Create \`src/adt/agents/supervised_supervisor.py\`
- [ ] Implement \`SupervisedSupervisor\` class:
  - \`handle(request, context) -> SupervisedResponse\`
  - Bypass standard repo/project/research routing
  - Use teaching-oriented system prompt
  - Parse LLM response into \`SupervisedResponse\`
- [ ] Define supervised system prompt (see Agent System Prompt section in roadmap extension)
- [ ] Handle JSON parsing failures gracefully (fallback to text)
- [ ] Document the prompt in \`docs/agents.md\`
- [ ] Add comprehensive docstrings
- [ ] Write unit tests with mocked LLM responses

## Definition of Done

- [ ] SupervisedSupervisor decomposes problems into numbered steps
- [ ] Output is valid \`SupervisedResponse\` JSON
- [ ] No full solutions are generated
- [ ] Parsing failures degrade gracefully
- [ ] System prompt is documented in \`docs/agents.md\`
- [ ] All tests pass

## References

- Agent System Prompt: Supervised Mode in roadmap extension
- Behavioral Contract in Phase 9 description" \
    "feature,phase-9,priority:high" \
    "$MILESTONE"

create_issue_if_not_exists \
    "feat(core): wire supervised mode into Runner and CLI output" \
    "## Context

The Runner and CLI must be extended to handle the supervised flow: ModeRouter
dispatches to SupervisedSupervisor, and the CLI formats SupervisedResponse as
a Rich panel with step details, requirements, hints, and questions.

## Tasks

- [ ] Modify \`Runner.__init__()\` to accept a \`ModeRouter\`
- [ ] Modify \`Runner.run()\` to check \`request.mode\` and use appropriate supervisor
- [ ] Ensure Phase 8 tracing captures supervised interactions
- [ ] Create Rich panel layout for supervised responses:
  - Problem summary, step N of M, goal, requirements, hints, questions
  - Footer with \`adt review\` instruction
- [ ] Write integration test for complete supervised flow
- [ ] Write unit tests for Rich rendering

## Definition of Done

- [ ] \`adt ask \"implement binary search\" --mode supervised\` returns formatted guidance
- [ ] Rich panel is readable and well-structured
- [ ] Tracing captures supervised mode events
- [ ] Integration test passes with mocked LLM
- [ ] All tests pass

## References

- [Rich Panel docs](https://rich.readthedocs.io/en/latest/panel.html)
- Architecture Changes in roadmap extension" \
    "feature,phase-9" \
    "$MILESTONE"

# ==============================================================================
# PHASE 9.2 — Interactive Feedback Loop
# ==============================================================================

echo ""
echo "==> Creating Phase 9.2 issues (Interactive Feedback Loop)..."
echo ""

create_issue_if_not_exists \
    "feat(cli): implement adt review command for code feedback" \
    "## Context

The \`adt review\` command completes the learning feedback loop. Users implement
a step and submit their code for structured technical feedback, enabling an
iterative implement → review → refine cycle.

## Tasks

- [ ] Add \`adt review <file>\` subcommand to Typer app
- [ ] Arguments: \`file\` (required path), \`--context\` (optional description)
- [ ] Load file content, validate existence and readability
- [ ] Send to \`SupervisedSupervisor.review()\`
- [ ] Display structured feedback using Rich
- [ ] Add docstrings
- [ ] Write unit tests for command parsing and file loading

## Definition of Done

- [ ] \`adt review solution.py\` loads file and sends for review
- [ ] Missing file shows clear error message
- [ ] \`--context\` adds description to the review prompt
- [ ] All tests pass

## References

- Phase 9.2 in roadmap extension
- [Typer commands](https://typer.tiangolo.com/tutorial/commands/)" \
    "feature,phase-9" \
    "$MILESTONE"

create_issue_if_not_exists \
    "feat(agent): implement feedback engine with structured code review" \
    "## Context

The feedback engine analyzes user-submitted code and returns structured, specific,
technical feedback with line-level issues, severity ratings, improvement suggestions,
and strengths — creating actionable learning moments.

## Tasks

- [ ] Add \`review()\` method to \`SupervisedSupervisor\`
- [ ] Create \`CodeIssue\` Pydantic model (line, severity, description, fix_hint)
- [ ] Create \`ReviewFeedback\` Pydantic model (issues, improvements, strengths, next_step, overall_assessment)
- [ ] Create review-specific system prompt
- [ ] Parse LLM response into \`ReviewFeedback\`
- [ ] Handle parsing failures with graceful fallback
- [ ] Create Rich layout for review output (color-coded severity)
- [ ] Add docstrings
- [ ] Write unit tests with sample code inputs

## Definition of Done

- [ ] \`adt review file.py\` returns specific, actionable feedback
- [ ] Issues include line numbers and severity levels
- [ ] Output is color-coded: errors (red), warnings (yellow), suggestions (blue)
- [ ] Parsing failures degrade gracefully
- [ ] All tests pass

## References

- ReviewFeedback model in Phase 9.2 description" \
    "feature,phase-9,priority:high" \
    "$MILESTONE"

create_issue_if_not_exists \
    "feat(core): implement lightweight session context for supervised mode" \
    "## Context

Session context allows follow-up commands to build on previous interactions. In
supervised mode, this means tracking which step the user is on, what feedback was
given, and how many iterations have occurred — all in memory, no persistence.

## Tasks

- [ ] Create \`SessionContext\` class:
  - \`current_step\`, \`total_steps\`, \`problem_summary\`, \`previous_feedback\`, \`iteration_count\`
- [ ] Store in memory during CLI process lifetime
- [ ] Allow follow-up \`adt ask\` to reference current step
- [ ] Allow \`adt review\` to reference step expectations
- [ ] Clear session on new supervised query with different problem
- [ ] Write unit tests for session lifecycle

## Definition of Done

- [ ] Follow-up queries reference previous step context
- [ ] \`adt review\` knows what the current step expects
- [ ] New problems clear the session
- [ ] Session state is never persisted to disk
- [ ] All tests pass

## References

- Phase 9.2 description in roadmap extension" \
    "feature,phase-9" \
    "$MILESTONE"

# ==============================================================================
# PHASE 9.3 — Skill Integration
# ==============================================================================

echo ""
echo "==> Creating Phase 9.3 issues (Skill Integration)..."
echo ""

create_issue_if_not_exists \
    "feat(skill): create supervised engineering skill definition" \
    "## Context

A skill definition file encodes teaching heuristics, decomposition patterns, and
feedback guidelines as a standalone, versionable document. This makes the supervised
behavior reusable and independently extensible without code changes.

## Tasks

- [ ] Create \`src/adt/skills/supervised_engineering/SKILL.md\`
- [ ] Include sections: When to Use, When NOT to Use, Teaching Heuristics, Decomposition Patterns, Feedback Guidelines, Anti-Patterns
- [ ] Create skill loader utility that reads SKILL.md at runtime
- [ ] Integrate skill content injection into SupervisedSupervisor system prompt
- [ ] Write unit tests verifying skill content is present in prompts

## Definition of Done

- [ ] SKILL.md is comprehensive and follows the specification in the roadmap
- [ ] Skill content is injected into LLM prompts at runtime
- [ ] Skill file can be updated without changing code
- [ ] All tests pass

## References

- Phase 9.3 description in roadmap extension
- SKILL.md content specification in roadmap" \
    "feature,phase-9" \
    "$MILESTONE"

# ==============================================================================
# PHASE 9.4 — Difficulty Levels
# ==============================================================================

echo ""
echo "==> Creating Phase 9.4 issues (Difficulty Levels)..."
echo ""

create_issue_if_not_exists \
    "feat(mode): add difficulty levels to supervised mode" \
    "## Context

Different skill levels need different teaching intensity. A beginner needs more
hints and explanation; an advanced user needs challenging questions and critique.
Difficulty levels make the supervised mode adaptive and personalized.

## Tasks

- [ ] Add \`--level\` flag to CLI (beginner | intermediate | advanced; default: intermediate)
- [ ] Create \`LevelConfig\` Pydantic model (hints_per_step, questions_per_step, explanation_depth, feedback_focus)
- [ ] Define level-specific configurations as data constants
- [ ] Inject \`LevelConfig\` into supervised system prompt
- [ ] Apply conditioning to both guidance and review prompts
- [ ] Show level indicator in Rich output header
- [ ] Show warning if \`--level\` used without \`--mode supervised\`
- [ ] Write unit tests for all levels and flag interactions

## Definition of Done

- [ ] \`--level beginner\` gives detailed guidance with many hints
- [ ] \`--level advanced\` gives minimal hints with tough questions
- [ ] Behavioral difference is clear across all three levels
- [ ] Warning shown when \`--level\` used without \`--mode supervised\`
- [ ] All tests pass

## References

- LevelConfig specification in Phase 9.4 description
- Phase 9.4 in roadmap extension" \
    "feature,phase-9" \
    "$MILESTONE"

# ==============================================================================
# PHASE 9.5 — Learning Analytics (Optional)
# ==============================================================================

echo ""
echo "==> Creating Phase 9.5 issues (Learning Analytics)..."
echo ""

create_issue_if_not_exists \
    "feat(analytics): implement supervised learning analytics" \
    "## Context

Learning analytics track user patterns, common mistakes, and improvement trends.
This builds on Phase 8 tracing to create a separate learning log, enabling
reflection on learning progress and identification of recurring weaknesses.

## Tasks

- [ ] Create \`LearningEvent\` Pydantic model extending \`TraceEvent\` (step_id, iteration_count, assessment, error_types, completion_time_ms)
- [ ] Create separate log file: \`~/.adt/logs/learning.log\`
- [ ] Log all supervised interactions as \`LearningEvent\` entries
- [ ] Apply log rotation (10MB, 5 files)
- [ ] Add \`adt stats\` CLI subcommand:
  - Sessions count, avg steps, avg iterations
  - Common issues (categorized)
  - Improvement trend
  - Total cost
- [ ] Add \`--last N\` flag to limit analysis window
- [ ] Write unit tests

## Definition of Done

- [ ] Supervised sessions are logged as structured learning events
- [ ] Learning logs are separate from execution logs
- [ ] \`adt stats\` displays readable summary
- [ ] \`--last N\` filter works correctly
- [ ] All tests pass

## References

- Phase 9.5 description in roadmap extension
- Observability & Governance Extension section" \
    "feature,phase-9" \
    "$MILESTONE"

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo "========================================"
echo "==> Phase 9 issues setup complete!"
echo "========================================"
echo ""
echo "Verify at: https://github.com/$REPO/issues"
echo ""

TOTAL=$(gh issue list --repo "$REPO" --state all --json title -q 'length' 2>/dev/null || echo "?")
echo "Total issues in repository: $TOTAL"
