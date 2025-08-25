EmailPilot – Changelog and Legacy Map

Overview
- Purpose: Document recent stabilization/refactor changes, backward-compat auth, ops endpoints, and where legacy endpoints now live.
- Scope: Backend (FastAPI), Revenue API service, Admin UI, tests/CI, deployment helpers, and cleanup.

Highlights (Current Refactor)
- Logging: Rotating file logs with optional JSON console logs for Cloud Run.
  - Module: `app/utils/logging_utils.py`
  - Env: `LOG_FORMAT=plain|json` (json recommended on Cloud Run)
- Security: Request ID, structured request logging, security headers, trusted hosts, and rate limiting.
  - Modules: `app/middleware/security.py`, `app/middleware/ratelimit.py`
  - Env: `TRUSTED_HOSTS`, `RL_*` (see Env Quick Ref)
- CORS and Compression: Tunable CORS for backend and Revenue API plus `GZipMiddleware`.
  - Env: `CORS_ALLOW_ALL`, `CORS_ORIGINS`
- Health: `GET /health` on main app; `GET /healthz` on Revenue API.
- Auth Compatibility: Legacy endpoints wired to Google OAuth flow.
  - Module: `app/api/auth_compat.py`
  - Notes: Restores `/api/auth/login`, `/api/auth/me`, `/api/auth/logout` behavior while delegating to Google OAuth.
- Revenue API service: CORS-enabled microservice for Klaviyo revenue attribution (Campaign + Flow values reports).
  - Path: `services/revenue_api/main.py` (+ `openapi.yaml`)
  - Admin helpers: probe, start, stop endpoints exposed via Admin Ops panel.
- Firestore/Secrets: Shared Firestore client singleton and Secret Manager utilities to minimize overhead.
  - Path: `app/deps/`
- Admin Ops: Endpoints to list/cleanup large logs, list big files, and control Revenue API.
  - Path: `app/api/admin.py` (and related admin modules)
  - UI: `frontend/public/components/AdminOpsPanel.js`
- Rate limits: Stricter defaults on auth endpoints; env-tunable.
- CI/Tests: Smoke tests and workflows for quick regression coverage.
  - Path: `tests/` and `.github/workflows/smoke.yml`
- Deployment: Cloud Run helper script and targets with preflight checks.
  - Script: `scripts/deploy_cloud_run.sh`
- Cleanup: Dead endpoints moved to `archive/legacy/` with placeholders.

Backward Compatibility Notes
- Legacy auth routes:
  - `GET|POST /api/auth/login` → Redirects to Google OAuth authorize.
  - `GET /api/auth/me` → Delegates to Google userinfo; returns current user.
  - `POST /api/auth/logout` → Clears auth cookies and session.
  - Cookies hardened in non-dev: `Secure`, `HttpOnly`, `SameSite=Lax`.
- CORS:
  - For local dev, allow `http://localhost:*` and configured origins.
  - For Cloud Run, restrict via `CORS_ORIGINS`.
- Logging:
  - File logs rotate; console logs default to plain locally; JSON recommended in Cloud Run.
- Rate limits:
  - Auth endpoints use `RL_AUTH_*`; others use `RL_DEFAULT_*`.

Admin Ops – Key Endpoints
- `GET /api/admin/ops/logs/large?threshold=500M` – list large log files.
- `POST /api/admin/ops/logs/cleanup` – JSON body `{ mode: list|truncate|delete, threshold: "500M" }`.
- `GET /api/admin/ops/files/big?threshold=200M` – list large non-log files.
- `GET /api/admin/revenue/status?base=http://127.0.0.1:9090&origin=http://localhost:3000` – Revenue probe + CORS headers.
- `POST /api/admin/revenue/start` – start local Revenue API (dev-only).
- `POST /api/admin/revenue/stop` – stop the local Revenue API.

