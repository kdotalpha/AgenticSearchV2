import statistics
from collections import defaultdict

from chart_registry import CHART_REGISTRY


def apply_filters(rows: list[dict], filters: list[dict]) -> list[dict]:
    if not filters:
        return rows

    filtered = rows
    for f in filters:
        field = f["field"]
        op = f["operator"]
        value = f["value"]
        filtered = [r for r in filtered if _match_filter(r.get(field, ""), op, value)]

    return filtered


def _match_filter(cell_value: str, operator: str, value) -> bool:
    if operator == "equals":
        return cell_value == str(value)
    elif operator == "not_equals":
        return cell_value != str(value)
    elif operator == "contains":
        return str(value).lower() in cell_value.lower()
    elif operator == "in":
        return cell_value in [str(v) for v in value]
    elif operator == "not_in":
        return cell_value not in [str(v) for v in value]
    elif operator in ("gt", "lt", "gte", "lte"):
        try:
            cell_num = float(cell_value)
            val_num = float(value)
        except (ValueError, TypeError):
            return False
        if operator == "gt":
            return cell_num > val_num
        elif operator == "lt":
            return cell_num < val_num
        elif operator == "gte":
            return cell_num >= val_num
        elif operator == "lte":
            return cell_num <= val_num
    return True


def _to_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# Axes whose continuity carries meaning: a day with no spend still belongs on the axis, so
# members of these fields are never suppressed even when their total is zero.
TIME_FIELDS = {"Day", "Month"}

# Legend entries beyond this are folded into a single "Other" member. Reports routinely carry
# dimensions with 20+ members, which renders as an unreadable legend of near-invisible slices.
MAX_SERIES = 12

OTHER_LABEL = "Other"

# Synthetic parent used when a two-dimensional chart is given only one dimension.
ALL_LABEL = "All"

# Highcharts keys a point's magnitude differently per series type: treemap sizes its tiles by
# "value" and wordcloud scales words by "weight". Emitting only "y" leaves those two with
# points that have no geometry, so they render blank without raising anything.
MAGNITUDE_KEYS = {"treemap": "value", "word_cloud": "weight"}


def _nonzero_keys(totals: dict) -> set:
    """Keys whose total is non-zero, or every key if nothing has a value.

    Suppression is always relative to the chart's own value_field: charting Spend drops
    dimension members with no spend, while charting Requests keeps them because they do
    have requests. Never suppress by member name.
    """
    nonzero = {k for k, v in totals.items() if v}
    return nonzero or set(totals)


def _keep_top(totals: dict, n: int = MAX_SERIES) -> tuple[list, bool]:
    """The top n keys by absolute total, plus whether anything was left over."""
    ranked = sorted(totals, key=lambda k: -abs(totals[k]))
    return ranked[:n], len(ranked) > n


def _readable_members(totals: dict, field: str, n: int = MAX_SERIES) -> tuple[list, set]:
    """Resolve which members of a dimension to chart.

    Returns the member names to render (sorted, with "Other" appended when a tail was
    dropped) and the set of members the "Other" bucket absorbs. A field in TIME_FIELDS keeps
    every member and never gets an "Other" bucket.
    """
    if field in TIME_FIELDS:
        return sorted(totals), set()

    kept = _nonzero_keys(totals)
    ranked = {k: totals[k] for k in kept}
    if len(ranked) <= n:
        return sorted(ranked), set()
    # n is the total number of legend entries, so the "Other" bucket takes one of the slots.
    top, _ = _keep_top(ranked, n - 1)
    return sorted(top) + [OTHER_LABEL], kept - set(top)


def _format_day(value: str) -> str:
    """Trim a Pay-i ISO timestamp to a readable date: 2026-07-17T00:00:00.0000000Z -> 2026-07-17."""
    if isinstance(value, str) and len(value) >= 10 and value[4] == "-" and "T" in value:
        return value[:10]
    return value


def _format_categories(categories: list, field: str) -> list:
    if field in TIME_FIELDS:
        return [_format_day(c) for c in categories]
    return categories


