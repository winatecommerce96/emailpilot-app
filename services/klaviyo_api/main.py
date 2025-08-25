import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any
import base64

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import subprocess
import threading
import json as _json
from google.cloud import firestore
from google.cloud import secretmanager


PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set for Secret Manager/Firestore access")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Klaviyo API (Test)", description="Email-attributed metrics via Klaviyo Campaign+Flow reports")

# Rotating file logging (local dev safety)
try:
    from app.utils.logging_utils import setup_rotating_file_logging
    setup_rotating_file_logging("klaviyo_api", logfile=os.path.join("logs", "klaviyo_api.log"))
except Exception:
    # Optional best-effort; continue without rotation if helper unavailable
    pass


# --- Simple in-memory cache (TTL seconds) ---
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = int(os.environ.get("REVENUE_CACHE_TTL", os.environ.get("KLAVIYO_CACHE_TTL", "300")))  # default 5 minutes


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    item = _CACHE.get(key)
    if not item:
        return None
    if time.time() - item["ts"] > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return item["value"]


def _cache_set(key: str, value: Dict[str, Any]) -> None:
    _CACHE[key] = {"ts": time.time(), "value": value}


def access_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    resp = client.access_secret_version(request={"name": name})
    return resp.payload.data.decode("utf-8")


def get_firestore_client() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)


def resolve_client_config(client_id: str) -> Dict[str, Any]:
    db = get_firestore_client()
    doc = db.collection("clients").document(client_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found in Firestore")
    cfg = doc.to_dict() or {}
    cfg["_doc_id"] = client_id
    return cfg


async def _resolve_named_metric_id(klaviyo_key: str, metric_name: str) -> Optional[str]:
    """Find a Klaviyo metric id by exact name match."""
    base = "https://a.klaviyo.com/api"
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "accept": "application/json",
        "revision": "2024-07-15",
    }
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{base}/metrics/?fields[metric]=name", headers=headers)
        if r.status_code != 200:
            return None
        data = r.json() or {}
        for item in (data.get("data") or []):
            attrs = item.get("attributes") or {}
            if attrs.get("name") == metric_name:
                return item.get("id")
    return None


async def _count_events(klaviyo_key: str, metric_id: str, start_iso: str, end_iso: str) -> int:
    """Count events for a metric using metric aggregates over an absolute range.

    Notes: timeframe_key is not supported on aggregates; use start/end. This is best-effort.
    """
    base = "https://a.klaviyo.com/api"
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "accept": "application/json",
        "content-type": "application/json",
        "revision": "2024-07-15",
    }
    body = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "metric_id": metric_id,
                "measurement": "count",
                "filter": f"between(timestamp, {start_iso}, {end_iso})",
                "interval": "day",
            },
        }
    }
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{base}/metric-aggregates/", headers=headers, json=body)
        if r.status_code != 200:
            return 0
        data = r.json() or {}
        total = 0
        try:
            for row in (((data.get("data") or {}).get("attributes") or {}).get("results") or []):
                total += int(row.get("measurement") or 0)
        except Exception:
            pass
        return total


# Allow local development calls from the main app or static server
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def resolve_klaviyo_key(client_cfg: Dict[str, Any]) -> str:
    # Preferred fields
    secret_ref = client_cfg.get("klaviyo_api_key_secret") or client_cfg.get("api_key_encrypted")
    # 1) If secret_ref looks like a full resource path, use as-is
    if isinstance(secret_ref, str) and secret_ref.startswith("projects/"):
        try:
            client = secretmanager.SecretManagerServiceClient()
            resp = client.access_secret_version(request={"name": secret_ref})
            return resp.payload.data.decode("utf-8")
        except Exception as e:
            # fall through to other strategies
            pass
    # 2) If secret_ref is base64 of a raw API key, decode and return (attempt before SM name)
    if isinstance(secret_ref, str) and secret_ref:
        try:
            dec = base64.b64decode(secret_ref).decode("utf-8", errors="strict").strip()
            # Heuristic: printable ASCII and reasonable length
            if dec and all(32 <= ord(c) <= 126 for c in dec) and len(dec) >= 16:
                return dec
        except Exception:
            pass
    # 3) Try treating secret_ref as a Secret Manager name within this project
    if isinstance(secret_ref, str) and secret_ref:
        try:
            return access_secret(PROJECT_ID, secret_ref)
        except Exception:
            pass
    # 4) Fallback to raw key field
    raw = client_cfg.get("klaviyo_api_key")
    if isinstance(raw, str) and raw:
        return raw.strip()
    # 5) Derive from slug convention (klaviyo-api-{slug})
    slug = client_cfg.get("client_slug")
    if isinstance(slug, str) and slug:
        try:
            return access_secret(PROJECT_ID, f"klaviyo-api-{slug}")
        except Exception:
            pass
    raise HTTPException(status_code=400, detail="Unable to resolve Klaviyo API key for client.")


def resolve_metric_id(client_cfg: Dict[str, Any], default_name: str = "Placed Order") -> Optional[str]:
    # Common storage patterns
    for key in (
        "metric_id",  # Current Firestore field name
        "placed_order_metric_id",
        "metrics.placed_order_metric_id",
        "klaviyo_placed_order_metric_id",
    ):
        v = client_cfg.get(key)
        if v:
            return v
    # Leave fallback to caller to try alternatives if needed
    return None


