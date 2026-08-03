---
name: run-payi-analytics
description: Build, run, and drive Pay-i Analytics. Use when asked to start the app, test the server, verify a change works, or interact with the running API.
---

Pay-i Analytics is a FastAPI server that streams Highcharts configs over SSE. Drive it via the smoke script at `.claude/skills/run-payi-analytics/smoke.sh` or manually with `curl` against the API.

## Prerequisites

- Python 3.13+ with pip
- Anthropic auth for the `claude-agent-sdk` interpreter: `ANTHROPIC_API_KEY` in `.env` (optional) or an existing Claude Code login. No Claude CLI install needed — the SDK bundles its own binary.
- A configured `.env` file with `PAYI_BASE_URL`, `PAYI_API_KEY`, and `REPORT_ID_1` through `REPORT_ID_6`

```bash
pip install -r requirements.txt
```

## Setup

Copy `.env.example` to `.env` and fill in the real values. The app won't start without `PAYI_BASE_URL` and `PAYI_API_KEY`.

## Run (agent path)

Run the smoke script — it starts the server, verifies health, tests the query endpoint, and stops cleanly:

```bash
bash .claude/skills/run-payi-analytics/smoke.sh
```

Exit code 0 means the full pipeline (interpret → fetch → transform → stream) works. Logs land at `/tmp/payi-analytics.log`.

### Manual curl interaction

To keep the server running and poke it interactively:

```bash
uvicorn main:app --port 8000 &> /tmp/payi-analytics.log &
echo $! > /tmp/payi-analytics.pid

# Wait for ready
for i in $(seq 1 20); do
  curl -sf http://localhost:8000/api/health > /dev/null && break
  sleep 1
done
```

Health check:

```bash
curl http://localhost:8000/api/health
# → {"status":"ok","reports_configured":6}
```

Query (returns SSE stream):

```bash
curl -s -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "show me total spend over the last 30 days"}' \
  --max-time 90
```

The response is a stream of `event: progress`, `event: chart`, and `event: complete` SSE frames. Each `chart` event contains a `config` field with a Highcharts-compatible JSON object.

Stop the server:

```bash
kill $(cat /tmp/payi-analytics.pid)
```

## Run (human path)

```bash
uvicorn main:app --reload --port 8000
# Open http://localhost:8000 in a browser. Type a query, press Enter. Ctrl-C to stop.
```

## Test

No test suite exists. The smoke script is the primary verification.

## Gotchas

- **Nested Claude Code sessions are no longer a problem.** The interpreter uses the `claude-agent-sdk`, which manages its subprocess environment itself — running the server or `claude_interpreter.py` from inside a Claude Code session works (verified 2026-08-03). Never manually unset or strip the `CLAUDECODE` env var anywhere.
- **Empty chart data is normal for narrow date ranges.** The LLM picks dates based on the query; if the Pay-i account has no data for that period, the chart series will be empty arrays. This is not a bug — the pipeline still works end-to-end.
- **Port 8000 conflicts.** If something else is on 8000, override with `PORT=8001 bash .claude/skills/run-payi-analytics/smoke.sh` (the smoke script respects `$PORT`).

## Troubleshooting

- **`ModuleNotFoundError: No module named 'fastapi'`**: Run `pip install -r requirements.txt`. Dependencies are installed globally (no virtualenv).
- **`FileNotFoundError: .env`**: Copy `.env.example` to `.env` and fill in the values.
- **`ModuleNotFoundError: No module named 'claude_agent_sdk'` during query**: Run `pip install -r requirements.txt`.
- **Auth errors / "Not logged in" in the SSE error event**: Set `ANTHROPIC_API_KEY` in `.env`, or log in to Claude Code once (`claude` then `/login`).
- **Server starts but `/api/query` returns an SSE error event**: Check `/tmp/payi-analytics.log` for the traceback. Common causes: expired API key, invalid report UUIDs, or the Pay-i API being unreachable.
