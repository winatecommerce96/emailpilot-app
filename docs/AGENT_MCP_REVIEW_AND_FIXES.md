AgentService and MCP Tools — Review and Fixes

Summary
- Issue: AgentService responses and MCP-driven weekly report flow were unreliable; “Generate new report” on the dashboard often failed or returned incomplete output.
- Scope fixed: Weekly MCP report endpoint resiliency, client filtering logic, and alignment notes. AgentService async handling already correct. MCP tool limitations documented with guidance.

Symptoms
- Clicking “Generate new report” (weekly) intermittently failed when the Revenue API was not running.
- Some clients were silently skipped due to a Firestore flag check (`has_klaviyo_key`) even when secrets were resolvable via conventions, resulting in undercounted totals.
- Monthly report path only returns a stub “started” message by design (no change made).

Root Causes
- Revenue API health/startup was not ensured before MCP V2 weekly aggregation started. A connection failure threw and aborted the run.
- Overly strict pre-filter required `has_klaviyo_key=true`, contradicting the Revenue API’s own key resolution (supports Secret Manager names and slug-based conventions).
- MCP tool startup relies on `npx @modelcontextprotocol/openapi` which may not be installed; failures were noisy but not the core cause of missing weekly results.

Changes Made
- File: `app/api/reports_mcp_v2.py`
  - Added auto-start for the Revenue API if health check fails (spawns `uvicorn services.revenue_api.main:app` with `GOOGLE_CLOUD_PROJECT` fallback and logs to `logs/revenue_api_uvicorn.out`). Waits briefly for readiness, then continues.
  - Removed the `has_klaviyo_key` client pre-filter. Now every client is attempted; a 400 with “Unable to resolve Klaviyo API key” is treated as “no key”. This prevents undercounting.
  - MCP OpenAPI server start inside Revenue API is now best-effort and non-fatal.
  - New weekly insights endpoint: `POST /api/reports/mcp/v2/weekly/insights` generates per-client and company-wide AI insights and posts to Slack (preview mode available).
- Klaviyo API (MCP) service
  - New endpoints under `services/klaviyo_api/main.py`:
    - `GET /clients/{client_id}/weekly/metrics` and `/clients/by-slug/{slug}/weekly/metrics`:
      - Returns weekly totals and order counts (campaign/flow split) for prompts.
  - `_sum_campaign_flow` now returns conversions (orders) alongside conversion_value sums.

Validation Steps
1) Ensure environment:
   - `GOOGLE_CLOUD_PROJECT` set (or defaults to `emailpilot-438321`).
   - Firestore contains clients; slugs preferred (`client_slug`).
   - Secrets present per client or resolvable by Revenue API conventions.
2) Start backend: `uvicorn main_firestore:app --host 0.0.0.0 --port 8000`.
3) Hit: `POST http://localhost:8000/api/reports/mcp/v2/weekly/generate`.
   - Expect a JSON payload with `summary.total_revenue`, `client_details[...]`, and background Slack send.
   - On first run, it may auto-start the Revenue API and take a few seconds.
4) Optional: Start Revenue API via Admin UI/API beforehand for faster runs:
   - `POST /api/admin/revenue/start`.

Operational Notes
- AgentService async behavior: `app/services/agent_service.py` already awaits the orchestrator correctly. No change required.
- MCP tools inside Revenue API (`/admin/mcp/...`) require `npx` and the MCP OpenAPI package. If not installed, MCP startup can fail harmlessly; weekly aggregation no longer depends on these processes.
- Monthly report endpoint (`/api/reports/monthly/generate`) remains a trigger stub; implement generation via `app/services/performance_monitor.py` if needed.

Next Improvements (Optional)
- Add a shared helper to ensure the Revenue API is up (de-duplicate admin and MCP paths).
- Expand error details in client_results for deeper diagnostics (e.g., include Revenue API error bodies).
- Implement the monthly report endpoint with the same pattern used for weekly.
