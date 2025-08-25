Klaviyo API (formerly Revenue API) — MCP Setup and In‑App Chat

Overview
- The local FastAPI service under `services/revenue_api` is the Klaviyo API service. Naming is being migrated from “Revenue API”.
- A true MCP interface is provided via the OpenAPI MCP wrapper (`@modelcontextprotocol/openapi`) which the app controls via HTTP.

Key Endpoints (EmailPilot)
- Klaviyo service admin (aliases):
  - `GET /api/admin/klaviyo/status` — health + CORS probe (alias of legacy `/api/admin/revenue/status`).
  - `POST /api/admin/klaviyo/start` — start local service (alias of legacy `/api/admin/revenue/start`).
  - `POST /api/admin/klaviyo/stop` — stop local service (alias of legacy `/api/admin/revenue/stop`).
- Weekly report (MCP V2): `POST /api/reports/mcp/v2/weekly/generate`
- Monthly report with agent prompting: `POST /api/reports/monthly/generate`
- MCP Chat:
 - `GET /api/mcp/tools` — list available MCP tools from the OpenAPI wrapper
  - `POST /api/mcp/chat` — call an MCP tool with arguments
  - Weekly insights (prompts): `POST /api/reports/mcp/v2/weekly/insights` (use `{ "preview": true }` to avoid Slack)

Shared Helper
- Module: `app/utils/klaviyo_api.py`
  - `get_base_url()` resolves `KLAVIYO_API_BASE` then `REVENUE_API_BASE` then defaults to `http://localhost:9090`.
  - `ensure_klaviyo_api_available()` checks `/healthz` and auto‑starts `uvicorn services.revenue_api.main:app` if down (dev convenience), waiting briefly for readiness.

MCP Wrapper
- The EmailPilot app talks to the MCP wrapper via the Klaviyo API service:
  - `POST http://localhost:9090/admin/mcp/start {"kind":"openapi_revenue"}`
  - `POST http://localhost:9090/admin/mcp/call` for raw JSON‑RPC
 - `POST http://localhost:9090/admin/mcp/tools/smart_call` for tool routing
  - `GET  http://localhost:9090/admin/mcp/status`

Environment
- Preferred: `KLAVIYO_API_BASE=http://localhost:9090`
- Back‑compat: `REVENUE_API_BASE` still supported.
- Optional: `KLAVIYO_API_HOST`, `KLAVIYO_API_PORT` for auto‑start.

Smoke Tests
1) Start EmailPilot backend:
   - `uvicorn main_firestore:app --host 0.0.0.0 --port 8000`
2) Weekly MCP report (auto‑starts service if needed):
   - `curl -s -X POST http://localhost:8000/api/reports/mcp/v2/weekly/generate | jq .`
   - `curl -s -X POST http://localhost:8000/api/reports/mcp/v2/weekly/insights -H 'Content-Type: application/json' -d '{"preview": true}' | jq .`
3) Monthly report (with agent summary):
   - `curl -s -X POST http://localhost:8000/api/reports/monthly/generate | jq .`
4) MCP tools list + chat:
   - `curl -s http://localhost:8000/api/mcp/tools | jq .`
   - `curl -s -X POST http://localhost:8000/api/mcp/chat -H 'Content-Type: application/json' -d '{"tool_name":"GET /clients/{client_id}/revenue/last7","arguments":{"client_id":"example-slug","timeframe_key":"last_7_days"}}' | jq .`

Notes
- Physical folder rename to `services/klaviyo_api` can be done later; code already uses the “Klaviyo API” naming and supports both env var names. When renaming, update uvicorn targets and imports.
- The `/api/mcp/chat` endpoint is a thin proxy: it executes a specified tool and returns the response quickly for an in‑app “chat” experience.
