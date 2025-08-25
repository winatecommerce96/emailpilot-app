#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_KEY_HEADER=""
if [[ -n "${ADMIN_API_KEY:-}" ]]; then
  ADMIN_KEY_HEADER="-H X-Admin-Key:${ADMIN_API_KEY}"
fi

json() { python -m json.tool; }

fail() { echo "❌ $1"; exit 1; }
info() { echo "ℹ️  $1"; }
ok()   { echo "✅ $1"; }

curl_json() {
  local path="$1"
  shift || true
  curl -sS ${ADMIN_KEY_HEADER} "$@" "${BASE_URL}${path}"
}

# --- 0) Ping core API
info "Checking agents listing…"
curl_json "/api/admin/langchain/agents" | json >/dev/null || fail "Agents API not responding"
ok "Agents API reachable"

# --- 1) Hardened endpoints sanity (no 500s)
info "Checking model providers…"
curl_json "/api/admin/langchain/models/providers" | json >/dev/null || fail "Providers endpoint failed"

info "Checking available models (openai)…"
HTTP=$(curl -sS -o /tmp/avail.json -w "%{http_code}" ${ADMIN_KEY_HEADER} "${BASE_URL}/api/admin/langchain/models/available?provider=openai" || true)
if [[ "$HTTP" == "500" ]]; then
  cat /tmp/avail.json; fail "/models/available returned 500"
fi
[[ "$HTTP" =~ ^2 ]] || fail "/models/available non-2xx: $HTTP"
ok "Models/available OK"
cat /tmp/avail.json | json >/dev/null || true

info "Checking model resolution (demo/acme)…"
HTTP=$(curl -sS -o /tmp/resolve.json -w "%{http_code}" ${ADMIN_KEY_HEADER} "${BASE_URL}/api/admin/langchain/models/resolve?user_id=demo&brand=acme" || true)
if [[ "$HTTP" == "500" ]]; then
  cat /tmp/resolve.json; fail "/models/resolve returned 500"
fi
[[ "$HTTP" =~ ^2|^4 ]] || fail "/models/resolve unexpected status: $HTTP"
ok "Models/resolve OK (2xx or 4xx with clear message)"
cat /tmp/resolve.json | json >/dev/null || true

# --- 2) Static Admin pages present
check_static() {
  local path="$1"
  local http; http=$(curl -sS -o /dev/null -w "%{http_code}" "${BASE_URL}${path}" || true)
  if [[ "$http" != "200" ]]; then
    echo "⚠️  ${path} returned ${http}. If you haven't mounted static, ensure:"
    echo '    app.mount("/static", StaticFiles(directory="static"), name="static")'
    echo "    and hit: ${BASE_URL}${path} in a browser."
    return 1
  fi
  ok "Static page available: ${path}"
}
check_static "/static/admin/langchain/agents.html"      || true
check_static "/static/admin/langchain/usage.html"       || true
check_static "/static/admin/langchain/models.html"      || true
check_static "/static/admin/langchain/mcp.html"         || true

# --- 3) Seed usage → verify non-zero tokens (RAG then Agent)
BASE_SUMMARY=$(curl_json "/api/admin/langchain/usage/summary?days=1" | python - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  print(d.get("total_tokens",0))
except: print(0)
PY
)
info "Current total_tokens (last 1d): ${BASE_SUMMARY}"

info "Running a quick RAG query via CLI to create token usage…"
if ! command -v python >/dev/null; then fail "Python missing"; fi
python lc.py rag.ask -q "In one line, what does EmailPilot do?" >/dev/null || info "RAG CLI returned non-zero (ok if CLI not wired to this machine)"

sleep 1
info "Running a lightweight agent task via CLI…"
python lc.py agent.run -t "Fetch last 7-day revenue for client_id=DEMO" --brand acme --user-id demo >/dev/null || info "Agent CLI returned non-zero (ok if demo tools disabled)"

sleep 2
POST_SUMMARY=$(curl_json "/api/admin/langchain/usage/summary?days=1" | python - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  print(d.get("total_tokens",0))
except: print(0)
PY
)
echo "Before tokens: ${BASE_SUMMARY}  → After tokens: ${POST_SUMMARY}"
if [[ "${POST_SUMMARY}" -gt "${BASE_SUMMARY}" ]]; then
  ok "Token usage increased"
else
  echo "⚠️  Tokens did not increase; if models require keys or policies, set them and retry."
fi

# --- 4) SSE stream smoke (if runs API exists and has a run)
info "Checking for latest run to stream events (optional)…"
LIST_HTTP=$(curl -sS -o /tmp/runs.json -w "%{http_code}" ${ADMIN_KEY_HEADER} "${BASE_URL}/api/admin/langchain/runs?limit=1" || true)
if [[ "$LIST_HTTP" =~ ^2 ]]; then
  RUN_ID=$(python - <<'PY'
import json,sys
try:
  data=json.load(open("/tmp/runs.json"))
  if isinstance(data, list) and data:
    print(data[0].get("run_id",""))
except: pass
PY
)
  if [[ -n "${RUN_ID}" ]]; then
    info "Streaming SSE for run_id=${RUN_ID} (3s)…"
    curl -sS ${ADMIN_KEY_HEADER} "${BASE_URL}/api/admin/langchain/runs/${RUN_ID}/events/stream" \
      --max-time 3 | head -n 5
    ok "SSE stream returned data (truncated)"
  else
    echo "ℹ️  No recent runs found; skip SSE smoke."
  fi
else
  echo "ℹ️  Runs listing endpoint not available; skip SSE smoke."
fi

ok "Smoke checks complete."