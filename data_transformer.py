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

        categories = sorted(set(row.get(x_field, "") for row in rows))
        series = []
        for s_name, x_data in sorted(grouped.items()):
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
        "xAxis": {"categories": categories, "title": {"text": x_field}},
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

    data = [{"name": name, "y": val} for name, val in sorted(grouped.items(), key=lambda x: -x[1])]

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

    x_categories = sorted(set(row.get(x_field, "") for row in rows))
    y_categories = sorted(set(row.get(y_field, "") for row in rows))

    x_map = {v: i for i, v in enumerate(x_categories)}
    y_map = {v: i for i, v in enumerate(y_categories)}

    data = []
    cell_values = defaultdict(float)
    for row in rows:
        x_idx = x_map.get(row.get(x_field, ""), 0)
        y_idx = y_map.get(row.get(y_field, ""), 0)
        cell_values[(x_idx, y_idx)] += _to_float(row.get(value_field, "0"))

    for (x_idx, y_idx), val in cell_values.items():
        data.append([x_idx, y_idx, round(val, 4)])

    all_vals = [d[2] for d in data] or [0]

    return {
        "xAxis": {"categories": x_categories, "title": {"text": x_field}},
        "yAxis": {"categories": y_categories, "title": {"text": y_field}},
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

    flow = defaultdict(float)
    for row in rows:
        from_node = row.get(x_field, "")
        to_node = row.get(y_field, "")
        if from_node and to_node:
            flow[(from_node, to_node)] += _to_float(row.get(value_field, "0"))

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
            if parent not in nodes:
                nodes[parent] = {"id": parent, "name": parent, "value": 0}
            nodes[parent]["value"] += weight
            child_id = f"{parent}-{child}"
            if child_id not in nodes:
                nodes[child_id] = {"id": child_id, "name": child, "parent": parent, "value": 0}
            nodes[child_id]["value"] += weight

        data = [{"id": "root", "name": "All"}]
        for node_id, node in nodes.items():
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
        series = []
        for s_name, cat_data in sorted(grouped.items()):
            data = [round(cat_data.get(c, 0), 4) for c in categories]
            series.append({"name": s_name, "data": data, "pointPlacement": "on"})
    else:
        grouped = defaultdict(float)
        for row in rows:
            cat = row.get(x_field, "")
            grouped[cat] += _to_float(row.get(value_field, "0"))

        categories = sorted(grouped.keys())
        data = [round(grouped[c], 4) for c in categories]
        series = [{"name": value_field, "data": data, "pointPlacement": "on"}]

    return {
        "xAxis": {
            "categories": categories,
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

    sorted_items = sorted(grouped.items(), key=lambda x: -x[1])
    categories = [item[0] for item in sorted_items]
    values = [round(item[1], 4) for item in sorted_items]

    return {
        "xAxis": {"categories": categories, "title": {"text": x_field}},
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
