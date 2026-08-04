import json
import logging
import traceback
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import PAYI_BASE_URL, PAYI_API_KEY, REPORT_IDS
from payi_client import PayiClient
from claude_interpreter import interpret_query, select_charts
from data_profile import build_data_profile
from data_transformer import apply_filters, build_highcharts_config

# uvicorn only attaches handlers to its own loggers, so configure ours explicitly
logging.basicConfig(level=logging.INFO, format="%(levelname)s:    %(name)s %(message)s")
log = logging.getLogger("payi.pipeline")

# Charts whose whole purpose is comparing members of a dimension. One data point means the
# dimension had a single value, so the chart says nothing even though it "rendered".
COMPARISON_CHARTS = {
    "pie", "donut", "treemap", "sunburst", "pareto", "funnel", "word_cloud",
    "bar", "column", "stacked_bar", "stacked_column", "waterfall", "sankey",
    "dependency_wheel", "heatmap",
}

app = FastAPI(title="Pay-i Analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

payi_client = PayiClient(PAYI_BASE_URL, PAYI_API_KEY)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "reports_configured": len(REPORT_IDS)}


@app.post("/api/query")
async def query(request: Request):
    body = await request.json()
    user_query = body.get("query", "")
    log.info("query: %s", user_query)

    async def generate():
        try:
            yield _sse_event("progress", {"step": "interpreting", "percent": 10, "message": "Interpreting your query..."})

            interpretation = await interpret_query(user_query)
            log.info("interpretation: %s", json.dumps(interpretation))

            yield _sse_event("progress", {
                "step": "interpreted",
                "percent": 25,
                "message": "Query interpreted, fetching data...",
                "time_range": interpretation.get("time_range", {}),
                "filters": interpretation.get("filters", []),
            })

            reports_needed = interpretation.get("reports_needed", [])
            time_range = interpretation.get("time_range", {})
            # Fallback matches the 90-day default the system prompt gives the LLM
            from_date = time_range.get("from_date", (date.today() - timedelta(days=90)).isoformat())
            to_date = time_range.get("to_date", date.today().isoformat())
            charts = interpretation.get("charts", [])
            filters = interpretation.get("filters", [])

            report_uuids = []
            for rid in reports_needed:
                uuid = REPORT_IDS.get(rid)
                if uuid:
                    report_uuids.append((rid, uuid))

            yield _sse_event("progress", {"step": "fetching", "percent": 40, "message": f"Fetching {len(report_uuids)} report(s)..."})

            report_data = {}
            for rid, uuid in report_uuids:
                rows = payi_client.fetch_report(uuid, from_date, to_date)
                report_data[rid] = rows
                log.info("report %s (%s..%s): %d rows", rid, from_date, to_date, len(rows))

            # Second interpreter pass: the first one picked charts from the wording of the
            # question alone, before any data existed. Now that the rows are in hand, re-pick
            # with the real dimension cardinalities and per-metric nonzero counts in view.
            yield _sse_event("progress", {"step": "selecting", "percent": 55, "message": "Matching charts to your data..."})

            profile = build_data_profile(report_data, from_date, to_date)
            log.info("data profile:\n%s", profile)
            try:
                selected = await select_charts(user_query, profile)
            except Exception as e:
                # A failed second pass must never fail the request — degrade to pass 1.
                log.warning("chart selection failed, keeping initial charts: %s", e)
            else:
                log.info(
                    "charts re-selected: %s -> %s",
                    [c.get("chart_type") for c in charts],
                    [c.get("chart_type") for c in selected],
                )
                log.info("selected charts: %s", json.dumps(selected))
                charts = selected

            yield _sse_event("progress", {"step": "transforming", "percent": 70, "message": "Building charts..."})

            chart_configs = []
            for i, chart_spec in enumerate(charts, start=1):
                rid = chart_spec.get("report_id")
                rows = report_data.get(rid, [])
                if rid not in report_data:
                    log.warning(
                        "chart %d (%s) wants report %s, which is not in reports_needed=%s",
                        i, chart_spec.get("chart_type", ""), rid, reports_needed,
                    )

                filtered_rows = apply_filters(rows, filters)
                log.info(
                    "chart %d (%s) report=%s: %d rows -> %d after filters",
                    i, chart_spec.get("chart_type", ""), rid, len(rows), len(filtered_rows),
                )

                # A field the report doesn't have would otherwise group every row under ""
                # and render as a silently empty chart.
                if filtered_rows:
                    available = set(filtered_rows[0].keys())
                    for key in ("x_field", "y_field", "series_field", "value_field"):
                        field = chart_spec.get(key)
                        if field and field not in available:
                            log.warning(
                                "chart %d (%s) %s=%r is not a column of report %s (has: %s)",
                                i, chart_spec.get("chart_type", ""), key, field, rid,
                                sorted(available),
                            )

                config = build_highcharts_config(chart_spec, filtered_rows)

                # Catch-all for the failure the user actually sees: a chart that rendered
                # nothing, or collapsed to a single point so there is nothing to compare.
                # Any cause — missing column, degenerate dimension, transform mismatch —
                # surfaces here rather than shipping a blank card to the browser.
                points = sum(len(s.get("data") or []) for s in config.get("series", []))
                if points == 0:
                    log.warning(
                        "chart %d (%s) produced NO data points from %d rows; spec=%s",
                        i, chart_spec.get("chart_type", ""), len(filtered_rows),
                        json.dumps(chart_spec),
                    )
                elif points == 1 and chart_spec.get("chart_type") in COMPARISON_CHARTS:
                    log.warning(
                        "chart %d (%s) collapsed to a single data point; spec=%s",
                        i, chart_spec.get("chart_type", ""), json.dumps(chart_spec),
                    )
                else:
                    log.info("chart %d (%s): %d data points", i, chart_spec.get("chart_type", ""), points)

                chart_configs.append(config)

                yield _sse_event("chart", {
                    "config": config,
                    "chart_type": chart_spec.get("chart_type", ""),
                    "title": chart_spec.get("title", "Chart"),
                    "description": chart_spec.get("description", ""),
                })

            yield _sse_event("progress", {"step": "complete", "percent": 100, "message": "Done!"})
            yield _sse_event("complete", {"count": len(chart_configs)})

        except Exception as e:
            yield _sse_event("error", {"message": str(e), "traceback": traceback.format_exc()})

    return StreamingResponse(generate(), media_type="text/event-stream")
