"""Export :class:`LearningStats` to CSV, JSON, or Markdown."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict

from adt.analytics.stats import LearningStats


def export_json(stats: LearningStats) -> str:
    """Serialize stats to a JSON string."""
    data = asdict(stats)
    return json.dumps(data, indent=2, default=str)


def export_csv(stats: LearningStats) -> str:
    """Serialize stats as a wide-format CSV (one header row + one data row)."""
    data = asdict(stats)
    # Flatten complex fields into strings for CSV.
    flat: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, default=str)
        else:
            flat[key] = str(value)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(flat.keys()))
    writer.writeheader()
    writer.writerow(flat)
    return buf.getvalue()


def export_markdown(stats: LearningStats) -> str:
    """Render stats as a Markdown table."""
    lines: list[str] = ["# Learning Stats", ""]
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Sessions | {stats.sessions} |")
    lines.append(f"| Reviews | {stats.reviews} |")
    lines.append(f"| Supervised steps | {stats.supervised_steps} |")
    lines.append(f"| Avg steps/session | {stats.avg_steps_per_session} |")
    lines.append(f"| Avg iterations/session | {stats.avg_iterations_per_step} |")
    lines.append(f"| Total tokens | {stats.total_tokens:,} |")

    if stats.common_issues:
        lines.append("")
        lines.append("## Common Issues")
        lines.append("")
        for name, count in stats.common_issues:
            lines.append(f"- **{name}**: {count}")

    if stats.assessments:
        lines.append("")
        lines.append("## Review Verdicts")
        lines.append("")
        for name, count in sorted(stats.assessments.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {name}: {count}")

    if stats.improvement_trend:
        lines.append("")
        lines.append("## Improvement Trend")
        lines.append("")
        arrow = " → ".join(str(v) for v in stats.improvement_trend)
        lines.append(f"Iterations per session: {arrow}")

    lines.append("")
    return "\n".join(lines)
