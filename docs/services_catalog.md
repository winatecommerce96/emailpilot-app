# EmailPilot Services Catalog

This catalog enumerates all services in the EmailPilot monorepo that run servers, background processes, MCP wrappers, CLI entrypoints, or provide service-style libraries under `app/services`. It aims to provide a single source of truth for how to run and interact with each component, what it reads/writes, and how health is determined. Use this as a map for debugging, consolidation, and deployment planning.

| Name | Type | Path | Summary | Entrypoint(s) | Healthcheck | Status |
|---|---|---|---|---|---|---|
| emailpilot-backend-api | api | `main_firestore.py` | Primary FastAPI backend serving EmailPilot APIs with Firestore (includes `/api/tools` and `/api/mcp/*` local). | `uvicorn main_firestore:app --host 0.0.0.0 --port 8000` | `GET /health` | active |
| klaviyo-api-test | api | `services/klaviyo_api/main.py` | Standalone FastAPI for email-attributed revenue and MCP tooling. | `uvicorn services.klaviyo_api.main:app --host 127.0.0.1 --port 9090` or `make quick-check-revenue` | `GET /healthz` | active |
| performance-api | api | `services/performance_api/main.py` | Jobs API to compute/store weekly/monthly performance using revenue service. | `uvicorn services.performance_api.main:app --host 127.0.0.1 --port 9091` | `GET /healthz` | active |
| anthropic-mapper | api | `anthropic_mapper.py` | Small FastAPI proxy that maps model aliases and proxies to Anthropic. | `uvicorn anthropic_mapper:app` | `GET /health` | experimental |
| revenue-api-legacy | api | `services/revenue_api` | Legacy revenue service folder (implementation moved to klaviyo_api). | — | — | legacy |
| mcp-openapi-revenue | mcp | `services/klaviyo_api/openapi.yaml` | MCP wrapper for Klaviyo API service (revenue + weekly metrics tools). | `npx @modelcontextprotocol/openapi --spec services/klaviyo_api/openapi.yaml --server.url http://localhost:9090` | — | active |
| mcp-openapi-performance | mcp | `services/performance_api/openapi.yaml` | MCP wrapper for Performance Jobs API. | `npx @modelcontextprotocol/openapi --spec services/performance_api/openapi.yaml --server.url http://localhost:9091` | — | active |
| mcp-openapi-ai-models | mcp | `services/ai_models_api/openapi.yaml` | MCP wrapper for AI Models management endpoints. | `npx @modelcontextprotocol/openapi --spec services/ai_models_api/openapi.yaml --server.url http://localhost:8000` | — | experimental |
| emailpilot-legacy-app | api | `app/main.py` | Minimal FastAPI (early dev) with `/health` and `/goals/{user_id}`. | `uvicorn app.main:app --reload --port 8000` | `GET /health` | legacy |
| order-monitor | library | `app/services/order_monitor.py` | Library to fetch last-5-days revenue via Klaviyo API service and alert on zero-revenue. | — | — | active |
| admin-notifications | library | `app/services/admin_notifications.py` | Manage admin notifications and alerts stored in Firestore. | — | — | active |
| agent-service | library | `app/services/agent_service.py` | Base multi-agent orchestration helper for Email/SMS agents. | — | — | active |
| agent-service-enhanced | library | `app/services/agent_service_enhanced.py` | Enhanced agent orchestration utilities and helpers. | — | — | active |
| ai-models-service | library | `app/services/ai_models_service.py` | Manage AI model configurations, prompts, and related operations. | — | — | active |
| asana-client | library | `app/services/asana_client.py` | Asana API client helpers for project/task access. | — | — | active |
| asana-event-processor | library | `app/services/asana_event_processor.py` | Process and normalize incoming Asana webhook events. | — | — | active |
| asana-oauth | library | `app/services/asana_oauth.py` | Support Asana OAuth linking flows for users/clients. | — | — | active |
| auth-service | library | `app/services/auth.py` | Authentication helpers used by API routes (tokens/sessions). | — | — | active |
| calendar-planning-prompts | library | `app/services/calendar_planning_prompts.py` | Reusable prompt templates for AI calendar planning flows. | — | — | active |
| calendar-service | library | `app/services/calendar_service.py` | Calendar CRUD and helper routines backing calendar APIs. | — | — | active |
| client-key-resolver | library | `app/services/client_key_resolver.py` | Resolve per-client API keys/secrets from Secret Manager/Firestore. | — | — | active |
| client-linking | library | `app/services/client_linking.py` | Link user accounts to client resources (Klaviyo/Asana) with status checks. | — | — | active |
| env-manager | library | `app/services/env_manager.py` | Environment configuration and convenience helpers for settings. | — | — | active |
| firestore-service | library | `app/services/firestore.py` | Firestore access helpers and utility functions. | — | — | active |
| firestore-optimized | library | `app/services/firestore_optimized.py` | Optimized Firestore query patterns and batching utilities. | — | — | active |
| gemini-service | library | `app/services/gemini_service.py` | Google Gemini client wrappers and goal-aware prompt execution. | — | — | active |
| goal-generator | library | `app/services/goal_generator.py` | Generate goals and recommendations for campaign planning. | — | — | experimental |
| goal-manager | library | `app/services/goal_manager.py` | Create, update, and track goals in Firestore for clients. | — | — | active |
| goals-aware-gemini-service | library | `app/services/goals_aware_gemini_service.py` | Gemini prompts that incorporate goals context for better suggestions. | — | — | active |
| google-service | library | `app/services/google_service.py` | Google API helpers (auth, sheets/drive placeholders). | — | — | experimental |
| klaviyo-client | library | `app/services/klaviyo_client.py` | HTTP client for Klaviyo endpoints used by performance and monitoring flows. | — | — | active |
| klaviyo-data-service | library | `app/services/klaviyo_data_service.py` | Klaviyo data access utilities and aggregations. | — | — | active |
| klaviyo-direct-service | library | `app/services/klaviyo_direct.py` | Direct Klaviyo API access helpers (low-level). | — | — | active |
| klaviyo-discovery-service | library | `app/services/klaviyo_discovery.py` | Discover Klaviyo account metadata and available resources. | — | — | active |
| mcp-client | library | `app/services/mcp_client.py` | Client-side helpers/models for MCP interactions. | — | — | active |
| mcp-firestore-sync | library | `app/services/mcp_firestore_sync.py` | Sync MCP artifacts and usage into Firestore collections. | — | — | active |
| mcp-service | library | `app/services/mcp_service.py` | Provider-agnostic MCP manager to execute tools via Claude/OpenAI/Gemini. | — | — | active |
| performance-monitor | library | `app/services/performance_monitor.py` | Compute performance KPIs and trends for dashboards using stored data. | — | — | active |
| report-generator | library | `app/services/report_generator.py` | Generate weekly/monthly reports and insights from metrics. | — | — | active |
| secrets-service | library | `app/services/secrets.py` | Wrapper around Google Secret Manager to fetch/store project and client secrets. | — | — | active |
| slack-alerts | library | `app/services/slack_alerts.py` | Slack alerting (replaced by admin notifications). | — | — | legacy |

## Consolidation Suggestions
- Replace revenue-api-legacy with klaviyo-api-test; remove or redirect references to `services.revenue_api` to `services.klaviyo_api`.
- Prefer AdminNotificationService over Slack alerts; retire `slack_alerts.py` usage.
