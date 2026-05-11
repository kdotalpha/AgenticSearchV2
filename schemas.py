INTERPRETATION_SCHEMA = {
    "type": "object",
    "properties": {
        "reports_needed": {
            "type": "array",
            "items": {"type": "integer", "minimum": 1, "maximum": 8},
            "description": "Which report IDs (1-8) to fetch"
        },
        "time_range": {
            "type": "object",
            "properties": {
                "from_date": {"type": "string", "description": "YYYY-MM-DD start date"},
                "to_date": {"type": "string", "description": "YYYY-MM-DD end date"}
            },
            "required": ["from_date", "to_date"]
        },
        "charts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": [
                            "line", "area", "stacked_area", "percent_area",
                            "spline", "column", "stacked_column", "percent_column",
                            "bar", "stacked_bar", "streamgraph",
                            "pie", "donut", "treemap", "sunburst",
                            "scatter", "bubble",
                            "heatmap",
                            "boxplot", "histogram", "bellcurve",
                            "column_range", "area_range",
                            "waterfall", "pareto", "funnel",
                            "sankey", "dependency_wheel",
                            "radar", "polar_column", "wind_rose",
                            "dumbbell", "lollipop",
                            "word_cloud",
                            "error_bar", "combo_line_column"
                        ]
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "report_id": {"type": "integer", "minimum": 1, "maximum": 8},
                    "x_field": {"type": "string"},
                    "y_field": {"type": "string"},
                    "series_field": {"type": ["string", "null"]},
                    "value_field": {"type": "string"},
                    "aggregation": {
                        "type": "string",
                        "enum": ["sum", "avg", "min", "max", "count", "none"]
                    }
                },
                "required": ["chart_type", "title", "report_id", "value_field"]
            }
        },
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "operator": {
                        "type": "string",
                        "enum": ["equals", "not_equals", "contains", "in", "not_in", "gt", "lt", "gte", "lte"]
                    },
                    "value": {}
                },
                "required": ["field", "operator", "value"]
            }
        }
    },
    "required": ["reports_needed", "time_range", "charts"]
}
