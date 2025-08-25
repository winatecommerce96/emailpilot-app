# AgentService: Setup, Usage, and Troubleshooting

This document explains how the in‑app AgentService is wired, what it needs to run, how to call it, and how to troubleshoot common issues.

## Overview
- Location: `app/services/agent_service.py`
- API entrypoint: `POST /api/agents/invoke` (see `app/api/agents.py`)
- Backend implementation: Uses `email-sms-mcp-server/server.py`'s `MultiAgentOrchestrator` (loaded in‑process, not via stdio)
- Config files: reads `email-sms-mcp-server/agents_config.json` (required) and optionally `email-sms-mcp-server/custom_instructions.json`

## AI Models Admin Integration
- Management UI: `/admin/ai-models` (SPA route, served by the app)
- Backend APIs:
  - `GET /api/ai-models/providers` — list providers and key status
  - `POST /api/ai-models/providers/{provider}/api-key` — set/update API keys
  - `GET /api/ai-models/prompts` and `POST /api/ai-models/prompts` — manage prompt templates in Firestore (`ai_prompts` collection)
  - `GET /api/agent-config/agents` — current agent → prompt mappings and status
  - `POST /api/agent-config/agents/{agent}/configure` — map an agent to a prompt and set provider/model/fallbacks
  - `POST /api/agent-config/agents/reload` — reload enhanced agents to pick up changes

How it works under the hood:
- `get_agent_service()` prefers the enhanced service (`app/services/agent_service_enhanced.py`).
- The enhanced orchestrator merges configuration from:
  1) `agents_config.json` (defaults)
  2) `custom_instructions.json` (optional overrides)
  3) Firestore `ai_prompts` (category=`agent`, using `metadata.agent_type` to map prompts to agents)
  4) Firestore `agent_configurations` (preferred provider/model, fallback providers, custom instructions)
- When you change prompts or mappings via the Admin UI/APIs, call `POST /api/agent-config/agents/reload` to apply live.

## Requirements
- Folder `email-sms-mcp-server` must exist at repo root alongside `app/`.
- File `email-sms-mcp-server/agents_config.json` must exist (present in this repo).
- Optional overrides in `email-sms-mcp-server/custom_instructions.json`.
- No special env vars are required specifically for AgentService.

## How It Loads
- AgentService prepends the path `email-sms-mcp-server` to `sys.path` and imports `MultiAgentOrchestrator` from `server.py`.
- `MultiAgentOrchestrator` loads `agents_config.json` and merges in `custom_instructions.json` if present.
- AgentService also (optionally) injects `custom_instructions` into each agent's `context` if that file exists. This is redundant but harmless.

## Calling the Service
- Endpoint: `POST /api/agents/invoke`
- Body (example — full email campaign orchestration):
  ```json
  {
    "campaign_type": "promotional",
    "target_audience": "high-value customers",
    "objectives": ["increase_sales", "drive_engagement"],
    "brand_guidelines": {"tone": "professional"},
    "customer_data": {"segments": ["vip_customers"]}
  }
  ```
- Response (success):
  ```json
  {
    "status": "success",
    "result": { "campaign_creation_complete": true, ... },
    "agents_used": ["content_strategist", "copywriter", ...]
  }
  ```

## Known Good Files
- `app/services/agent_service.py` — service wrapper
- `app/api/agents.py` — exposes `/api/agents/invoke`
- `email-sms-mcp-server/server.py` — orchestrator implementation
- `email-sms-mcp-server/agents_config.json` — base agent config (present)
- `email-sms-mcp-server/custom_instructions.json` — optional overrides (not present by default)

## Common Issues & Fixes
- ImportError: `MultiAgentOrchestrator` — ensure `email-sms-mcp-server/server.py` exists and the folder is at repo root. The service injects this path into `sys.path` automatically.
- Missing config — ensure `agents_config.json` exists (it does in this repo). `custom_instructions.json` is optional.
- Async invocation mismatch — `MultiAgentOrchestrator.orchestrate_campaign_creation` is async. In `AgentService.invoke_agent`, it should be awaited directly. Current implementation uses `asyncio.to_thread(...)` which can surface as an unserializable coroutine in responses. Recommended fix (code change):
  ```python
  result = await self.orchestrator.orchestrate_campaign_creation(data)
  ```
  This is a code change; no configuration change is needed.
- UI routes vs. service — `/api/agents/invoke` is included from `main_firestore.py`. Ensure the app is started from `main_firestore.py`.
- Admin page not reflecting in responses — after editing prompts/mappings in `/admin/ai-models`, trigger a reload:
  ```bash
  curl -s -X POST http://localhost:8000/api/agent-config/agents/reload
  ```
  Then re‑invoke the agent.

## Creating Custom Instructions (optional)
Create `email-sms-mcp-server/custom_instructions.json` with partial overrides, for example:
```json
{
  "agents": {
    "copywriter": {
      "tone": "brand_serious",
      "responsibilities": ["short_subjects", "cta_focus"]
    }
  }
}
```
The orchestrator merges this file when present. AgentService also adds it into each agent's context under `custom_instructions` for convenience.

## Smoke Test (local)
- Start the app (from repo root):
  - `uvicorn main_firestore:app --host 0.0.0.0 --port 8000 --reload`
- Health: `curl -s http://localhost:8000/health`
- Invoke agents: 
  ```bash
  curl -s -X POST http://localhost:8000/api/agents/invoke \
    -H 'Content-Type: application/json' \
    -d '{"campaign_type":"promotional","target_audience":"high-value customers"}'
  ```
If configured correctly, you should receive a JSON payload with `status":"success"` and the orchestrated result.

Optional: Invoke with a specific prompt (via AI Models Service):
```bash
curl -s -X POST http://localhost:8000/api/agents/invoke-with-prompt \
  -H 'Content-Type: application/json' \
  -d '{
        "agent_type":"content_strategist",
        "context":{"campaign_type":"promotional","target_audience":"vip"}
      }'
```

## Status: Config OK, One Code Fix Advised
- Configuration and file layout are correct; `agents_config.json` is present; `custom_instructions.json` is optional.
- Recommend updating `AgentService.invoke_agent` to directly `await` the async orchestrator method to avoid coroutine leakage.
