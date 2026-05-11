import json
import traceback
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import PAYI_BASE_URL, PAYI_API_KEY, REPORT_IDS, DEFAULT_TIME_RANGE_DAYS
from payi_client import PayiClient
from claude_interpreter import interpret_query
from data_transformer import apply_filters, build_highcharts_config

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

    async def generate():
        try:
            yield _sse_event("progress", {"step": "interpreting", "percent": 10, "message": "Interpreting your query..."})

            interpretation = interpret_query(user_query)

            yield _sse_event("progress", {
                "step": "interpreted",
                "percent": 25,
                "message": "Query interpreted, fetching data...",
                "time_range": interpretation.get("time_range", {}),
                "filters": interpretation.get("filters", []),
            })

            reports_needed = interpretation.get("reports_needed", [])
            time_range = interpretation.get("time_range", {})
            from_date = time_range.get("from_date", (date.today() - timedelta(days=DEFAULT_TIME_RANGE_DAYS)).isoformat())
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

            yield _sse_event("progress", {"step": "transforming", "percent": 70, "message": "Building charts..."})

            chart_configs = []
            for chart_spec in charts:
                rid = chart_spec.get("report_id")
                rows = report_data.get(rid, [])

                filtered_rows = apply_filters(rows, filters)

                config = build_highcharts_config(chart_spec, filtered_rows)
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
