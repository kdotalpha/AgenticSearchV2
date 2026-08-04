"""Summarize fetched report rows so chart selection can account for the real data shape.

The interpreter's first pass picks charts from the wording of the question alone, before any
data exists. That is how a "use case vs resource" heatmap gets chosen for an account with a
single use case, or a spend chart gets built over dimension members whose spend is all zero.
This module renders the facts that decide those calls — dimension cardinality and which
members actually carry each metric — compactly enough to hand back to the model.
"""

# Value columns across all six reports. Everything else is a pivot dimension, including
# numeric-looking ones like "Hour" and "Response Code".
METRIC_COLUMNS = ("Spend", "Units", "Requests", "Instances", "Request: Latency")

# Above this, listing individual values is noise — report 3 carries thousands of instance IDs.
MAX_LISTED_VALUES = 25

# Time dimensions are summarized as a span; enumerating every timestamp tells the model
# nothing it needs to pick a chart type.
TIME_DIMENSIONS = ("Day", "Month", "Hour")


def _to_float(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _fmt(val: float) -> str:
    if val == int(val) and abs(val) < 1e15:
        return str(int(val))
    return f"{val:.2f}"


def build_data_profile(report_data: dict, from_date: str, to_date: str) -> str:
    """Render a text profile of the fetched reports for the chart-selection prompt."""
    blocks = []
    for report_id in sorted(report_data):
        rows = report_data[report_id]
        lines = [f"Report {report_id} - {len(rows)} rows, {from_date}..{to_date}"]

        if not rows:
            lines.append("  (no rows returned for this range - do not chart this report)")
            blocks.append("\n".join(lines))
            continue

        columns = list(rows[0].keys())
        metrics = [c for c in columns if c in METRIC_COLUMNS]
        dimensions = [c for c in columns if c not in METRIC_COLUMNS]

        for dim in dimensions:
            values = {row.get(dim, "") for row in rows}
            line = f"  {dim}: {len(values)} distinct"

            # Which members actually carry each metric — the fact that decides whether a
            # chart of that metric over this dimension will have anything to show.
            nonzero_notes = []
            for metric in metrics:
                totals = {}
                for row in rows:
                    key = row.get(dim, "")
                    totals[key] = totals.get(key, 0.0) + abs(_to_float(row.get(metric)))
                nonzero = sum(1 for v in totals.values() if v)
                if nonzero != len(values):
                    nonzero_notes.append(f"{nonzero} with nonzero {metric}")
            if nonzero_notes:
                line += " -> " + ", ".join(nonzero_notes)

            if dim in TIME_DIMENSIONS:
                ordered = sorted(values)
                line += f", spanning {ordered[0][:10]}..{ordered[-1][:10]}"
            elif len(values) <= MAX_LISTED_VALUES:
                listed = ", ".join(repr(v) for v in sorted(values))
                line += f"\n    values: [{listed}]"
            else:
                line += " (too many to list; high-cardinality)"
            lines.append(line)

        totals_parts = []
        for metric in metrics:
            total = sum(_to_float(row.get(metric)) for row in rows)
            totals_parts.append(f"{metric} {_fmt(total)}")
        if totals_parts:
            lines.append("  Metric totals: " + ", ".join(totals_parts))

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks) if blocks else "(no reports fetched)"
