"""Aggregate :class:`LearningEvent` streams into a :class:`LearningStats`."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from adt.analytics.events import LearningEvent


@dataclass(frozen=True)
class LearningStats:
    """Summary metrics computed from a list of learning events.

    Attributes:
        sessions: Number of distinct supervised problems encountered.
        reviews: Number of code review events recorded.
        supervised_steps: Number of supervised step-guidance events.
        avg_steps_per_session: Mean of each session's highest step index.
        avg_iterations_per_step: Mean iterations observed per session.
        common_issues: List of ``(category, count)`` tuples ordered by
            descending frequency. Categories come from
            :func:`~adt.analytics.events.categorize_issue`.
        improvement_trend: Rolling average iterations-per-session, split
            into at most three equal buckets (earliest → latest). Empty
            when there are fewer than three events.
        total_tokens: Sum of ``prompt_tokens`` + ``completion_tokens``
            extracted from each event's ``data`` dict. ``0`` when events
            did not carry token counts.
        assessments: Count of each ``assessment`` value across reviews.
    """

    sessions: int = 0
    reviews: int = 0
    supervised_steps: int = 0
    avg_steps_per_session: float = 0.0
    avg_iterations_per_step: float = 0.0
    common_issues: list[tuple[str, int]] = field(default_factory=list)
    improvement_trend: list[float] = field(default_factory=list)
    total_tokens: int = 0
    assessments: dict[str, int] = field(default_factory=dict)


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _session_key(event: LearningEvent) -> str:
    key = (event.problem_summary or "").strip().lower()
    if key:
        return key
    if event.session_name:
        return f"session:{event.session_name}"
    return f"trace:{event.trace_id or 'unknown'}"


def compute_stats(
    events: list[LearningEvent],
    *,
    last_n: int | None = None,
    classifier: str = "keyword",
) -> LearningStats:
    """Derive :class:`LearningStats` from a list of events.

    Args:
        events: Events in chronological order (oldest first).
        last_n: When set and positive, only consider the last ``last_n``
            sessions (grouped by ``problem_summary``). Sessions are
            identified in the order their first event appears.

    Returns:
        A frozen :class:`LearningStats` dataclass ready for rendering.
    """
    if not events:
        return LearningStats()

    # Group into sessions in first-seen order so ``last_n`` is meaningful.
    session_order: list[str] = []
    session_events: dict[str, list[LearningEvent]] = {}
    for ev in events:
        key = _session_key(ev)
        if key not in session_events:
            session_order.append(key)
            session_events[key] = []
        session_events[key].append(ev)

    if last_n is not None and last_n > 0:
        selected_keys = session_order[-last_n:]
    else:
        selected_keys = session_order
    selected_events: list[LearningEvent] = [
        ev for key in selected_keys for ev in session_events[key]
    ]

    sessions = len(selected_keys)
    reviews = sum(1 for ev in selected_events if ev.event_type == "code_review")
    supervised_steps = sum(
        1 for ev in selected_events if ev.event_type == "supervised_step"
    )

    # Steps per session = highest step_id observed per session.
    per_session_steps: list[float] = []
    per_session_iterations: list[float] = []
    for key in selected_keys:
        evs = session_events[key]
        max_step = max((ev.step_id for ev in evs), default=0)
        max_iter = max((ev.iteration_count for ev in evs), default=0)
        if max_step:
            per_session_steps.append(float(max_step))
        if max_iter:
            per_session_iterations.append(float(max_iter))

    # Common issues: flatten error_types from every event.
    counter: Counter[str] = Counter()
    for ev in selected_events:
        counter.update(ev.error_types)
    common_issues = counter.most_common(5)

    # Improvement trend: bucket iterations_per_session into up to 3 slices.
    trend: list[float] = []
    if len(per_session_iterations) >= 3:
        n = len(per_session_iterations)
        third = n // 3
        buckets = [
            per_session_iterations[:third],
            per_session_iterations[third : 2 * third],
            per_session_iterations[2 * third :],
        ]
        trend = [_round(_mean(b)) for b in buckets if b]

    assessments: dict[str, int] = {}
    for ev in selected_events:
        if ev.event_type != "code_review":
            continue
        assessments[ev.assessment] = assessments.get(ev.assessment, 0) + 1

    total_tokens = 0
    for ev in selected_events:
        data = ev.data or {}
        total_tokens += int(data.get("prompt_tokens", 0) or 0)
        total_tokens += int(data.get("completion_tokens", 0) or 0)

    return LearningStats(
        sessions=sessions,
        reviews=reviews,
        supervised_steps=supervised_steps,
        avg_steps_per_session=_round(_mean(per_session_steps)),
        avg_iterations_per_step=_round(_mean(per_session_iterations)),
        common_issues=common_issues,
        improvement_trend=trend,
        total_tokens=total_tokens,
        assessments=assessments,
    )
