# Pay-i Analytics

A natural-language analytics interface for exploring AI/GenAI spending data tracked by [Pay-i](https://pay-i.com). Type a question like "Show me daily spend by resource" or "What's the distribution of spend per instance?" and get interactive Highcharts visualizations back in seconds.

## How It Works

1. You type a question in the search bar
2. The backend sends your question to Claude (via the Claude Agent SDK) along with a system prompt describing your available reports and chart types
3. Claude returns structured JSON specifying which reports to fetch, time range, chart configurations, and filters
4. The backend fetches the relevant CSV reports from the Pay-i API, applies filters, and transforms the data into Highcharts configs
5. Results stream back to the browser via Server-Sent Events, rendering charts as they're ready

## Prerequisites

- **Python 3.13+**
- **Anthropic auth** — either `ANTHROPIC_API_KEY` in `.env`, or an existing Claude Code login (the `claude-agent-sdk` dependency bundles its own Claude binary)
- **Pay-i account** — with API key and pre-configured Query Builder reports

## Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` with your values:

```
PAYI_BASE_URL=https://api.pay-i.com/
PAYI_API_KEY=sk-payi-app-your-key-here
REPORT_ID_1=<uuid>
REPORT_ID_2=<uuid>
...
REPORT_ID_6=<uuid>
```

Each `REPORT_ID_N` corresponds to a pre-configured Pay-i Query Builder report. See `chart-query-mapping.md` for what pivots and values each report should have.

## Running

```bash
uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Required Report Configurations

Each report must be created in the Pay-i Query Builder with the exact pivots and values listed below. The resulting CSV column names must match exactly.

Chart transforms automatically collapse any pivot dimension a chart doesn't reference by summing over it, so a three-pivot report also serves simpler one- and two-dimensional charts.

> **Warning:** Adding any `Request: *` value (Latency, ID, Spend, ...) to a query forces it to per-request detail level — the pivots stop aggregating and row counts explode (~60k rows/week). Only Report 3 is intentionally detail-level; keep `Request: *` values out of all other reports.

The API returns compact PascalCase CSV headers (`DateDay`, `UseCase`, `RequestLatency`, ...); `payi_client.py:COLUMN_NAME_MAP` normalizes them to the display names below, which is what the rest of the app uses.

### Report 1: Daily by Use Case and Resource

| | Fields |
|---|--------|
| **Pivots** | `@ Day`, `Use Case`, `Resource` |
| **Values** | `Spend`, `Units`, `Requests`, `Instances` |
| **CSV columns** | `Day`, `Use Case`, `Resource`, `Spend`, `Units`, `Requests`, `Instances` |

The workhorse report. Best for: line, area, column, bar, stacked variants, streamgraph, heatmap, pie, treemap, word cloud, radar, sankey (Use Case -> Resource), dependency wheel, pareto, bubble, daily use case trends.

### Report 2: Monthly by Category and Use Case

| | Fields |
|---|--------|
| **Pivots** | `@ Month`, `Category`, `Use Case` |
| **Values** | `Spend`, `Instances`, `Requests`, `Units` |
| **CSV columns** | `Month`, `Category`, `Use Case`, `Spend`, `Instances`, `Requests`, `Units` |

Best for: sunburst, sankey, dependency wheel, treemap, funnel, monthly trend lines, stacked area.

### Report 3: Instance-Level Detail

| | Fields |
|---|--------|
| **Pivots** | `Use Case`, `Instance ID`, `Resource` |
| **Values** | `Spend`, `Request: Latency` |
| **CSV columns** | `Use Case`, `Instance ID`, `Resource`, `Spend`, `Request: Latency`, `Request: ID` |

Best for: box plot, scatter, histogram, bell curve, column range, area range, lollipop, latency analysis (the only report with latency). Note: `Requests` and `Units` cannot be used as values when pivoting by `Instance ID` (Pay-i limitation). This report is per-request detail (`Request: Latency` forces it; the API adds `Request: ID` automatically) — large date ranges are slow and may time out, so the LLM is instructed to keep it to ≤14 days.

### Report 4: Hourly Pattern by Category

| | Fields |
|---|--------|
| **Pivots** | `@ Hour`, `Category` |
| **Values** | `Spend`, `Requests`, `Units` |
| **CSV columns** | `Hour`, `Category`, `Spend`, `Requests`, `Units` |

Best for: polar/radar, wind rose, polar column, hourly trend lines, heatmap.

### Report 5: Daily by Resource and Response Code

| | Fields |
|---|--------|
| **Pivots** | `@ Day`, `Resource`, `Response Code` |
| **Values** | `Spend`, `Requests` |
| **CSV columns** | `Day`, `Resource`, `Response Code`, `Spend`, `Requests` |

Best for: pie/donut (success vs failure), stacked bar, percent column, waterfall, pareto, error trends over time.

### Report 6: Daily by Use Case and Version

| | Fields |
|---|--------|
| **Pivots** | `@ Day`, `Use Case`, `Use Case Version` |
| **Values** | `Spend`, `Units`, `Instances`, `Requests` |
| **CSV columns** | `Day`, `Use Case`, `Use Case Version`, `Spend`, `Units`, `Instances`, `Requests` |

Best for: grouped column, dumbbell, waterfall, heatmap, radar (multi-metric per version), version trends over time.

## Supported Chart Types

Line, area, stacked area, spline, column, stacked column, bar, stacked bar, streamgraph, pie, donut, treemap, sunburst, scatter, bubble, heatmap, boxplot, histogram, bell curve, column range, area range, waterfall, pareto, funnel, sankey, dependency wheel, radar, polar column, wind rose, dumbbell, lollipop, word cloud, error bar, and combo line+column.

## Project Structure

```
main.py                 FastAPI app with SSE streaming endpoint
claude_interpreter.py   Claude Agent SDK call for NL→structured JSON
payi_client.py          HTTP client for the Pay-i reports API
data_transformer.py     Chart-type-specific data transforms
chart_registry.py       Maps chart types → Highcharts configs and transforms
schemas.py              JSON Schema enforced on Claude's output
prompts.py              System prompt with report definitions and rules
config.py               Environment variable loading
static/index.html       Single-page frontend with Highcharts rendering
```

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **LLM Integration**: claude-agent-sdk (structured output via JSON Schema)
- **Charting**: Highcharts (loaded via CDN)
- **Data Source**: Pay-i REST API (CSV reports)