def build_highcharts_config(chart_spec: dict, rows: list[dict]) -> dict:
    chart_type = chart_spec["chart_type"]
    registry_entry = CHART_REGISTRY.get(chart_type)
    if not registry_entry:
        return _fallback_config(chart_spec, rows)

    transform_name = registry_entry["transform"]
    transform_fn = TRANSFORMS.get(transform_name)
    if not transform_fn:
        return _fallback_config(chart_spec, rows)

    series_data = transform_fn(chart_spec, rows)

    config = {
        "chart": {"type": registry_entry["highcharts_type"]},
        "title": {"text": chart_spec.get("title", "Chart")},
        "subtitle": {"text": chart_spec.get("description", "")},
        "credits": {"enabled": False},
    }

    if "chart_options" in registry_entry:
        config["chart"].update(registry_entry["chart_options"])

    if "plot_options" in registry_entry:
        config["plotOptions"] = registry_entry["plot_options"]

    config.update(series_data)

    if "series_options" in registry_entry:
        for s in config.get("series", []):
            s.update(registry_entry["series_options"])

    config["_modules"] = registry_entry.get("modules", [])

    return config


def build_time_series(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field", "")
    value_field = chart_spec.get("value_field", "Spend")
    series_field = chart_spec.get("series_field")
    aggregation = chart_spec.get("aggregation", "sum")

    if series_field:
        grouped = defaultdict(lambda: defaultdict(list))
        for row in rows:
            x_val = row.get(x_field, "")
            s_val = row.get(series_field, "")
            grouped[s_val][x_val].append(_to_float(row.get(value_field, "0")))

        # The x axis keeps every category it has — only the series list is narrowed, so a
        # day with no spend still appears on a daily chart.
        categories = sorted(set(row.get(x_field, "") for row in rows))
        totals = {
            s_name: sum(abs(v) for vals in x_data.values() for v in vals)
            for s_name, x_data in grouped.items()
        }
        members, bucketed = _readable_members(totals, series_field)

        series = []
        for s_name in members:
            if s_name == OTHER_LABEL:
                # Pool the raw values before aggregating so avg/min/max stay meaningful
                # for the bucket rather than being an aggregate of aggregates.
                pooled = defaultdict(list)
                for dropped in bucketed:
                    for cat, vals in grouped[dropped].items():
                        pooled[cat].extend(vals)
                x_data = pooled
            else:
                x_data = grouped[s_name]
            data = [_aggregate(x_data.get(cat, [0]), aggregation) for cat in categories]
            series.append({"name": s_name, "data": data})
    else:
        grouped = defaultdict(list)
        for row in rows:
            x_val = row.get(x_field, "")
            grouped[x_val].append(_to_float(row.get(value_field, "0")))

        categories = sorted(grouped.keys())
        data = [_aggregate(grouped[cat], aggregation) for cat in categories]
        series = [{"name": value_field, "data": data}]

    return {
        "xAxis": {"categories": _format_categories(categories, x_field), "title": {"text": x_field}},
        "yAxis": {"title": {"text": value_field}},
        "series": series,
    }


def build_pie_data(chart_spec: dict, rows: list[dict]) -> dict:
    category_field = chart_spec.get("x_field") or chart_spec.get("series_field", "")
    value_field = chart_spec.get("value_field", "Spend")

    grouped = defaultdict(float)
    for row in rows:
        cat = row.get(category_field, "Unknown")
        grouped[cat] += _to_float(row.get(value_field, "0"))

    # Zero slices are invisible but still consume a legend entry, and a long tail of tiny
    # slices is unreadable — keep the members that carry the metric and bucket the rest.
    members, bucketed = _readable_members(grouped, category_field)
    sliced = {name: grouped[name] for name in members if name != OTHER_LABEL}
    if bucketed:
        sliced[OTHER_LABEL] = sum(grouped[name] for name in bucketed)

    magnitude_key = MAGNITUDE_KEYS.get(chart_spec.get("chart_type", ""))
    data = []
    for name, val in sorted(sliced.items(), key=lambda x: -x[1]):
        if category_field in TIME_FIELDS:
            name = _format_day(name)
        point = {"name": name, "y": round(val, 4)}
        if magnitude_key:
            point[magnitude_key] = round(val, 4)
        data.append(point)

    return {
        "series": [{"name": value_field, "colorByPoint": True, "data": data}],
    }


def build_scatter_data(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field", "")
    y_field = chart_spec.get("y_field") or chart_spec.get("value_field", "")
    series_field = chart_spec.get("series_field")

    chart_type = chart_spec.get("chart_type", "scatter")
    is_bubble = chart_type == "bubble"
    z_field = chart_spec.get("value_field", "") if is_bubble and chart_spec.get("y_field") else None

    if series_field:
        grouped = defaultdict(list)
        for row in rows:
            x = _to_float(row.get(x_field, "0"))
            y = _to_float(row.get(y_field, "0"))
            point = {"x": x, "y": y}
            if is_bubble and z_field:
                point["z"] = _to_float(row.get(z_field, "0"))
            grouped[row.get(series_field, "")].append(point)

        series = [{"name": name, "data": points} for name, points in sorted(grouped.items())]
    else:
        data = []
        for row in rows:
            x = _to_float(row.get(x_field, "0"))
            y = _to_float(row.get(y_field, "0"))
            point = {"x": x, "y": y}
            if is_bubble and z_field:
                point["z"] = _to_float(row.get(z_field, "0"))
            data.append(point)
        series = [{"name": y_field, "data": data}]

    result = {
        "xAxis": {"title": {"text": x_field}},
        "yAxis": {"title": {"text": y_field}},
        "series": series,
    }

    if is_bubble:
        result["chart"] = {"type": "bubble", "zoomType": "xy"}

    return result


def build_heatmap_data(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field", "")
    y_field = chart_spec.get("series_field") or chart_spec.get("y_field", "")
    value_field = chart_spec.get("value_field", "Spend")

    # Sum by category name first, then narrow each axis. Reports routinely carry dimension
    # values with no spend at all (event-type resources, say); padding the grid with all-zero
    # bands renders them as blank cells at the bottom of the color axis, so the chart looks
    # empty even though the real cells are present. A time axis is exempt — dropping
    # zero-spend days would silently break the continuity of the axis.
    totals = defaultdict(float)
    for row in rows:
        key = (row.get(x_field, ""), row.get(y_field, ""))
        totals[key] += _to_float(row.get(value_field, "0"))

    x_totals = defaultdict(float)
    y_totals = defaultdict(float)
    for (x_val, y_val), val in totals.items():
        x_totals[x_val] += abs(val)
        y_totals[y_val] += abs(val)

    x_categories, x_bucketed = _readable_members(x_totals, x_field)
    y_categories, y_bucketed = _readable_members(y_totals, y_field)

    x_map = {v: i for i, v in enumerate(x_categories)}
    y_map = {v: i for i, v in enumerate(y_categories)}

    cells = defaultdict(float)
    for (x_val, y_val), val in totals.items():
        x_key = OTHER_LABEL if x_val in x_bucketed else x_val
        y_key = OTHER_LABEL if y_val in y_bucketed else y_val
        if x_key not in x_map or y_key not in y_map:
            continue
        cells[(x_map[x_key], y_map[y_key])] += val

    data = [[x_idx, y_idx, round(val, 4)] for (x_idx, y_idx), val in cells.items()]

    all_vals = [d[2] for d in data] or [0]

    return {
        "xAxis": {"categories": _format_categories(x_categories, x_field), "title": {"text": x_field}},
        "yAxis": {"categories": _format_categories(y_categories, y_field), "title": {"text": y_field}},
        "colorAxis": {"min": min(all_vals), "max": max(all_vals)},
        "series": [{"name": value_field, "data": data, "borderWidth": 1}],
    }


def build_boxplot_data(chart_spec: dict, rows: list[dict]) -> dict:
    category_field = chart_spec.get("x_field") or chart_spec.get("series_field", "")
    value_field = chart_spec.get("value_field", "Spend")

    grouped = defaultdict(list)
    for row in rows:
        cat = row.get(category_field, "Unknown")
        grouped[cat].append(_to_float(row.get(value_field, "0")))

    categories = sorted(grouped.keys())
    data = []
    for cat in categories:
        values = sorted(grouped[cat])
        if len(values) < 5:
            while len(values) < 5:
                values.append(values[-1] if values else 0)
        n = len(values)
        low = values[0]
        q1 = values[n // 4]
        median = values[n // 2]
        q3 = values[(3 * n) // 4]
        high = values[-1]
        data.append([round(low, 4), round(q1, 4), round(median, 4), round(q3, 4), round(high, 4)])

    return {
        "xAxis": {"categories": categories, "title": {"text": category_field}},
        "yAxis": {"title": {"text": value_field}},
        "series": [{"name": value_field, "data": data}],
    }


def build_histogram_data(chart_spec: dict, rows: list[dict]) -> dict:
    value_field = chart_spec.get("value_field", "Spend")
    values = [_to_float(row.get(value_field, "0")) for row in rows]

    return {
        "xAxis": [{"title": {"text": value_field}}, {"title": {"text": "Frequency"}, "opposite": True}],
        "yAxis": [{"title": {"text": "Count"}}, {"title": {"text": ""}, "opposite": True}],
        "series": [
            {"name": value_field, "type": "histogram", "baseSeries": "data", "zIndex": -1},
            {"name": "Data", "type": "scatter", "data": values, "id": "data", "visible": False},
        ],
    }


def build_hierarchy_data(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field", "")
    y_field = chart_spec.get("y_field") or chart_spec.get("series_field", "")
    value_field = chart_spec.get("value_field", "Spend")
    chart_type = chart_spec.get("chart_type", "sankey")

    # These charts need two dimensions. Given only one, group by it a single level deep
    # rather than emitting a bare root node, which renders as an empty chart.
    single_level = not y_field or y_field == x_field
    if single_level:
        y_field = x_field
        x_field = ""

    flow = defaultdict(float)
    for row in rows:
        from_node = row.get(x_field, ALL_LABEL) or ALL_LABEL
        to_node = row.get(y_field, "")
        if from_node and to_node:
            flow[(from_node, to_node)] += _to_float(row.get(value_field, "0"))

    # A zero-weight link draws no ribbon but still adds its node to the diagram, so a
    # dimension full of members without spend crowds the chart with dead nodes.
    to_totals = defaultdict(float)
    for (_, to_node), weight in flow.items():
        to_totals[to_node] += abs(weight)
    to_members, to_bucketed = _readable_members(to_totals, y_field)
    to_keep = set(to_members)

    bucketed_flow = defaultdict(float)
    for (from_node, to_node), weight in flow.items():
        key = OTHER_LABEL if to_node in to_bucketed else to_node
        if key not in to_keep:
            continue
        bucketed_flow[(from_node, key)] += weight
    flow = bucketed_flow

    if chart_type in ("sankey", "dependency_wheel"):
        data = [[f, t, round(w, 4)] for (f, t), w in sorted(flow.items(), key=lambda x: -x[1])]
        return {
            "series": [{
                "keys": ["from", "to", "weight"],
                "data": data,
            }],
        }
    else:
        # sunburst
        nodes = {}
        for (parent, child), weight in flow.items():
            if not single_level:
                if parent not in nodes:
                    nodes[parent] = {"id": parent, "name": parent, "value": 0}
                nodes[parent]["value"] += weight
            # With one dimension the members hang straight off the root; inserting the
            # synthetic parent would add a redundant ring wrapping the whole chart.
            child_id = child if single_level else f"{parent}-{child}"
            if child_id not in nodes:
                node = {"id": child_id, "name": child, "value": 0}
                if not single_level:
                    node["parent"] = parent
                nodes[child_id] = node
            nodes[child_id]["value"] += weight

        data = [{"id": "root", "name": ALL_LABEL}]
        for node in nodes.values():
            if "parent" not in node:
                node["parent"] = "root"
            node["value"] = round(node["value"], 4)
            data.append(node)

        return {
            "series": [{"data": data, "allowTraversingTree": True}],
        }


def build_polar_data(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field", "")
    value_field = chart_spec.get("value_field", "Spend")
    series_field = chart_spec.get("series_field")

    if series_field:
        grouped = defaultdict(lambda: defaultdict(float))
        for row in rows:
            cat = row.get(x_field, "")
            s = row.get(series_field, "")
            grouped[s][cat] += _to_float(row.get(value_field, "0"))

        categories = sorted(set(row.get(x_field, "") for row in rows))
        totals = {
            s_name: sum(abs(v) for v in cat_data.values())
            for s_name, cat_data in grouped.items()
        }
        members, bucketed = _readable_members(totals, series_field)

        series = []
        for s_name in members:
            if s_name == OTHER_LABEL:
                cat_data = defaultdict(float)
                for dropped in bucketed:
                    for c, v in grouped[dropped].items():
                        cat_data[c] += v
            else:
                cat_data = grouped[s_name]
            data = [round(cat_data.get(c, 0), 4) for c in categories]
            series.append({"name": s_name, "data": data, "pointPlacement": "on"})
    else:
        grouped = defaultdict(float)
        for row in rows:
            cat = row.get(x_field, "")
            grouped[cat] += _to_float(row.get(value_field, "0"))

        members, bucketed = _readable_members(grouped, x_field)
        categories = members
        data = [
            round(sum(grouped[d] for d in bucketed) if c == OTHER_LABEL else grouped[c], 4)
            for c in categories
        ]
        series = [{"name": value_field, "data": data, "pointPlacement": "on"}]

    return {
        "xAxis": {
            "categories": _format_categories(categories, x_field),
            "tickmarkPlacement": "on",
            "lineWidth": 0,
        },
        "yAxis": {
            "gridLineInterpolation": "polygon",
            "lineWidth": 0,
            "min": 0,
        },
        "series": series,
    }


def build_range_data(chart_spec: dict, rows: list[dict]) -> dict:
    category_field = chart_spec.get("x_field") or chart_spec.get("series_field", "")
    value_field = chart_spec.get("value_field", "Spend")

    grouped = defaultdict(list)
    for row in rows:
        cat = row.get(category_field, "Unknown")
        grouped[cat].append(_to_float(row.get(value_field, "0")))

    categories = sorted(grouped.keys())
    data = []
    for cat in categories:
        values = sorted(grouped[cat])
        low = values[0] if values else 0
        high = values[-1] if values else 0
        data.append([round(low, 4), round(high, 4)])

    return {
        "xAxis": {"categories": categories, "title": {"text": category_field}},
        "yAxis": {"title": {"text": value_field}},
        "series": [{"name": value_field, "data": data}],
    }


def build_waterfall_data(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field") or chart_spec.get("series_field", "")
    value_field = chart_spec.get("value_field", "Spend")

    grouped = defaultdict(float)
    for row in rows:
        cat = row.get(x_field, "Unknown")
        grouped[cat] += _to_float(row.get(value_field, "0"))

    sorted_items = sorted(grouped.items(), key=lambda x: -abs(x[1]))
    data = [{"name": name, "y": round(val, 4)} for name, val in sorted_items]
    data.append({"name": "Total", "isSum": True})

    return {
        "xAxis": {"type": "category"},
        "yAxis": {"title": {"text": value_field}},
        "series": [{"name": value_field, "data": data, "colorByPoint": True}],
    }


def build_pareto_data(chart_spec: dict, rows: list[dict]) -> dict:
    x_field = chart_spec.get("x_field") or chart_spec.get("series_field", "")
    value_field = chart_spec.get("value_field", "Spend")

    grouped = defaultdict(float)
    for row in rows:
        cat = row.get(x_field, "Unknown")
        grouped[cat] += _to_float(row.get(value_field, "0"))

    # A long tail of zero-valued categories flattens the cumulative-% line and pushes the
    # meaningful bars into the left margin.
    members, bucketed = _readable_members(grouped, x_field)
    ranked = {name: grouped[name] for name in members if name != OTHER_LABEL}
    if bucketed:
        ranked[OTHER_LABEL] = sum(grouped[name] for name in bucketed)

    sorted_items = sorted(ranked.items(), key=lambda x: -x[1])
    categories = [item[0] for item in sorted_items]
    values = [round(item[1], 4) for item in sorted_items]

    return {
        "xAxis": {"categories": _format_categories(categories, x_field), "title": {"text": x_field}},
        "yAxis": [
            {"title": {"text": value_field}},
            {"title": {"text": "Cumulative %"}, "opposite": True, "max": 100},
        ],
        "series": [
            {"type": "column", "name": value_field, "data": values},
            {"type": "pareto", "name": "Cumulative %", "yAxis": 1, "baseSeries": 0},
        ],
    }


def _aggregate(values: list[float], method: str) -> float:
    if not values:
        return 0.0
    if method == "sum":
        return round(sum(values), 4)
    elif method == "avg":
        return round(statistics.mean(values), 4)
    elif method == "min":
        return round(min(values), 4)
    elif method == "max":
        return round(max(values), 4)
    elif method == "count":
        return len(values)
    else:
        return round(sum(values), 4)


def _fallback_config(chart_spec: dict, rows: list[dict]) -> dict:
    return build_time_series(chart_spec, rows)


TRANSFORMS = {
    "build_time_series": build_time_series,
    "build_pie_data": build_pie_data,
    "build_scatter_data": build_scatter_data,
    "build_heatmap_data": build_heatmap_data,
    "build_boxplot_data": build_boxplot_data,
    "build_histogram_data": build_histogram_data,
    "build_hierarchy_data": build_hierarchy_data,
    "build_polar_data": build_polar_data,
    "build_range_data": build_range_data,
    "build_waterfall_data": build_waterfall_data,
    "build_pareto_data": build_pareto_data,
}
