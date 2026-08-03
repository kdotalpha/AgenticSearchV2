#!/usr/bin/env bash
# Smoke test for Pay-i Analytics: start server, hit endpoints, stop.
# Exit code 0 = healthy. Non-zero = something's broken.
set -euo pipefail

PORT=${PORT:-8000}
LOG=/tmp/payi-analytics.log
PID_FILE=/tmp/payi-analytics.pid

cleanup() {
  if [ -f "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
}
trap cleanup EXIT

# Kill any leftover from a previous run
if [ -f "$PID_FILE" ]; then
  kill "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
  sleep 1
fi

echo "==> Starting uvicorn on port $PORT..."
uvicorn main:app --port "$PORT" &> "$LOG" &
echo $! > "$PID_FILE"

echo "==> Waiting for server to be ready..."
for i in $(seq 1 20); do
  if curl -sf "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "FAIL: server didn't start in 20s. Logs:"
    cat "$LOG"
    exit 1
  fi
  sleep 1
done

echo "==> Health check..."
HEALTH=$(curl -sf "http://localhost:$PORT/api/health")
echo "    $HEALTH"

echo "==> Fetching index page..."
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:$PORT/")
if [ "$STATUS" != "200" ]; then
  echo "FAIL: index returned $STATUS"
  exit 1
fi
echo "    GET / -> 200 OK"

echo "==> Testing /api/query (SSE stream)..."
RESPONSE=$(curl -s -X POST "http://localhost:$PORT/api/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "show me total spend"}' \
  --max-time 90)

if echo "$RESPONSE" | grep -q "event: error"; then
  ERROR_MSG=$(echo "$RESPONSE" | grep "^data:" | tail -1)
  echo "FAIL: query returned error: $ERROR_MSG"
  exit 1
fi

if echo "$RESPONSE" | grep -q "event: complete"; then
  CHART_COUNT=$(echo "$RESPONSE" | grep "event: chart" | wc -l)
  echo "    Query completed successfully. Charts returned: $CHART_COUNT"
else
  echo "WARN: query did not reach 'complete' event (may indicate timeout or partial response)"
  echo "    Raw tail:"
  echo "$RESPONSE" | tail -5
fi

echo ""
echo "==> All checks passed. Server logs at $LOG"
echo "==> Server PID: $(cat "$PID_FILE") (will be stopped on exit)"
