Weekly Performance Pipeline — MCP + AI Prompts

Overview
- Endpoint: `POST /api/reports/mcp/v2/weekly/insights`
- Collects weekly metrics for all clients, generates:
  - Individual client insights (4 insights + 4 actions) via your provided prompt
  - Company-wide summary (4 insights + 4 actions) via your provided prompt
- Posts a concise company summary to Slack; optional per-client Slack posts.

Data Flow
- Klaviyo API (MCP-backed): `services/klaviyo_api`
  - `GET /clients/{client_id}/weekly/metrics` computes:
    - `weekly_revenue`, `weekly_orders`, `campaign_revenue`, `campaign_orders`, `flow_revenue`, `flow_orders`
    - Derived from Klaviyo values reports using “Placed Order” metric.
- Performance monitor (existing): additional weekly metrics when available, e.g. open rate, CTR, AOV.

Prompts
- Individual Client Weekly Insights Prompt
  - Exactly 4 insights + 4 actions. Injected with metrics for each client.
- Company-Wide Summary Insights Prompt
  - Exactly 4 summary insights + 4 actions. Includes client breakdown lines with WoW where available.

Managing Prompts in Admin
- Use AI Models Admin API to store/edit prompts in Firestore (`ai_prompts`):
  - Create “weekly_client_insights” (category: analysis, provider: your choice, active: true)
  - Create “weekly_company_summary” (category: analysis, provider: your choice, active: true)
- Although the endpoint embeds robust defaults, keeping these prompts in `ai_prompts` lets you revise wording live.
  Example create:
  - `POST /api/ai-models/prompts`
    {
      "name": "weekly_client_insights",
      "description": "Per-client weekly insights (4+4)",
      "prompt_template": "You are a CRM expert analyzing weekly Klaviyo performance for {account_name}\n\nWEEKLY PERFORMANCE DATA:\n- Total Revenue: ${weekly_revenue}\n- Total Orders: {weekly_orders}\n- Campaign Revenue: ${campaign_revenue} ({campaign_orders} orders)\n- Flow Revenue: ${flow_revenue} ({flow_orders} orders)\n- Overall Open Rate: {open_rate}%\n- Overall Click Rate: {click_rate}%\n- Click Through Rate: {click_through_rate}%\n- Conversion Rate: {conversion_rate}%\n- Average Order Value: ${avg_order_value}\n- Revenue per Recipient: ${revenue_per_recipient}\n- Week over Week Change: {wow_change}\n- Monthly Goal Progress: {goal_progress}\n- Status: {on_track_status}\n\nProvide exactly 4 bullet point insights about performance and exactly 4 bullet point action items.\n\nFormat your response as:\nINSIGHTS:\n• [insight 1]\n• [insight 2]\n• [insight 3]\n• [insight 4]\n\nACTIONS:\n• [action 1]\n• [action 2]\n• [action 3]\n• [action 4]",
      "model_provider": "gemini",
      "model_name": "gemini-1.5-pro-latest",
      "category": "analysis",
      "variables": ["account_name","weekly_revenue","weekly_orders","campaign_revenue","campaign_orders","flow_revenue","flow_orders","open_rate","click_rate","click_through_rate","conversion_rate","avg_order_value","revenue_per_recipient","wow_change","goal_progress","on_track_status"],
      "active": true
    }


API Usage
- Generate and post company summary (and return all prompts/responses):
  - `POST /api/reports/mcp/v2/weekly/insights`
  - Body options:
    - `send_client_posts` (bool): also posts each client’s insights to Slack (default comes from Admin setting)
    - `preview` (bool, default false): do not post to Slack; just return prompts and responses

Slack Setup
- Secret: `emailpilot-slack-webhook-url`
- Company summary is always sent unless `preview=true`.
- Per-client posts are controlled by `send_client_posts`.

Admin Setting
- GET `/api/admin/reports/settings` → `{ weekly_send_client_posts_default }`
- POST `/api/admin/reports/settings` with `{ weekly_send_client_posts_default: true|false }`

MCP Endpoints Added
- `GET /clients/{client_id}/weekly/metrics`
- `GET /clients/by-slug/{slug}/weekly/metrics`
- Both live under `services/klaviyo_api/main.py`.

Testing
- Preview mode: `POST /api/reports/mcp/v2/weekly/insights {"preview": true}` returns all rendered prompts and AI responses without Slack posts.
- Smoke: run main app then call the endpoint; verify Slack receives a company summary and top client list.
