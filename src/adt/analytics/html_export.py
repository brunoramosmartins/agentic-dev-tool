"""Render :class:`LearningStats` into a standalone HTML dashboard.

The generated HTML embeds a simple SVG sparkline for the improvement
trend and lays out all stats in a clean, printable single-page report.
No external CDN is required — everything is inline.
"""

from __future__ import annotations

from datetime import datetime, timezone

from jinja2 import Template

from adt.analytics.stats import LearningStats

_TEMPLATE = Template(
    """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>adt — Learning Stats Dashboard</title>
<style>
  :root { --bg: #f8f9fa; --card: #fff; --border: #dee2e6; --text: #212529;
          --dim: #6c757d; --accent: #0d6efd; --green: #198754;
          --yellow: #ffc107; --red: #dc3545; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif;
         background: var(--bg); color: var(--text); padding: 2rem; }
  h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
  .subtitle { color: var(--dim); margin-bottom: 1.5rem; font-size: 0.9rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem; margin-bottom: 2rem; }
  .card { background: var(--card); border: 1px solid var(--border);
          border-radius: 8px; padding: 1rem; }
  .card .label { font-size: 0.8rem; color: var(--dim); text-transform: uppercase; }
  .card .value { font-size: 1.8rem; font-weight: 700; margin-top: 0.25rem; }
  .section { margin-bottom: 2rem; }
  .section h2 { font-size: 1.1rem; margin-bottom: 0.75rem;
                 border-bottom: 1px solid var(--border); padding-bottom: 0.25rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.4rem 0.75rem;
           border-bottom: 1px solid var(--border); }
  th { font-size: 0.8rem; color: var(--dim); text-transform: uppercase; }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
           font-size: 0.8rem; font-weight: 600; }
  .badge-green { background: #d1e7dd; color: var(--green); }
  .badge-yellow { background: #fff3cd; color: #664d03; }
  .badge-red { background: #f8d7da; color: var(--red); }
  svg.sparkline { display: block; margin: 0.5rem 0; }
  footer { margin-top: 2rem; font-size: 0.75rem;
           color: var(--dim); text-align: center; }
</style>
</head>
<body>

<h1>Learning Stats Dashboard</h1>
<p class="subtitle">Generated {{ generated_at }}</p>

<div class="grid">
  <div class="card">
    <div class="label">Sessions</div>
    <div class="value">{{ stats.sessions }}</div>
  </div>
  <div class="card">
    <div class="label">Reviews</div>
    <div class="value">{{ stats.reviews }}</div>
  </div>
  <div class="card">
    <div class="label">Supervised Steps</div>
    <div class="value">{{ stats.supervised_steps }}</div>
  </div>
  <div class="card">
    <div class="label">Avg Steps/Session</div>
    <div class="value">{{ stats.avg_steps_per_session }}</div>
  </div>
  <div class="card">
    <div class="label">Avg Iterations/Session</div>
    <div class="value">{{ stats.avg_iterations_per_step }}</div>
  </div>
  <div class="card">
    <div class="label">Total Tokens</div>
    <div class="value">{{ "{:,}".format(stats.total_tokens) }}</div>
  </div>
</div>

{% if stats.common_issues %}
<div class="section">
  <h2>Common Issues</h2>
  <table>
    <thead><tr><th>Category</th><th>Count</th></tr></thead>
    <tbody>
    {% for name, count in stats.common_issues %}
      <tr><td>{{ name }}</td><td>{{ count }}</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

{% if stats.assessments %}
<div class="section">
  <h2>Review Verdicts</h2>
  <table>
    <thead><tr><th>Verdict</th><th>Count</th></tr></thead>
    <tbody>
    {% for name, count in assessments_sorted %}
      <tr>
        <td>
          {% if name == "excellent" %}
            <span class="badge badge-green">{{ name }}</span>
          {% elif name == "on_track" %}
            <span class="badge badge-yellow">{{ name }}</span>
          {% else %}
            <span class="badge badge-red">{{ name }}</span>
          {% endif %}
        </td>
        <td>{{ count }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

{% if sparkline_svg %}
<div class="section">
  <h2>Improvement Trend</h2>
  <p style="color: var(--dim); font-size: 0.85rem;">
    Iterations per session ({{ trend_labels }})
  </p>
  {{ sparkline_svg }}
</div>
{% endif %}

<footer>
  adt — Agentic Dev Tool &middot; Learning Analytics Dashboard
</footer>

</body>
</html>
"""
)


def _build_sparkline_svg(
    values: list[float],
    width: int = 300,
    height: int = 60,
) -> str:
    """Render a small SVG sparkline from a list of numeric values."""
    if not values or len(values) < 2:
        return ""
    min_v = min(values)
    max_v = max(values)
    span = max_v - min_v if max_v != min_v else 1.0
    padding = 4
    w = width - 2 * padding
    h = height - 2 * padding

    points: list[str] = []
    for i, v in enumerate(values):
        x = padding + (i / (len(values) - 1)) * w
        y = padding + h - ((v - min_v) / span) * h
        points.append(f"{x:.1f},{y:.1f}")

    polyline = " ".join(points)
    return (
        f'<svg class="sparkline" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polyline fill="none" stroke="#0d6efd" stroke-width="2" '
        f'points="{polyline}"/>'
        f"</svg>"
    )


def export_html(stats: LearningStats) -> str:
    """Render the stats dashboard as a standalone HTML string."""
    assessments_sorted = sorted(stats.assessments.items(), key=lambda kv: -kv[1])
    sparkline_svg = _build_sparkline_svg(stats.improvement_trend)
    trend_labels = " → ".join(str(v) for v in stats.improvement_trend)

    return _TEMPLATE.render(
        stats=stats,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        assessments_sorted=assessments_sorted,
        sparkline_svg=sparkline_svg,
        trend_labels=trend_labels,
    )
