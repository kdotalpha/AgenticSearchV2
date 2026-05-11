CHART_REGISTRY = {
    "line": {
        "highcharts_type": "line",
        "transform": "build_time_series",
        "modules": [],
    },
    "area": {
        "highcharts_type": "area",
        "transform": "build_time_series",
        "modules": [],
    },
    "stacked_area": {
        "highcharts_type": "area",
        "transform": "build_time_series",
        "modules": [],
        "plot_options": {"area": {"stacking": "normal"}},
    },
    "percent_area": {
        "highcharts_type": "area",
        "transform": "build_time_series",
        "modules": [],
        "plot_options": {"area": {"stacking": "percent"}},
    },
    "spline": {
        "highcharts_type": "spline",
        "transform": "build_time_series",
        "modules": [],
    },
    "column": {
        "highcharts_type": "column",
        "transform": "build_time_series",
        "modules": [],
    },
    "stacked_column": {
        "highcharts_type": "column",
        "transform": "build_time_series",
        "modules": [],
        "plot_options": {"column": {"stacking": "normal"}},
    },
    "percent_column": {
        "highcharts_type": "column",
        "transform": "build_time_series",
        "modules": [],
        "plot_options": {"column": {"stacking": "percent"}},
    },
    "bar": {
        "highcharts_type": "bar",
        "transform": "build_time_series",
        "modules": [],
    },
    "stacked_bar": {
        "highcharts_type": "bar",
        "transform": "build_time_series",
        "modules": [],
        "plot_options": {"bar": {"stacking": "normal"}},
    },
    "streamgraph": {
        "highcharts_type": "streamgraph",
        "transform": "build_time_series",
        "modules": ["modules/streamgraph"],
    },
    "pie": {
        "highcharts_type": "pie",
        "transform": "build_pie_data",
        "modules": [],
    },
    "donut": {
        "highcharts_type": "pie",
        "transform": "build_pie_data",
        "modules": [],
        "series_options": {"innerSize": "60%"},
    },
    "treemap": {
        "highcharts_type": "treemap",
        "transform": "build_pie_data",
        "modules": ["modules/treemap"],
    },
    "sunburst": {
        "highcharts_type": "sunburst",
        "transform": "build_hierarchy_data",
        "modules": ["modules/sunburst"],
    },
    "scatter": {
        "highcharts_type": "scatter",
        "transform": "build_scatter_data",
        "modules": [],
    },
    "bubble": {
        "highcharts_type": "bubble",
        "transform": "build_scatter_data",
        "modules": ["highcharts-more"],
    },
    "heatmap": {
        "highcharts_type": "heatmap",
        "transform": "build_heatmap_data",
        "modules": ["modules/heatmap"],
    },
    "boxplot": {
        "highcharts_type": "boxplot",
        "transform": "build_boxplot_data",
        "modules": ["highcharts-more"],
    },
    "histogram": {
        "highcharts_type": "histogram",
        "transform": "build_histogram_data",
        "modules": ["modules/histogram-bellcurve"],
    },
    "bellcurve": {
        "highcharts_type": "bellcurve",
        "transform": "build_histogram_data",
        "modules": ["modules/histogram-bellcurve"],
    },
    "column_range": {
        "highcharts_type": "columnrange",
        "transform": "build_range_data",
        "modules": ["highcharts-more"],
    },
    "area_range": {
        "highcharts_type": "arearange",
        "transform": "build_range_data",
        "modules": ["highcharts-more"],
    },
    "waterfall": {
        "highcharts_type": "waterfall",
        "transform": "build_waterfall_data",
        "modules": [],
    },
    "pareto": {
        "highcharts_type": "column",
        "transform": "build_pareto_data",
        "modules": ["modules/pareto"],
    },
    "funnel": {
        "highcharts_type": "funnel",
        "transform": "build_pie_data",
        "modules": ["modules/funnel"],
    },
    "sankey": {
        "highcharts_type": "sankey",
        "transform": "build_hierarchy_data",
        "modules": ["modules/sankey"],
    },
    "dependency_wheel": {
        "highcharts_type": "dependencywheel",
        "transform": "build_hierarchy_data",
        "modules": ["modules/sankey", "modules/dependency-wheel"],
    },
    "radar": {
        "highcharts_type": "line",
        "transform": "build_polar_data",
        "modules": ["highcharts-more"],
        "chart_options": {"polar": True},
    },
    "polar_column": {
        "highcharts_type": "column",
        "transform": "build_polar_data",
        "modules": ["highcharts-more"],
        "chart_options": {"polar": True},
    },
    "wind_rose": {
        "highcharts_type": "column",
        "transform": "build_polar_data",
        "modules": ["highcharts-more"],
        "chart_options": {"polar": True},
        "plot_options": {"column": {"stacking": "normal"}},
    },
    "dumbbell": {
        "highcharts_type": "dumbbell",
        "transform": "build_range_data",
        "modules": ["highcharts-more", "modules/dumbbell"],
    },
    "lollipop": {
        "highcharts_type": "lollipop",
        "transform": "build_time_series",
        "modules": ["highcharts-more", "modules/lollipop"],
    },
    "word_cloud": {
        "highcharts_type": "wordcloud",
        "transform": "build_pie_data",
        "modules": ["modules/wordcloud"],
    },
    "error_bar": {
        "highcharts_type": "errorbar",
        "transform": "build_range_data",
        "modules": ["highcharts-more"],
    },
    "combo_line_column": {
        "highcharts_type": "column",
        "transform": "build_time_series",
        "modules": [],
    },
}
