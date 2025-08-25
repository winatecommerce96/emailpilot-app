# Klaviyo API (Test)

A small FastAPI service that returns email-attributed metrics for the last 7 days by summing Klaviyo Campaign and Flow "conversion_value" for the client's "Placed Order" metric.

- Endpoint: `GET /clients/{client_id}/revenue/last7`
- Endpoint: `GET /clients/{client_id}/weekly/metrics` (campaign/flow totals + order counts)
- Endpoint: `GET /clients/{client_id}/weekly/full` (adds emails_sent/opened/clicked and derived rates)
- Auth: Uses Secret Manager to resolve the client-specific Klaviyo API key.
- Client config: Reads from Firestore `clients/{client_id}`.
- Timeframe: `last_7_days` (matches Klaviyo UI boundaries/timezone).
- Output: `{ client_id, metric_id, campaign_total, flow_total, total, timeframe }`

Notes
- Metric ID per client: The service reads `placed_order_metric_id` from Firestore if present (`placed_order_metric_id`, `metrics.placed_order_metric_id`, or `klaviyo_placed_order_metric_id`). If missing, it discovers the best "Placed Order" metric by probing candidates and selects the one with non-zero activity.
- Secret resolution: The service supports these patterns for the key:
  - `klaviyo_api_key_secret`: Secret Manager name (e.g., `klaviyo-api-rogue-creamery`), or full resource path `projects/.../secrets/.../versions/...`.
  - `api_key_encrypted`: If base64 encoded and decodes to a value that looks like a key (e.g., starts with `pk_`), it is used as a raw API key. Otherwise, it is treated like a secret name.
  - Fallback to `klaviyo_api_key` when secret references are not available.

Local run
- `export GOOGLE_CLOUD_PROJECT=emailpilot-438321`
- `uvicorn services.klaviyo_api.main:app --host 0.0.0.0 --port 9090`
- `curl http://localhost:9090/healthz`
- `curl "http://localhost:9090/clients/<client_doc_id>/revenue/last7"`
- `curl "http://localhost:9090/clients/<client_doc_id>/weekly/metrics"`
- `curl "http://localhost:9090/clients/<client_doc_id>/weekly/full"`
