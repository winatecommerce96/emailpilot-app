import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise RuntimeError("GOOGLE_CLOUD_PROJECT must be set")

REVENUE_API_BASE = os.environ.get("REVENUE_API_BASE", "http://localhost:9090")

app = FastAPI(title="Performance Jobs (Test)", description="Weekly/Monthly performance vs goals stored in Firestore")

class JobRequest(BaseModel):
    client_id: Optional[str] = None
    slug: Optional[str] = None

def get_db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID)

def month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")

def iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

async def fetch_revenue(client_id: Optional[str], slug: Optional[str], timeframe_key: Optional[str] = None,
                        start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
    params = {"recompute": "true"}
    if timeframe_key:
        params["timeframe_key"] = timeframe_key
    if start and end:
        params["start"] = start
        params["end"] = end
    
    path = (
        f"/clients/{client_id}/weekly/metrics" if client_id
        else f"/clients/by-slug/{slug}/weekly/metrics"
    )
    
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(REVENUE_API_BASE + path, params=params)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=f"Revenue API error: {r.text}")
        return r.json()

def read_goal(db: firestore.Client, client_id: str, year: int, month: int) -> Optional[float]:
    goals_ref = db.collection("clients").document(client_id).collection("goals").document(f"{year:04d}-{month:02d}")
    doc = goals_ref.get()
    if doc.exists:
        data = doc.to_dict() or {}
        val = data.get("monthly_goal")
        try:
            return float(val) if val is not None else None
        except Exception:
            return None
    return None

def write_performance(db: firestore.Client, client_id: str, scope: str, payload: Dict[str, Any]) -> str:
    col = db.collection("clients").document(client_id).collection("performance")
    doc_id = payload.get("doc_id") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    col.document(doc_id).set({
        "scope": scope,
        **payload
    }, merge=True)
    return doc_id

@app.get("/healthz")
def healthz():
    return {"status": "ok", "project": PROJECT_ID, "revenue_api": REVENUE_API_BASE}

@app.post("/jobs/weekly")
async def job_weekly(req: JobRequest):
    if not req.client_id and not req.slug:
        raise HTTPException(status_code=400, detail="Provide client_id or slug")
    
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start_dt = now - timedelta(days=7)
    
    revenue = await fetch_revenue(req.client_id, req.slug, start=iso(start_dt), end=iso(now))
    
    db = get_db()
    client_id = req.client_id
    if not client_id and req.slug:
        docs = list(db.collection("clients").where("client_slug", "==", req.slug).limit(1).stream())
        if not docs:
            raise HTTPException(status_code=404, detail="Client slug not found in Firestore")
        client_id = docs[0].id

    payload = {
        "doc_id": f"weekly-{now.strftime('%Y-%m-%d')}",
        "client_id": client_id,
        "metric_id": revenue.get("metric_id"),
        "campaign_total": revenue.get("campaign_total", 0.0),
        "flow_total": revenue.get("flow_total", 0.0),
        "total": revenue.get("total", 0.0),
        "timeframe": {"start": iso(start_dt), "end": iso(now)},
        "created_at": iso(now),
    }
    doc_id = write_performance(db, client_id, "weekly", payload)
    return {"status": "ok", "doc_id": doc_id, "result": payload}

@app.post("/jobs/monthly")
async def job_monthly(req: JobRequest, month: Optional[str] = None):
    if not req.client_id and not req.slug:
        raise HTTPException(status_code=400, detail="Provide client_id or slug")
    
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    
    if month:
        try:
            year, mon = map(int, month.split("-"))
            start_dt = datetime(year, mon, 1, tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid month; expected YYYY-MM")
    else:
        start_dt = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    if start_dt.year == now.year and start_dt.month == now.month:
        end_dt = now
    else:
        next_month = (start_dt.month % 12) + 1
        next_year = start_dt.year + (1 if start_dt.month == 12 else 0)
        end_dt = datetime(next_year, next_month, 1, tzinfo=timezone.utc)

    revenue = await fetch_revenue(req.client_id, req.slug, start=iso(start_dt), end=iso(end_dt))
    
    db = get_db()
    client_id = req.client_id
    if not client_id and req.slug:
        docs = list(db.collection("clients").where("client_slug", "==", req.slug).limit(1).stream())
        if not docs:
            raise HTTPException(status_code=404, detail="Client slug not found in Firestore")
        client_id = docs[0].id
        
    goal = read_goal(db, client_id, start_dt.year, start_dt.month)
    total = float(revenue.get("total", 0.0))
    progress = (total / goal * 100.0) if goal and goal > 0 else None
    
    payload = {
        "doc_id": f"monthly-{start_dt.strftime('%Y-%m')}",
        "client_id": client_id,
        "metric_id": revenue.get("metric_id"),
        "campaign_total": revenue.get("campaign_total", 0.0),
        "flow_total": revenue.get("flow_total", 0.0),
        "total": total,
        "goal": goal,
        "progress_percent": progress,
        "timeframe": {"start": iso(start_dt), "end": iso(end_dt)},
        "created_at": iso(now),
    }
    doc_id = write_performance(db, client_id, "monthly", payload)
    return {"status": "ok", "doc_id": doc_id, "result": payload}