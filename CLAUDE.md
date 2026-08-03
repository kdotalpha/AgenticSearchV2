# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Pay-i Analytics is a natural-language-to-chart application for exploring AI/GenAI spending data tracked by the Pay-i platform. Users type a question in a search bar, the backend interprets it via the Claude Agent SDK into a structured query, fetches CSV report data from the Pay-i API, transforms it into Highcharts configs, and streams results to the browser over SSE.

## Running the App

```bash
# Install dependencies (Python 3.13+, installed globally)
pip3 install -r requirements.txt

# Copy .env.example to .env and fill in PAYI_BASE_URL, PAYI_API_KEY, REPORT_ID_1..6

# Start the dev server
uvicorn main:app --reload --port 8000
```

The interpreter uses the `claude-agent-sdk` Python package, which bundles its own Claude binary — no Claude CLI install is required. Auth comes from `ANTHROPIC_API_KEY` in `.env` (optional) or an existing Claude Code login.

## Architecture

The request flow for `/api/query` is:

1. **`claude_interpreter.py`** — Async `interpret_query()` calls the Claude Agent SDK's `query()` with the system prompt from `prompts.py` (report schemas, chart type guidance, and today's date) and structured output enforced via `output_format` with `schemas.py:INTERPRETATION_SCHEMA`. Runs hermetically (`tools=[]`, `setting_sources=[]`). Returns structured JSON with `reports_needed`, `time_range`, `charts[]`, and `filters[]`.

2. **`payi_client.py`** — `PayiClient` fetches reports by UUID from the Pay-i REST API (`/api/v1/reports/{id}`). Returns CSV parsed into `list[dict]`. The client does client-side date filtering on `Day`/`Month` columns.

3. **`data_transformer.py`** — Two stages: `apply_filters()` narrows rows, then `build_highcharts_config()` dispatches to a chart-type-specific transform function via `CHART_REGISTRY` (in `chart_registry.py`). Each transform (e.g., `build_time_series`, `build_pie_data`, `build_scatter_data`) produces a Highcharts-compatible config dict.

4. **`main.py`** — FastAPI app that streams SSE events (`progress`, `chart`, `complete`, `error`) back to the frontend as each step completes.

5. **`static/index.html`** — Single-page frontend. Consumes SSE, renders Highcharts in card-based layout with Pay-i brand theming. All Highcharts modules are loaded via CDN script tags.

### Key mappings

- `chart_registry.py:CHART_REGISTRY` maps ~35 chart type strings → `{ highcharts_type, transform, modules, plot_options }`. This is the single source of truth for which chart types exist and how they render.
- `schemas.py:INTERPRETATION_SCHEMA` is the JSON Schema enforced on Claude's output. The `chart_type` enum here must stay in sync with `CHART_REGISTRY` keys.
- `prompts.py` contains the full system prompt describing all 6 reports, their CSV columns, chart-to-report compatibility rules, and examples. This is what teaches the LLM how to interpret queries.

### Report IDs

Reports 1–6 are pre-configured Pay-i Query Builder reports. Their UUIDs are stored in `.env` as `REPORT_ID_1` through `REPORT_ID_6`. The integer keys in `config.py:REPORT_IDS` map to these UUIDs. `chart-query-mapping.md` documents what pivots/values each report uses and which chart types each supports. Chart transforms sum over any pivot dimension a chart doesn't reference, so three-pivot reports also serve simpler views.

## Adding a New Chart Type

1. Add the type string to the `chart_type` enum in `schemas.py`
2. Add an entry in `chart_registry.py:CHART_REGISTRY` pointing to the correct transform function and Highcharts module(s)
3. If no existing transform fits, add a new `build_*` function in `data_transformer.py` and register it in `TRANSFORMS`
4. Update the chart-type lists and compatibility section in `prompts.py` so the LLM knows when to pick it
5. If the chart needs a Highcharts module not already loaded, add the `<script>` tag in `static/index.html`

## Environment

- Python 3.13+ (dependencies installed globally, no virtualenv)
- FastAPI + Uvicorn
- No test suite currently exists
- Auth to Pay-i uses `xproxy-api-key` header (set via `PAYI_API_KEY` env var)
- The Claude Agent SDK is invoked with `model="sonnet"` and structured output enforced by `INTERPRETATION_SCHEMA`