Revenue API – Summary
- Purpose: Correctly compute marketing-attributed revenue using Klaviyo values reports APIs for Campaigns and Flows.
- Endpoints: `GET /healthz`, `GET /clients/{client_id}/revenue/last7`, `GET /clients/by-slug/{slug}/revenue/last7`.
- Inputs: `timeframe_key` (default `last_7_days`), optional ISO `start`/`end`, or JSON `timeframe`; `recompute` bypasses cache.
- Output: `{ client_id, metric_id, campaign_total, flow_total, total, timeframe }`.
- Caching: In-memory; TTL via `REVENUE_CACHE_TTL`.
- Secrets: Resolves Klaviyo API key via Secret Manager or provided fallbacks.

Security and Observability
- Request IDs and structured log fields on every request.
- Security headers: HSTS (when HTTPS), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
- Trusted hosts: Restrict with `TRUSTED_HOSTS` in Cloud Run.
- Rate limiting: Env-tuned; protect auth endpoints more strictly.

Local Development
- Backend: `uvicorn app.main:app --reload` (or Make/script if provided).
- Revenue API (dev): Start via Admin Ops or `python services/revenue_api/main.py`.
- Health checks: `GET /health`, `GET :9090/healthz`.
- CORS: For localhost, either set `CORS_ALLOW_ALL=true` or specify `CORS_ORIGINS`.

Cloud Run Readiness
- Use `scripts/deploy_cloud_run.sh` for deployment guidance and checks.
- Set `LOG_FORMAT=json`, `TRUSTED_HOSTS` to your domain(s), and production cookie flags are applied automatically.

Legacy Archive
- Location: `archive/legacy/`
  - Example placeholders: `main.py.old`, `main_simple.py.old`, `main_with_db.py.old`, `main_emergency.py.old` + `README.md`.
- Why placeholders: To prevent confusion and keep production tree clean while preserving a breadcrumb trail.
- Recovering original content:
  - Use `git log -- <path>` to find the commit containing the original file.
  - Then `git show <commit>:<original/path>` to view the exact historical contents.
  - Optionally restore into `archive/legacy/` alongside the placeholder with a filename suffix like `.orig.<shortsha>`.

Known Gaps / Next Steps
- Consider adding a CSP once the frontend asset map is audited.
- Add metrics export (p50/p95 latencies, counters) to Cloud Monitoring or a `/metrics` endpoint.
- Normalize env var settings and remove unused ones over time.
- Standardize frontend calls to `/api/auth/google/me` and deprecate the compat shim when safe.

Environment Variables – Quick Reference
- `LOG_FORMAT`: `plain` (default), `json` for Cloud Run.
- `TRUSTED_HOSTS`: Comma-separated hostnames (e.g., `example.run.app,www.example.com`).
- `CORS_ALLOW_ALL`: `true|false`.
- `CORS_ORIGINS`: Comma-separated origins (e.g., `https://app.example.com,http://localhost:3000`).
- `RL_DEFAULT_MAX`, `RL_DEFAULT_WINDOW`: Defaults for generic endpoints.
- `RL_AUTH_MAX`, `RL_AUTH_WINDOW`: Stricter limits for auth endpoints.
- `GOOGLE_CLOUD_PROJECT`: Required for GCP integrations.
- Revenue: `REVENUE_CACHE_TTL`, optional Klaviyo secret name conventions.

Testing and CI
- `tests/` includes smoke tests for core endpoints and admin ops.
- `.github/workflows/smoke.yml` runs smoke tests on pushes/PRs.

Change Log (Recent)
- Added rotating file logging and JSON console logging.
- Introduced security, request ID, and logging middleware.
- Implemented rate limiting (auth-focused) and trusted hosts.
- Added `/health` (main) and `/healthz` (revenue service).
- Restored legacy auth endpoints via Google OAuth shim.
- Implemented Admin Ops endpoints and Admin UI panel for logs/files/revenue.
- Introduced Revenue API microservice with proper attribution logic.
- Added Firestore singleton and Secret Manager convenience helpers.
- Created Cloud Run deploy helper script and documentation.
- Added smoke tests and CI workflow.
- Archived dead endpoints to `archive/legacy/`.

