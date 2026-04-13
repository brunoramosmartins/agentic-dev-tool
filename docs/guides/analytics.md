# Learning Analytics

`adt` records supervised learning events and code reviews to
`~/.adt/logs/learning.jsonl`. The `adt stats` command aggregates
these into actionable metrics.

## View stats

```bash
adt stats
adt stats --last 5       # most recent 5 sessions only
```

## Export formats

```bash
adt stats --export json                  # stdout
adt stats --export csv --out stats.csv   # file
adt stats --export md --out report.md    # markdown
adt stats --html ./report                # HTML dashboard
```

## Metrics

| Metric | Description |
|--------|-------------|
| Sessions | Distinct supervised problems |
| Reviews | Code review events |
| Avg steps/session | Mean highest step index per session |
| Common issues | Top issue categories (off_by_one, naming, etc.) |
| Improvement trend | Rolling average iterations across session buckets |
| Assessments | Count of each review verdict |

## Classifier

By default, issues are classified via keyword matching. Use the
embedding classifier for better accuracy:

```bash
adt stats --classifier embedding
```

## HTTP API

```
GET /stats?last=5
```