async def _find_best_placed_order_metric(klaviyo_key: str) -> Optional[str]:
    base = "https://a.klaviyo.com/api"
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "accept": "application/json",
        "revision": "2024-07-15",
    }
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{base}/metrics/?fields[metric]=name", headers=headers)
        r.raise_for_status()
        data = r.json()
        candidates = [item["id"] for item in (data.get("data") or []) if (item.get("attributes") or {}).get("name") == "Placed Order"]
    # Probe each candidate using last_7_days values reports; choose the one with highest total
    best_id = None
    best_total = 0.0
    for mid in candidates:
        try:
            totals = await _sum_campaign_flow_last7(klaviyo_key, mid)
            if totals.get("total", 0) > best_total:
                best_total = totals["total"]
                best_id = mid
        except Exception:
            continue
    return best_id


async def _sum_campaign_flow(klaviyo_key: str, metric_id: str, timeframe: Dict[str, Any]) -> Dict[str, Any]:
    base = "https://a.klaviyo.com/api"
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "accept": "application/json",
        "content-type": "application/json",
        "revision": "2024-07-15",
    }
    campaign_payload = {
        "data": {
            "type": "campaign-values-report",
            "attributes": {
                "statistics": ["conversions", "conversion_value"],
                "conversion_metric_id": metric_id,
                "timeframe": timeframe,
            },
        }
    }
    flow_payload = {
        "data": {
            "type": "flow-values-report",
            "attributes": {
                "statistics": ["conversions", "conversion_value"],
                "conversion_metric_id": metric_id,
                "timeframe": timeframe,
            },
        }
    }

    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Campaign report
        logger.info(f"Fetching campaign values report for metric {metric_id}...")
        camp_total = 0.0
        camp_orders = 0
        for attempt in range(3):  # Increased retry attempts
            r = await client.post(f"{base}/campaign-values-reports/", headers=headers, json=campaign_payload)
            if r.status_code == 429:  # Rate limited
                wait_time = 5.0 * (attempt + 1)  # Exponential backoff
                logger.warning(f"Rate limited on campaign report, waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            if r.status_code >= 500 and attempt < 2:
                logger.warning(f"Server error {r.status_code} on campaign report, retrying...")
                await asyncio.sleep(2.0)
                continue
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail=f"Klaviyo (campaign) error: {r.text}")
            data = r.json()
            attrs = (data.get("data") or {}).get("attributes") or {}
            for row in attrs.get("results", []) or []:
                stats = row.get("statistics") or {}
                camp_total += float(stats.get("conversion_value") or 0)
                try:
                    camp_orders += int(stats.get("conversions") or 0)
                except Exception:
                    pass
            logger.info(f"Campaign total: ${camp_total:,.2f}")
            break

        # Add delay between API calls to avoid rate limiting
        logger.info("Waiting 10 seconds before flow report to avoid rate limiting...")
        await asyncio.sleep(10.0)

        # Flow report
        logger.info(f"Fetching flow values report for metric {metric_id}...")
        flow_total = 0.0
        flow_orders = 0
        for attempt in range(3):  # Increased retry attempts
            r = await client.post(f"{base}/flow-values-reports/", headers=headers, json=flow_payload)
            if r.status_code == 429:  # Rate limited
                wait_time = 5.0 * (attempt + 1)  # Exponential backoff
                logger.warning(f"Rate limited on flow report, waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            if r.status_code >= 500 and attempt < 2:
                logger.warning(f"Server error {r.status_code} on flow report, retrying...")
                await asyncio.sleep(2.0)
                continue
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail=f"Klaviyo (flow) error: {r.text}")
            data = r.json()
            attrs = (data.get("data") or {}).get("attributes") or {}
            for row in attrs.get("results", []) or []:
                stats = row.get("statistics") or {}
                flow_total += float(stats.get("conversion_value") or 0)
                try:
                    flow_orders += int(stats.get("conversions") or 0)
                except Exception:
                    pass
            logger.info(f"Flow total: ${flow_total:,.2f}")
            break

    return {
        "metric_id": metric_id,
        "campaign_total": round(camp_total, 2),
        "flow_total": round(flow_total, 2),
        "total": round(camp_total + flow_total, 2),
        "campaign_orders": camp_orders,
        "flow_orders": flow_orders,
        "total_orders": camp_orders + flow_orders,
        "timeframe": timeframe.get("key") or timeframe,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok", "project": PROJECT_ID}


def _validate_timeframe_key(key: Optional[str]) -> str:
    allowed = {"last_7_days", "last_30_days", "last_90_days", "yesterday", "last_24_hours"}
    if not key:
        return "last_7_days"
    if key not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe_key '{key}'. Allowed: {sorted(allowed)}")
    return key


def _build_timeframe_payload(timeframe_key: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, timeframe_json: Optional[str] = None) -> Dict[str, Any]:
    # Highest precedence: explicit timeframe JSON
    if timeframe_json:
        try:
            import json as _json
            tf = _json.loads(timeframe_json)
            if not isinstance(tf, dict):
                raise ValueError("timeframe must be a JSON object")
            # Basic validation: must include 'key' OR ('start' and 'end')
            if not ("key" in tf or ("start" in tf and "end" in tf)):
                raise ValueError("timeframe JSON must include 'key' or 'start'+'end'")
            return tf
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe JSON: {e}")
    # Next: absolute start/end
    if start and end:
        return {"start": start, "end": end}
    # Fallback: key
    key = _validate_timeframe_key(timeframe_key)
    return {"key": key}


@app.get("/clients/{client_id}/revenue/last7")
async def revenue_last7(client_id: str, metric_name: str = "Placed Order", timeframe_key: Optional[str] = None, tz: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, timeframe: Optional[str] = None, recompute: Optional[bool] = False):
    # Cache key per client and metric
    tf_payload = _build_timeframe_payload(timeframe_key=timeframe_key, start=start, end=end, timeframe_json=timeframe)
    tf_cache_key = tf_payload.get("key") or f"{tf_payload.get('start','')}-{tf_payload.get('end','')}"
    cache_key = f"{client_id}:{metric_name}:{tf_cache_key}:{tz or ''}"
    cached = None if recompute else _cache_get(cache_key)
    if cached:
        return cached

    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    metric_id = resolve_metric_id(cfg, default_name=metric_name)
    if not metric_id:
        # Fallback: discover the best "Placed Order" metric id automatically
        metric_id = await _find_best_placed_order_metric(klaviyo_key)
        if not metric_id:
            raise HTTPException(status_code=400, detail="Unable to resolve a valid 'Placed Order' metric_id.")

    # For values-reports we accept either timeframe.key or absolute start/end
    result = await _sum_campaign_flow(klaviyo_key, metric_id, tf_payload)
    result.update({"client_id": client_id})
    _cache_set(cache_key, result)
    return result


@app.get("/clients/by-slug/{slug}/revenue/last7")
async def revenue_last7_by_slug(slug: str, metric_name: str = "Placed Order", timeframe_key: Optional[str] = None, tz: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, timeframe: Optional[str] = None, recompute: Optional[bool] = False):
    db = get_firestore_client()
    # Query clients by field client_slug == slug
    docs = list(db.collection("clients").where("client_slug", "==", slug).limit(2).stream())
    if not docs:
        raise HTTPException(status_code=404, detail=f"Client with slug '{slug}' not found.")
    if len(docs) > 1:
        raise HTTPException(status_code=400, detail=f"Multiple clients found for slug '{slug}'.")
    doc = docs[0]
    return await revenue_last7(doc.id, metric_name=metric_name, timeframe_key=timeframe_key, tz=tz, start=start, end=end, timeframe=timeframe, recompute=recompute)


@app.get("/clients/{client_id}/weekly/metrics")
async def weekly_metrics(client_id: str, metric_name: str = "Placed Order", timeframe_key: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, timeframe: Optional[str] = None, recompute: Optional[bool] = False):
    """Weekly metrics bundle for prompts, via Klaviyo values reports.

    Returns totals and order counts from campaign/flow values reports.
    Other UX rates (open, click, CTR, conv rate) are not computed here.
    """
    tf_payload = _build_timeframe_payload(timeframe_key=timeframe_key, start=start, end=end, timeframe_json=timeframe)
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    metric_id = resolve_metric_id(cfg, default_name=metric_name)
    if not metric_id:
        metric_id = await _find_best_placed_order_metric(klaviyo_key)
        if not metric_id:
            raise HTTPException(status_code=400, detail="Unable to resolve a valid 'Placed Order' metric_id.")
    result = await _sum_campaign_flow(klaviyo_key, metric_id, tf_payload)
    out = {
        "client_id": client_id,
        "metric_id": result["metric_id"],
        "weekly_revenue": result["total"],
        "weekly_orders": result.get("total_orders", 0),
        "campaign_revenue": result["campaign_total"],
        "campaign_orders": result.get("campaign_orders", 0),
        "flow_revenue": result["flow_total"],
        "flow_orders": result.get("flow_orders", 0),
        "timeframe": result["timeframe"],
    }
    return out


@app.get("/clients/by-slug/{slug}/weekly/metrics")
async def weekly_metrics_by_slug(slug: str, metric_name: str = "Placed Order", timeframe_key: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, timeframe: Optional[str] = None, recompute: Optional[bool] = False):
    db = get_firestore_client()
    docs = list(db.collection("clients").where("client_slug", "==", slug).limit(2).stream())
    if not docs:
        raise HTTPException(status_code=404, detail=f"Client with slug '{slug}' not found.")
    if len(docs) > 1:
        raise HTTPException(status_code=400, detail=f"Multiple clients found for slug '{slug}'.")
    return await weekly_metrics(docs[0].id, metric_name=metric_name, timeframe_key=timeframe_key, start=start, end=end, timeframe=timeframe, recompute=recompute)


@app.get("/clients/{client_id}/weekly/full")
async def weekly_full_metrics(client_id: str, metric_name: str = "Placed Order", timeframe_key: str = "last_7_days"):
    """Full weekly metrics including revenue split and email engagement rates (best effort).

    Computes:
    - weekly_revenue, weekly_orders, campaign/flow split
    - emails_sent (received), emails_opened, emails_clicked
    - open_rate (opened/sent), click_rate (clicked/opened), click_through_rate (clicked/sent)
    - conversion_rate (orders/sent), avg_order_value, revenue_per_recipient
    - week_over_week_change (revenue)
    """
    tf_payload = _build_timeframe_payload(timeframe_key=timeframe_key)
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    metric_id = resolve_metric_id(cfg, default_name=metric_name)
    if not metric_id:
        metric_id = await _find_best_placed_order_metric(klaviyo_key)
        if not metric_id:
            raise HTTPException(status_code=400, detail="Unable to resolve a valid 'Placed Order' metric_id.")

    # Revenue / orders via values reports
    rev = await _sum_campaign_flow(klaviyo_key, metric_id, tf_payload)
    weekly_revenue = float(rev.get("total", 0))
    weekly_orders = int(rev.get("total_orders", 0))

    # Engagement counts via aggregates (best-effort)
    # Resolve common metric ids
    opened_id = await _resolve_named_metric_id(klaviyo_key, "Opened Email")
    clicked_id = await _resolve_named_metric_id(klaviyo_key, "Clicked Email")
    received_id = await _resolve_named_metric_id(klaviyo_key, "Received Email")

    # Convert timeframe to absolute
    if isinstance(tf_payload, dict) and tf_payload.get("key"):
        # Calculate absolute bounds for last_7_days
        now = time.time()
        from datetime import datetime, timedelta, timezone
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=7)
        start_iso = start_dt.strftime("%Y-%m-%dT00:00:00Z")
        end_iso = end_dt.strftime("%Y-%m-%dT23:59:59Z")
    else:
        start_iso = tf_payload.get("start")
        end_iso = tf_payload.get("end")

    emails_opened = await _count_events(klaviyo_key, opened_id, start_iso, end_iso) if opened_id else 0
    emails_clicked = await _count_events(klaviyo_key, clicked_id, start_iso, end_iso) if clicked_id else 0
    emails_sent = await _count_events(klaviyo_key, received_id, start_iso, end_iso) if received_id else 0

    # Derived rates
    def pct(n, d):
        try:
            return round((n / d) * 100, 2) if d and d > 0 else 0.0
        except Exception:
            return 0.0
    open_rate = pct(emails_opened, emails_sent)
    click_through_rate = pct(emails_clicked, emails_sent)
    click_rate = pct(emails_clicked, emails_opened)
    conversion_rate = pct(weekly_orders, emails_sent)
    avg_order_value = round((weekly_revenue / weekly_orders), 2) if weekly_orders > 0 else 0.0
    revenue_per_recipient = round((weekly_revenue / emails_sent), 3) if emails_sent > 0 else 0.0

    # WoW change (previous 7 days revenue)
    from datetime import datetime, timedelta, timezone
    prev_end = datetime.now(timezone.utc) - timedelta(days=7)
    prev_start = prev_end - timedelta(days=7)
    prev_tf = {"start": prev_start.strftime("%Y-%m-%dT00:00:00Z"), "end": prev_end.strftime("%Y-%m-%dT23:59:59Z")}
    prev_rev = await _sum_campaign_flow(klaviyo_key, metric_id, prev_tf)
    prev_total = float(prev_rev.get("total", 0))
    wow_change = round(((weekly_revenue - prev_total) / prev_total) * 100, 2) if prev_total > 0 else None

    return {
        "client_id": client_id,
        "metric_id": metric_id,
        "weekly_revenue": weekly_revenue,
        "weekly_orders": weekly_orders,
        "campaign_revenue": float(rev.get("campaign_total", 0)),
        "campaign_orders": int(rev.get("campaign_orders", 0)),
        "flow_revenue": float(rev.get("flow_total", 0)),
        "flow_orders": int(rev.get("flow_orders", 0)),
        "emails_sent": emails_sent,
        "emails_opened": emails_opened,
        "emails_clicked": emails_clicked,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "click_through_rate": click_through_rate,
        "conversion_rate": conversion_rate,
        "avg_order_value": avg_order_value,
        "revenue_per_recipient": revenue_per_recipient,
        "week_over_week_change": wow_change,
        "timeframe": tf_payload.get("key") or tf_payload,
        "data_source": "klaviyo_values_reports+aggregates",
    }


