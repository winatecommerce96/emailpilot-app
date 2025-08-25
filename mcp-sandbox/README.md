MCP Sandbox Service (Klaviyo + Firestore)

Overview
- A standalone FastAPI service that demonstrates a thin MCP-style orchestrator that:
  - Dispatches requests to external APIs (Klaviyo for now)
  - Persists state in Firestore (sessions, turns, tool logs, cache)
  - Returns natural-language answers with a compact evidence JSON block
  - Is modular to route results to downstream analyzers later

Key Features (MVP)
- Bearer auth for all non-health endpoints
- Health endpoints: GET /healthz, GET /readyz
- Clients: GET /clients (from Firestore)
- Chat: POST /chat → NL summary + evidence; persists session/turns/tool logs
- Simple cache: last successful tool response per (client,intent,range) with TTL (~15m)
- Rate limiting/backoff for Klaviyo (401/403 handled; 429 with exponential backoff; 5xx with retries)
- Minimal web UI under /web (dropdown, textarea, message list, evidence toggle)
- Clean abstractions for adding more tools/agents

Project Layout
- src/
  - server.py              → FastAPI app, routes, middleware
  - settings.py            → Env & defaults handling
  - auth.py                → Bearer auth dependency
  - logging_utils.py       → JSON logging + request IDs
  - models.py              → Pydantic data models
  - utils/
    - timeparse.py         → Parse date phrases (today/yesterday/last week/last 30 days)
    - ids.py               → Request/turn/session IDs
  - mcp/
    - orchestrator.py      → Rule-based intent → tool calls → NLG → persistence
    - nlg.py               → NL summary builders
    - tools/
      - firestore_state.py → Firestore MCP: profiles, sessions, turns, tool logs, cache
      - openapi_klaviyo.py → Klaviyo REST client with retries/backoff
- web/
  - index.html, app.js, styles.css
- scripts/
  - seed_demo_client.py    → Seed a demo client_profile in Firestore
  - run_dev.sh             → Convenience launcher
- tests/
  - test_health.py, test_chat_flow.py, test_klaviyo_tool.py
- requirements.txt, .env.example

Requirements
- Python 3.11+
- Google Firestore (via a service account JSON or ADC)
- Node not required (UI is static)

Configuration
- Copy .env.example → .env and set values. Settings precedence: env > .env > defaults.

Key env vars
- APP_AUTH_BEARER=change-me                 # Bearer token required for /chat and /clients
- GOOGLE_CLOUD_PROJECT=your-project-id
- GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
- CORS_ORIGINS=http://localhost:8000,http://localhost:3000
- CACHE_TTL_SECONDS=900
- SANDBOX_USE_INMEMORY=0                   # Set 1 for tests/dev to avoid Firestore

Run (Dev)
1) python -m venv .venv && source .venv/bin/activate
2) pip install -r requirements.txt
3) export $(grep -v '^#' .env | xargs)   # or set env manually
4) Optionally seed a demo client:
   python scripts/seed_demo_client.py --client_key demo --display_name "Demo Client" --klaviyo_api_key "sk_test_xxx"
5) Start server:
   uvicorn src.server:app --host 0.0.0.0 --port 9090 --reload

HTTP Examples
AUTH=change-me
curl -s http://localhost:9090/healthz
curl -s -H "Authorization: Bearer $AUTH" http://localhost:9090/clients
curl -s -H "Authorization: Bearer $AUTH" -H "Content-Type: application/json" \
  -d '{"client_key":"demo","text":"Summarize last week\'s campaign performance"}' \
  http://localhost:9090/chat | jq

Testing
- Unit + integration smoke tests (mocks for HTTP/Firestore):
  - export SANDBOX_USE_INMEMORY=1
  - pytest -q

Firestore Layout (collections)
- clients/{client_key} → ClientProfile
- sessions/{session_id} → { session_id, client_key, created_at, last_active_at }
- turns/{turn_id} → Turn
- tool_logs/{auto_id} → ToolResult log with request_id link
- caches/{hash_key} → { data, expires_at }

Notes
- No secrets are committed. Use Firestore + Secret Manager or local .env only for dev.
- Orchestrator is agent-agnostic to allow future plug-in analyzers.

