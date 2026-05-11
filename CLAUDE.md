# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Pay-i Analytics is a natural-language-to-chart application for exploring AI/GenAI spending data tracked by the Pay-i platform. Users type a question in a search bar, the backend interprets it via the Claude CLI into a structured query, fetches CSV report data from the Pay-i API, transforms it into Highcharts configs, and streams results to the browser over SSE.

## Running the App

```bash
# Install dependencies (Python 3.13+, virtual env at .venv/)
pip install -r requirements.txt

# Copy .env.example to .env and fill in PAYI_BASE_URL, PAYI_API_KEY, REPORT_ID_1..8

# Start the dev server
uvicorn main:app --reload --port 8000
```

The Claude CLI (`claude`) must be installed and on PATH — the interpreter shells out to it via subprocess.

## Architecture

The request flow for `/api/query` is:

1. **`claude_interpreter.py`** — Builds a prompt from `prompts.py` (system prompt with report schemas, chart type guidance, and today's date) plus the user query. Calls the Claude CLI as a subprocess with `--json-schema` pointing to `schemas.py:INTERPRETATION_SCHEMA`. Returns structured JSON with `reports_needed`, `time_range`, `charts[]`, and `filters[]`.

2. **`payi_client.py`** — `PayiClient` fetches reports by UUID from the Pay-i REST API (`/api/v1/reports/{id}`). Returns CSV parsed into `list[dict]`. The client does client-side date filtering on `Day`/`Month` columns.

3. **`data_transformer.py`** — Two stages: `apply_filters()` narrows rows, then `build_highcharts_config()` dispatches to a chart-type-specific transform function via `CHART_REGISTRY` (in `chart_registry.py`). Each transform (e.g., `build_time_series`, `build_pie_data`, `build_scatter_data`) produces a Highcharts-compatible config dict.

4. **`main.py`** — FastAPI app that streams SSE events (`progress`, `chart`, `complete`, `error`) back to the frontend as each step completes.

5. **`static/index.html`** — Single-page frontend. Consumes SSE, renders Highcharts in card-based layout with Pay-i brand theming. All Highcharts modules are loaded via CDN script tags.

### Key mappings

- `chart_registry.py:CHART_REGISTRY` maps ~35 chart type strings → `{ highcharts_type, transform, modules, plot_options }`. This is the single source of truth for which chart types exist and how they render.
- `schemas.py:INTERPRETATION_SCHEMA` is the JSON Schema enforced on Claude's output. The `chart_type` enum here must stay in sync with `CHART_REGISTRY` keys.
- `prompts.py` contains the full system prompt describing all 8 reports, their CSV columns, chart-to-report compatibility rules, and examples. This is what teaches the LLM how to interpret queries.

### Report IDs

Reports 1–8 are pre-configured Pay-i Query Builder reports. Their UUIDs are stored in `.env` as `REPORT_ID_1` through `REPORT_ID_8`. The integer keys in `config.py:REPORT_IDS` map to these UUIDs. `chart-query-mapping.md` documents what pivots/values each report uses and which chart types each supports.

## Adding a New Chart Type

1. Add the type string to the `chart_type` enum in `schemas.py`
2. Add an entry in `chart_registry.py:CHART_REGISTRY` pointing to the correct transform function and Highcharts module(s)
3. If no existing transform fits, add a new `build_*` function in `data_transformer.py` and register it in `TRANSFORMS`
4. Update the chart-type lists and compatibility section in `prompts.py` so the LLM knows when to pick it
5. If the chart needs a Highcharts module not already loaded, add the `<script>` tag in `static/index.html`

## Environment

- Python 3.13+ with `.venv/` virtualenv
- FastAPI + Uvicorn
- No test suite currently exists
- Auth to Pay-i uses `xproxy-api-key` header (set via `PAYI_API_KEY` env var)
- The Claude CLI is invoked with `--model sonnet` and `--output-format json`