@app.get("/clients/by-slug/{slug}/weekly/full")
async def weekly_full_metrics_by_slug(slug: str, metric_name: str = "Placed Order", timeframe_key: str = "last_7_days"):
    db = get_firestore_client()
    docs = list(db.collection("clients").where("client_slug", "==", slug).limit(2).stream())
    if not docs:
        raise HTTPException(status_code=404, detail=f"Client with slug '{slug}' not found.")
    if len(docs) > 1:
        raise HTTPException(status_code=400, detail=f"Multiple clients found for slug '{slug}'.")
    return await weekly_full_metrics(docs[0].id, metric_name=metric_name, timeframe_key=timeframe_key)


# --- Campaign and Flow endpoints ---
@app.get("/clients/{client_id}/campaigns")
async def get_campaigns(
    client_id: str, 
    timeframe_key: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 50,
    recompute: Optional[bool] = False
):
    """Get campaign performance data for a client.
    
    Returns campaign metrics including sends, opens, clicks, and revenue.
    """
    # Build cache key
    tf_payload = _build_timeframe_payload(timeframe_key=timeframe_key, start=start, end=end)
    tf_cache_key = tf_payload.get("key") or f"{tf_payload.get('start','')}-{tf_payload.get('end','')}"
    cache_key = f"campaigns:{client_id}:{tf_cache_key}"
    
    cached = None if recompute else _cache_get(cache_key)
    if cached:
        return cached
    
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    # Get campaigns from Klaviyo API
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    # Build filter - channel is required by Klaviyo API
    filter_params = ["equals(messages.channel,'email')"]  # Default to email campaigns
    
    if tf_payload.get("start"):
        filter_params.append(f"greater-or-equal(scheduled_at,{tf_payload['start']}T00:00:00)")
    if tf_payload.get("end"):
        filter_params.append(f"less-or-equal(scheduled_at,{tf_payload['end']}T23:59:59)")
    
    params = {
        "fields[campaign]": "name,status,scheduled_at,created_at,updated_at",
        "filter": "and(" + ",".join(filter_params) + ")"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get campaigns list
            response = await client.get(
                "https://a.klaviyo.com/api/campaigns",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            campaigns_data = response.json()
            
            # Process campaign data
            campaigns = []
            for campaign in campaigns_data.get("data", []):
                campaign_info = {
                    "id": campaign.get("id"),
                    "name": campaign.get("attributes", {}).get("name"),
                    "status": campaign.get("attributes", {}).get("status"),
                    "send_time": campaign.get("attributes", {}).get("scheduled_at"),
                    "created": campaign.get("attributes", {}).get("created_at"),
                    "updated": campaign.get("attributes", {}).get("updated_at")
                }
                
                # Try to get campaign metrics
                try:
                    metrics_response = await client.get(
                        f"https://a.klaviyo.com/api/campaign-values-reports",
                        headers=headers,
                        params={
                            "filter": f"equals(campaign_id,{campaign['id']})",
                            "fields[campaign-values-report]": "clicks_unique,opens_unique,deliveries,revenue"
                        }
                    )
                    if metrics_response.status_code == 200:
                        metrics_data = metrics_response.json()
                        if metrics_data.get("data"):
                            metrics = metrics_data["data"][0].get("attributes", {})
                            campaign_info.update({
                                "deliveries": metrics.get("deliveries", 0),
                                "opens": metrics.get("opens_unique", 0),
                                "clicks": metrics.get("clicks_unique", 0),
                                "revenue": metrics.get("revenue", 0)
                            })
                except Exception as e:
                    logger.warning(f"Failed to get metrics for campaign {campaign['id']}: {e}")
                
                campaigns.append(campaign_info)
            
            result = {
                "campaigns": campaigns,
                "total": len(campaigns),
                "timeframe": tf_payload,
                "client_id": client_id
            }
            
            _cache_set(cache_key, result)
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Klaviyo API error for campaigns: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")
        except Exception as e:
            logger.error(f"Failed to get campaigns: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/clients/{client_id}/flows")
async def get_flows(
    client_id: str,
    limit: int = 50,
    recompute: Optional[bool] = False
):
    """Get flow performance data for a client.
    
    Returns flow metrics including triggers, completions, and revenue.
    """
    # Build cache key
    cache_key = f"flows:{client_id}"
    
    cached = None if recompute else _cache_get(cache_key)
    if cached:
        return cached
    
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    # Get flows from Klaviyo API
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[flow]": "name,status,created,updated",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get flows list
            response = await client.get(
                "https://a.klaviyo.com/api/flows",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            flows_data = response.json()
            
            # Process flow data
            flows = []
            for flow in flows_data.get("data", []):
                flow_info = {
                    "id": flow.get("id"),
                    "name": flow.get("attributes", {}).get("name"),
                    "status": flow.get("attributes", {}).get("status"),
                    "created": flow.get("attributes", {}).get("created"),
                    "updated": flow.get("attributes", {}).get("updated")
                }
                
                # Try to get flow metrics (if available)
                try:
                    metrics_response = await client.get(
                        f"https://a.klaviyo.com/api/flow-values-reports",
                        headers=headers,
                        params={
                            "filter": f"equals(flow_id,{flow['id']})",
                            "fields[flow-values-report]": "clicks_unique,opens_unique,deliveries,revenue"
                        }
                    )
                    if metrics_response.status_code == 200:
                        metrics_data = metrics_response.json()
                        if metrics_data.get("data"):
                            metrics = metrics_data["data"][0].get("attributes", {})
                            flow_info.update({
                                "deliveries": metrics.get("deliveries", 0),
                                "opens": metrics.get("opens_unique", 0),
                                "clicks": metrics.get("clicks_unique", 0),
                                "revenue": metrics.get("revenue", 0)
                            })
                except Exception as e:
                    logger.warning(f"Failed to get metrics for flow {flow['id']}: {e}")
                
                flows.append(flow_info)
            
            result = {
                "flows": flows,
                "total": len(flows),
                "client_id": client_id
            }
            
            _cache_set(cache_key, result)
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Klaviyo API error for flows: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")
        except Exception as e:
            logger.error(f"Failed to get flows: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# --- Account Management Endpoints ---
@app.get("/account")
async def get_account(api_key: Optional[str] = None):
    """Get account details for the current Klaviyo account."""
    if not api_key:
        # Try to get from first client as fallback
        db = get_firestore_client()
        docs = list(db.collection("clients").limit(1).stream())
        if docs:
            cfg = docs[0].to_dict()
            api_key = resolve_klaviyo_key(cfg)
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required")
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/accounts",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Profile Management Endpoints ---
@app.get("/clients/{client_id}/profiles")
async def get_profiles(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    filter: Optional[str] = None,
    sort: Optional[str] = None
):
    """Get profiles for a client with optional filtering and sorting."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[profile]": "email,first_name,last_name,phone_number,created,updated"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    if filter:
        params["filter"] = filter
    if sort:
        params["sort"] = sort
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/profiles",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.get("/clients/{client_id}/profiles/{profile_id}")
async def get_profile(client_id: str, profile_id: str):
    """Get a specific profile by ID."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"https://a.klaviyo.com/api/profiles/{profile_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.post("/clients/{client_id}/profiles")
async def create_profile(client_id: str, profile_data: Dict[str, Any]):
    """Create a new profile."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://a.klaviyo.com/api/profiles",
                headers=headers,
                json=profile_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.patch("/clients/{client_id}/profiles/{profile_id}")
async def update_profile(client_id: str, profile_id: str, profile_data: Dict[str, Any]):
    """Update an existing profile."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.patch(
                f"https://a.klaviyo.com/api/profiles/{profile_id}",
                headers=headers,
                json=profile_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Event Management Endpoints ---
@app.get("/clients/{client_id}/events")
async def get_events(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    filter: Optional[str] = None,
    sort: Optional[str] = None
):
    """Get events for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[event]": "metric,profile,timestamp,event_properties"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    if filter:
        params["filter"] = filter
    if sort:
        params["sort"] = sort
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/events",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.post("/clients/{client_id}/events")
async def create_event(client_id: str, event_data: Dict[str, Any]):
    """Create a new event."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://a.klaviyo.com/api/events",
                headers=headers,
                json=event_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Catalog Management Endpoints ---
@app.get("/clients/{client_id}/catalog/items")
async def get_catalog_items(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    filter: Optional[str] = None
):
    """Get catalog items for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[catalog-item]": "external_id,title,description,price,url,image_full_url"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    if filter:
        params["filter"] = filter
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/catalog-items",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.get("/clients/{client_id}/catalog/categories")
async def get_catalog_categories(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
):
    """Get catalog categories for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[catalog-category]": "external_id,name"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/catalog-categories",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Metrics Endpoints ---
@app.get("/clients/{client_id}/metrics")
async def get_metrics(
    client_id: str,
    limit: int = 100,
    cursor: Optional[str] = None
):
    """Get all available metrics for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[metric]": "name,created,updated,integration"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/metrics",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.get("/clients/{client_id}/metrics/{metric_id}/aggregates")
async def get_metric_aggregates(
    client_id: str,
    metric_id: str,
    start: str,
    end: str,
    interval: str = "day",
    measurement: str = "unique"
):
    """Get aggregated data for a specific metric."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "revision": "2024-10-15"
    }
    
    data = {
        "data": {
            "type": "metric-aggregate",
            "attributes": {
                "metric_id": metric_id,
                "measurements": [measurement],
                "interval": interval,
                "filter": [f"datetime_range(timestamp, {start}, {end})"]
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "https://a.klaviyo.com/api/metric-aggregates",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Segments Endpoints ---
@app.get("/clients/{client_id}/segments")
async def get_segments(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
):
    """Get segments for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[segment]": "name,created,updated,is_active"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/segments",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.get("/clients/{client_id}/segments/{segment_id}")
async def get_segment(client_id: str, segment_id: str):
    """Get a specific segment by ID."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"https://a.klaviyo.com/api/segments/{segment_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Lists Endpoints ---
@app.get("/clients/{client_id}/lists")
async def get_lists(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None
):
    """Get lists for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[list]": "name,created,updated"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/lists",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.get("/clients/{client_id}/lists/{list_id}")
async def get_list(client_id: str, list_id: str):
    """Get a specific list by ID."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"https://a.klaviyo.com/api/lists/{list_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Templates Endpoints ---
@app.get("/clients/{client_id}/templates")
async def get_templates(
    client_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    filter: Optional[str] = None
):
    """Get email templates for a client."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    params = {
        "page[size]": limit,
        "fields[template]": "name,created,updated,html,text"
    }
    
    if cursor:
        params["page[cursor]"] = cursor
    if filter:
        params["filter"] = filter
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://a.klaviyo.com/api/templates",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


@app.get("/clients/{client_id}/templates/{template_id}")
async def get_template(client_id: str, template_id: str):
    """Get a specific template by ID."""
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    
    headers = {
        "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
        "Accept": "application/json",
        "revision": "2024-10-15"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"https://a.klaviyo.com/api/templates/{template_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")


# --- Admin/Diagnostics endpoints ---
@app.post("/admin/cache/clear")
def admin_cache_clear(client_id: str, timeframe_key: Optional[str] = None, tz: Optional[str] = None, metric_name: str = "Placed Order"):
    tf_key = _validate_timeframe_key(timeframe_key)
    keys = [
        f"{client_id}:{metric_name}:{tf_key}:{tz or ''}",
        f"{client_id}:{metric_name}:{tf_key}:",
    ]
    removed = 0
    for k in keys:
        if _CACHE.pop(k, None):
            removed += 1
    return {"removed": removed}


@app.post("/admin/metric/detect")
async def admin_metric_detect(client_id: str):
    cfg = resolve_client_config(client_id)
    klaviyo_key = resolve_klaviyo_key(cfg)
    mid = await _find_best_placed_order_metric(klaviyo_key)
    if not mid:
        raise HTTPException(status_code=400, detail="No viable 'Placed Order' metric found via detection.")
    return {"client_id": client_id, "detected_metric_id": mid}


@app.post("/admin/metric/lock")
def admin_metric_lock(client_id: str, metric_id: str):
    db = get_firestore_client()
    ref = db.collection("clients").document(client_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Client not found")
    ref.update({"placed_order_metric_id": metric_id})
    # Evict cache for this client
    for k in list(_CACHE.keys()):
        if k.startswith(f"{client_id}:"):
            _CACHE.pop(k, None)
    return {"client_id": client_id, "locked_metric_id": metric_id}


# --- Prompt Management (Firestore: collection mcp_prompts) ---
def _prompt_ref(name: str):
    return get_firestore_client().collection("mcp_prompts").document(name)


@app.get("/admin/prompts")
def admin_prompts_list():
    db = get_firestore_client()
    col = db.collection("mcp_prompts")
    items = []
    for doc in col.stream():
        d = doc.to_dict() or {}
        items.append({
            "name": doc.id,
            "description": d.get("description"),
            "variables": d.get("variables", []),
            "enabled": d.get("enabled", True),
            "updated_at": str(d.get("updated_at")) if d.get("updated_at") else None,
            "tool": d.get("tool"),
            "defaults": d.get("defaults", {}),
            "tags": d.get("tags", []),
        })
    return {"items": items}


@app.get("/admin/prompts/{name}")
def admin_prompts_get(name: str):
    ref = _prompt_ref(name)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Prompt not found")
    d = doc.to_dict() or {}
    d["name"] = name
    return d


from fastapi import Body


@app.post("/admin/prompts")
def admin_prompts_upsert(payload: Dict[str, Any] = Body(...)):
    name = payload.get("name")
    if not name or not isinstance(name, str):
        raise HTTPException(status_code=400, detail="name is required")
    ref = _prompt_ref(name)
    data = {
        "description": payload.get("description"),
        "content": payload.get("content", ""),
        "variables": payload.get("variables", []),
        "tool": payload.get("tool", "get_revenue_last7"),
        "defaults": payload.get("defaults", {}),
        "enabled": payload.get("enabled", True),
        "tags": payload.get("tags", []),
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    ref.set(data, merge=True)
    out = ref.get().to_dict() or {}
    out["name"] = name
    return out


@app.delete("/admin/prompts/{name}")
def admin_prompts_delete(name: str):
    ref = _prompt_ref(name)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Prompt not found")
    ref.delete()
    return {"deleted": name}


def _render_template(text: str, variables: Dict[str, Any]) -> str:
    # Minimal {{ var }} replacement
    import re
    def repl(m):
        key = m.group(1).strip()
        return str(variables.get(key, m.group(0)))
    return re.sub(r"\{\{\s*([^}]+)\s*\}\}", repl, text or "")


@app.post("/admin/prompts/{name}/test")
async def admin_prompts_test(name: str, payload: Dict[str, Any] = Body(...)):
    ref = _prompt_ref(name)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt = doc.to_dict() or {}
    tool = prompt.get("tool", "get_revenue_last7")
    content = prompt.get("content", "")
    defaults = prompt.get("defaults", {}) or {}
    variables = {**defaults, **(payload.get("variables") or {})}
    rendered = _render_template(content, variables)

    # Build tool args from params + variables
    params = payload.get("params") or {}
    client_id = payload.get("client_id")
    slug = payload.get("slug")

    import time as _time
    t0 = _time.monotonic()
    if tool == "get_revenue_last7":
        # Route to internal revenue function
        if client_id:
            result = await revenue_last7(
                client_id=client_id,
                timeframe_key=params.get("timeframe_key"),
                tz=params.get("tz"),
                start=params.get("start"),
                end=params.get("end"),
                timeframe=params.get("timeframe"),
                recompute=bool(params.get("recompute")),
            )
            tool_args = {"client_id": client_id, **params}
        elif slug:
            result = await revenue_last7_by_slug(
                slug=slug,
                timeframe_key=params.get("timeframe_key"),
                tz=params.get("tz"),
                start=params.get("start"),
                end=params.get("end"),
                timeframe=params.get("timeframe"),
                recompute=bool(params.get("recompute")),
            )
            tool_args = {"slug": slug, **params}
        else:
            raise HTTPException(status_code=400, detail="Provide client_id or slug for test")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported tool '{tool}' in prompt")
    latency = int((_time.monotonic() - t0) * 1000)
    return {
        "name": name,
        "rendered_prompt": rendered,
        "tool": tool,
        "tool_args": tool_args,
        "tool_result": result,
        "latency_ms": latency,
    }


# --- MCP Management (OpenAPI MCP for Revenue API and Firebase MCP) ---
class MCPProcess:
    def __init__(self, cmd: list[str], env: Optional[Dict[str, str]] = None):
        self.cmd = cmd
        self.env = env or os.environ.copy()
        self.proc: Optional[subprocess.Popen] = None
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                return
            self.proc = subprocess.Popen(
                self.cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env,
                bufsize=1,
            )
            # Initialize MCP session
            self._send({
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "admin-mcp", "version": "1.0"}}
            })
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_response=False)

    def stop(self):
        with self.lock:
            if self.proc:
                try:
                    self.proc.terminate()
                except Exception:
                    pass
                self.proc = None

    def status(self) -> str:
        p = self.proc
        if not p:
            return "stopped"
        return "running" if p.poll() is None else f"exited({p.poll()})"

    def _send(self, obj: Dict[str, Any], expect_response: bool = True) -> Optional[Dict[str, Any]]:
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("MCP process not running")
        self.proc.stdin.write(_json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        if not expect_response:
            return None
        line = self.proc.stdout.readline()
        return _json.loads(line) if line else None

    def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            if not self.proc or self.proc.poll() is not None:
                self.start()
            self.proc.stdin.write(_json.dumps(request) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("No response from MCP server")
            return _json.loads(line)


_mcp_instances: Dict[str, MCPProcess] = {}


def _get_mcp_instance(kind: str) -> MCPProcess:
    if kind not in _mcp_instances:
        if kind == "openapi_revenue":
            cmd = [
                "npx", "@modelcontextprotocol/openapi",
                "--spec", os.path.join("services", "klaviyo_api", "openapi.yaml"),
                "--server.url", os.environ.get("REVENUE_API_BASE", "http://localhost:9090"),
            ]
            _mcp_instances[kind] = MCPProcess(cmd)
        elif kind == "performance_openapi":
            cmd = [
                "npx", "@modelcontextprotocol/openapi",
                "--spec", os.path.join("services", "performance_api", "openapi.yaml"),
                "--server.url", os.environ.get("PERFORMANCE_API_BASE", "http://localhost:9091"),
            ]
            _mcp_instances[kind] = MCPProcess(cmd)
        elif kind == "firebase":
            # Firebase CLI MCP server (requires firebase CLI installed and authed)
            cmd = [os.environ.get("FIREBASE_MCP_CMD", "firebase"), "mcp"]
            _mcp_instances[kind] = MCPProcess(cmd)
        elif kind == "ai_models_openapi":
            cmd = [
                "npx", "@modelcontextprotocol/openapi",
                "--spec", os.path.join("services", "ai_models_api", "openapi.yaml"),
                "--server.url", os.environ.get("AI_MODELS_API_BASE", "http://localhost:8000"),
            ]
            _mcp_instances[kind] = MCPProcess(cmd)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown MCP kind '{kind}'")
    return _mcp_instances[kind]


@app.get("/admin/mcp/status")
def admin_mcp_status():
    return {k: v.status() for k, v in _mcp_instances.items()}


@app.post("/admin/mcp/start")
def admin_mcp_start(kind: str = Body(..., embed=True)):
    inst = _get_mcp_instance(kind)
    inst.start()
    return {"kind": kind, "status": inst.status()}


@app.post("/admin/mcp/stop")
def admin_mcp_stop(kind: str = Body(..., embed=True)):
    inst = _get_mcp_instance(kind)
    inst.stop()
    return {"kind": kind, "status": inst.status()}


@app.post("/admin/mcp/call")
def admin_mcp_call(kind: str = Body(...), request: Dict[str, Any] = Body(...)):
    inst = _get_mcp_instance(kind)
    try:
        resp = inst.call(request)
        return {"response": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP call failed: {e}")


@app.post("/admin/mcp/tools/call")
def admin_mcp_tools_call(kind: str = Body(...), name: str = Body(...), arguments: Dict[str, Any] = Body(default_factory=dict)):
    inst = _get_mcp_instance(kind)
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    try:
        resp = inst.call(req)
        return {"response": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCP tool call failed: {e}")


# --- Smart router: determine Firebase MCP vs OpenAPI MCP automatically ---
_tools_cache: Dict[str, set[str]] = {"openapi_revenue": set(), "performance_openapi": set(), "firebase": set()}


def _list_tools(kind: str) -> set[str]:
    try:
        inst = _get_mcp_instance(kind)
        inst.start()
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        resp = inst.call(req)
        # Expect a result structure; be tolerant of wrappers
        text = _json.dumps(resp)
        names = set()
        # naive parse for tool names in response
        try:
            # Find name occurrences
            data = resp.get("result") or resp.get("response") or resp
            if isinstance(data, dict):
                tools = data.get("tools") or data.get("result") or []
            else:
                tools = []
            for t in tools:
                n = (t.get("name") if isinstance(t, dict) else None)
                if n:
                    names.add(n)
        except Exception:
            pass
        if not names:
            # fallback: try to extract with regex from raw
            import re as _re
            for m in _re.finditer(r'"name"\s*:\s*"([^"]+)"', text):
                names.add(m.group(1))
        _tools_cache[kind] = names
        return names
    except Exception:
        return set()


@app.post("/admin/mcp/tools/smart_call")
def admin_mcp_tools_smart_call(name: str = Body(...), arguments: Dict[str, Any] = Body(default_factory=dict), prefer: Optional[str] = Body(default=None)):
    # If user prefers a specific backend, honor it
    if prefer in {"openapi_revenue", "performance_openapi", "firebase"}:
        return admin_mcp_tools_call(kind=prefer, name=name, arguments=arguments)

    # Heuristics: route by known path prefixes
    if name.startswith("GET /clients/"):
        return admin_mcp_tools_call(kind="openapi_revenue", name=name, arguments=arguments)
    if name.startswith("GET /clients/by-slug/"):
        return admin_mcp_tools_call(kind="openapi_revenue", name=name, arguments=arguments)
    if name.startswith("GET /api/ai-models/") or name.startswith("POST /api/ai-models/"):
        return admin_mcp_tools_call(kind="ai_models_openapi", name=name, arguments=arguments)
    if name.startswith("/jobs/") or name.upper().startswith("POST /JOBS/"):
        return admin_mcp_tools_call(kind="performance_openapi", name=name, arguments=arguments)

    # Discover tools from each backend and route to one that contains the tool
    for kind in ("openapi_revenue", "performance_openapi", "firebase"):
        names = _tools_cache.get(kind) or _list_tools(kind)
        if name in names:
            return admin_mcp_tools_call(kind=kind, name=name, arguments=arguments)

    # Fallback: try firebase then openapi_revenue
    try:
        return admin_mcp_tools_call(kind="firebase", name=name, arguments=arguments)
    except HTTPException:
        return admin_mcp_tools_call(kind="openapi_revenue", name=name, arguments=arguments)
