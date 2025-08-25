EmailPilot – Rollout & Deployment Checklist

Owner and Dates
- Owner: <name>
- Target rollout window: <dates>
- Environments: local → staging → production (Cloud Run)

Preflight (Local)
- [ ] Pull latest `main` and review `docs/CHANGELOG_AND_LEGACY.md`.
- [ ] Set env: `LOG_FORMAT=plain`, `CORS_ALLOW_ALL=true` (or set `CORS_ORIGINS`), `GOOGLE_CLOUD_PROJECT`.
- [ ] Start backend; verify `GET /health` returns 200.
- [ ] Admin UI loads; status banner shows green for core checks.
- [ ] Run smoke tests: `pytest -q tests/test_smoke.py`.
- [ ] Auth shim works:
  - [ ] `GET /api/auth/login` redirects to Google OAuth.
  - [ ] `GET /api/auth/me` returns user when logged in.
  - [ ] `POST /api/auth/logout` clears cookies.
- [ ] Revenue API local:
  - [ ] Start via Admin Ops or `python services/revenue_api/main.py`.
  - [ ] `GET :9090/healthz` returns 200.
  - [ ] Admin probe shows CORS headers and OK status.

Disk / Logs Hygiene
- [ ] `GET /api/admin/ops/logs/large?threshold=500M` returns no oversized logs;
      otherwise run cleanup with `truncate|delete` mode.
- [ ] `GET /api/admin/ops/files/big?threshold=200M` has no unexpected large files.

Security & Observability
- [ ] Confirm security headers present on a normal request (inspect response headers).
- [ ] Confirm request ID attached to logs and responses.
- [ ] Rate limits: attempt quick burst on `/api/auth/*` to see 429s when expected.

Staging (Cloud Run)
- [ ] Configure service env:
  - [ ] `LOG_FORMAT=json`
  - [ ] `TRUSTED_HOSTS=<your.run.app>,<custom-domain>`
  - [ ] `CORS_ALLOW_ALL=false` and set `CORS_ORIGINS` to allowed origins.
  - [ ] `RL_*` tuned for expected auth traffic.
- [ ] Deploy via `scripts/deploy_cloud_run.sh` or CI workflow.
- [ ] Verify `/health` and basic routes; tail logs for JSON structure.
- [ ] Admin Ops panel surfaces revenue status; CORS checks pass from frontend.
- [ ] Smoke tests against staging URL (where applicable).

Production (Cloud Run)
- [ ] Promote staging image or redeploy with same config.
- [ ] Post-deploy checks:
  - [ ] `/health` and key endpoints respond 200.
  - [ ] Admin Ops badges are green; no large logs accumulating.
  - [ ] OAuth callbacks working; cookies `Secure`/`HttpOnly`/`SameSite=Lax` set.
  - [ ] Rate limiting and trusted hosts enforced.
- [ ] Monitor logs for errors, latency p95/p99, and 429/5xx rates for 24–48h.

Rollback Plan
- [ ] If critical issues arise, roll back to previous revision in Cloud Run.
- [ ] Re-run smoke tests and validate `/health`.
- [ ] File an incident note with root cause and follow-ups.

Post-Rollout Follow-ups
- [ ] Consider adding CSP headers after asset audit.
- [ ] Add metrics export or `/metrics` endpoint (p50/p95 and counters).
- [ ] Normalize/unify env var documentation in one place.
- [ ] Plan deprecation of auth compat shim and standardize on `/api/auth/google/*`.

References
- Changelog & Legacy Map: `docs/CHANGELOG_AND_LEGACY.md`
- Revenue service: `services/revenue_api/`
- Admin Ops UI: `frontend/public/components/AdminOpsPanel.js`
- Admin Ops API: `app/api/admin.py` and related modules
- Deploy helper: `scripts/deploy_cloud_run.sh`
- CI: `.github/workflows/smoke.yml`

