# app/api/performance.py
"""
Performance API
- Month-to-date (MTD) metrics with optional Klaviyo enrichment
- Historical & comparison views (mocked but consistent schema)
- Simple forecast
- Weekly/Monthly report triggers (placeholders to wire into jobs)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
# Firestore deps (project uses Firestore, not SQLAlchemy)
try:
    from app.deps.firestore import get_db  # preferred thin wrapper
except Exception:
    from app.services.firestore_client import get_firestore_client as get_db  # type: ignore

# Import KlaviyoClient and Secret Manager services
from app.services.klaviyo_client import KlaviyoClient
try:
    from app.services.secret_manager import get_secret_manager
except Exception:
    get_secret_manager = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/performance", tags=["performance"])


def _resolve_client_key(db, client_id: str) -> Optional[str]:
    """
    Resolve a per-client Klaviyo API key via:
      1) Client's klaviyo_secret_name in Secret Manager
      2) Legacy fallback to direct fields (temporary)
    
    Returns None if client not found, database error, or no API key configured.
    """
    if not client_id:
        logger.warning("Empty client_id provided to _resolve_client_key")
        return None
    
    if not db:
        logger.error("Database connection is None")
        return None
    
    try:
        snap = db.collection("clients").document(client_id).get()
        if not snap.exists:
            logger.warning(f"Client document not found: {client_id}")
            return None
        
        data = snap.to_dict() or {}
        
        # First try secret manager with client's specified secret name
        if get_secret_manager:
            secret_name = data.get("klaviyo_secret_name") or f"klaviyo-api-key-{client_id}"
            try:
                secret_manager = get_secret_manager()
                key = secret_manager.get_secret(secret_name)
                if key and key.strip():
                    logger.debug(f"Successfully retrieved API key from Secret Manager for client {client_id}")
                    return key.strip()
            except Exception as e:
                logger.debug(f"Secret Manager lookup failed for {secret_name}: {e}")
        
        # Temporary legacy fallback to direct fields
        legacy_key = data.get("klaviyo_api_key") or data.get("klaviyo_private_key")
        if legacy_key and legacy_key.strip():
            logger.warning(f"Client {client_id} using legacy plaintext key - migrate to Secret Manager")
            return legacy_key.strip()
        
        logger.info(f"No Klaviyo API key found for client {client_id}")
        return None
            
    except Exception as e:
        logger.error(f"Key resolution failed for client {client_id}: {e}")
        # Re-raise database connection errors so the caller can handle them appropriately
        if "Permission denied" in str(e) or "CONSUMER_INVALID" in str(e):
            raise
        return None


def _safe_int_from_client_id(client_id: Union[str, int]) -> int:
    try:
        return int(str(client_id).replace("client_", "").replace("demo_", ""))
    except (ValueError, TypeError):
        return hash(str(client_id)) % 100


def _get_client_klaviyo_account_id(db, client_id: str) -> Optional[str]:
    """
    Try to read a client's Klaviyo account id from Firestore.
    Adjust field names to your actual schema if needed.
    """
    try:
        snap = db.collection("clients").document(client_id).get()
        if snap.exists:
            data = snap.to_dict() or {}
            return (
                data.get("klaviyo_account_id")
                or data.get("klaviyoAccountId")
                or data.get("metric_id")  # sometimes used for integrations
            )
    except Exception as e:
        logger.debug("Account id lookup failed for %s: %s", client_id, e)
    return None


async def _fetch_klaviyo_summary_with_client(
    klaviyo_client: KlaviyoClient,
    start_iso: str,
    end_iso: str,
) -> Dict[str, Any]:
    """
    Fetch Klaviyo summary using the KlaviyoClient service.
    """
    try:
        return await klaviyo_client.mtd_summary()
    except Exception as e:
        logger.error(f"Klaviyo API fetch failed: {e}")
        raise


def _mock_mtd(client_id: Union[str, int]) -> Dict[str, Any]:
    id_num = _safe_int_from_client_id(client_id)
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    days_in_month = (datetime(now.year, now.month + 1, 1) - timedelta(days=1)).day if now.month < 12 else 31
    days_passed = now.day
    days_remaining = max(0, days_in_month - days_passed)

    base_revenue = 30000 + (id_num * 500)
    base_orders = 150 + (id_num * 5)

    return {
        "period": {
            "start": start_of_month.isoformat(),
            "end": now.isoformat(),
            "days_passed": days_passed,
            "days_remaining": days_remaining,
            "days_in_month": days_in_month,
            "progress_percentage": (days_passed / days_in_month) * 100 if days_in_month else 0,
        },
        "revenue": {
            "mtd": base_revenue,
            "daily_average": base_revenue / days_passed if days_passed > 0 else 0,
            "projected_eom": (base_revenue / max(1, days_passed) * days_in_month),
            "last_30_days": base_revenue * 1.2,
            "yoy_change": 12.5 + (id_num % 20),
        },
        "orders": {
            "mtd": base_orders,
            "daily_average": base_orders / days_passed if days_passed > 0 else 0,
            "average_order_value": (base_revenue / base_orders) if base_orders > 0 else 0,
            "conversion_rate": 2.5 + (id_num % 5) * 0.1,
        },
        "email_performance": {
            "emails_sent": 10000 + (id_num * 100),
            "unique_opens": 2800 + (id_num * 30),
            "unique_clicks": 560 + (id_num * 6),
            "open_rate": 28.0 + (id_num % 10),
            "click_rate": 5.6 + (id_num % 3),
            "click_to_open_rate": 20.0 + (id_num % 8),
            "bounced": 30 + (id_num % 20),
            "unsubscribed": 8 + (id_num % 10),
        },
        "campaigns": {
            "sent": 6 + (id_num % 5),
            "scheduled": 2 + (id_num % 3),
            "draft": 1 + (id_num % 2),
            "best_performer": {
                "name": f"Campaign {id_num % 10 + 1}",
                "revenue": base_revenue * 0.3,
                "open_rate": 32.5 + (id_num % 8),
                "click_rate": 7.2 + (id_num % 3),
            },
        },
        "flows": {
            "active": 8 + (id_num % 6),
            "total_revenue": base_revenue * 0.6,
            "top_performer": {
                "name": "Abandoned Cart",
                "revenue": base_revenue * 0.35,
                "messages_sent": 400 + (id_num * 10),
            },
        },
        "segments": {
            "vip_customers": 800 + (id_num * 20),
            "engaged_30_days": 3200 + (id_num * 50),
            "at_risk": 450 + (id_num * 8),
            "win_back_eligible": 280 + (id_num * 5),
        },
    }


@router.get("/mtd/{client_id}")
async def get_mtd_performance(client_id: Union[str, int]) -> Dict[str, Any]:
    """
    Month-to-date performance for a client.
    Uses per-client Klaviyo keys if configured; otherwise returns mock data.
    """
    client_id_str = str(client_id)
    mtd = _mock_mtd(client_id)
    data_source = "mock"
    error_details = None

    try:
        # Try to get database connection
        try:
            db = get_db()
        except Exception as db_error:
            logger.error(f"Database connection failed: {db_error}")
            error_details = f"Database connection error: {str(db_error)}"
            db = None
        
        # Try to resolve per-client Klaviyo key
        api_key = _resolve_client_key(db, client_id_str) if db else None
        
        if api_key and api_key.strip():
            try:
                # Use KlaviyoClient for real API calls
                klaviyo_client = KlaviyoClient(api_key)
                real = await _fetch_klaviyo_summary_with_client(
                    klaviyo_client,
                    start_iso=mtd["period"]["start"],
                    end_iso=mtd["period"]["end"],
                )
                
                # Merge real data into mock structure
                mtd["revenue"]["mtd"] = real.get("revenue", mtd["revenue"]["mtd"])
                mtd["orders"]["mtd"] = real.get("orders", mtd["orders"]["mtd"])
                ep = mtd["email_performance"]
                ep["emails_sent"] = real.get("emails_sent", ep["emails_sent"])
                ep["unique_opens"] = real.get("unique_opens", ep["unique_opens"])
                ep["unique_clicks"] = real.get("unique_clicks", ep["unique_clicks"])
                ep["bounced"] = real.get("bounced", ep["bounced"])
                ep["unsubscribed"] = real.get("unsubscribed", ep["unsubscribed"])
                
                # Recalculate derived metrics with real data
                if ep["emails_sent"] > 0:
                    ep["open_rate"] = (ep["unique_opens"] / ep["emails_sent"]) * 100
                    ep["click_rate"] = (ep["unique_clicks"] / ep["emails_sent"]) * 100
                if ep["unique_opens"] > 0:
                    ep["click_to_open_rate"] = (ep["unique_clicks"] / ep["unique_opens"]) * 100
                
                if mtd["orders"]["mtd"] > 0:
                    mtd["orders"]["average_order_value"] = mtd["revenue"]["mtd"] / mtd["orders"]["mtd"]
                
                data_source = "klaviyo"
                logger.info(f"Successfully enriched MTD data for client {client_id_str} with Klaviyo data")
                
            except ValueError as ve:
                logger.error(f"Invalid Klaviyo API key for client {client_id_str}: {ve}")
                error_details = f"Invalid API key configuration: {str(ve)}"
                data_source = "mock"
            except Exception as e:
                logger.error(f"Klaviyo enrichment failed for client {client_id_str}: {e}")
                error_details = f"Klaviyo API error: {str(e)}"
                data_source = "mock"
        else:
            logger.info(f"No Klaviyo API key configured for client {client_id_str}, returning mock data")
            
    except Exception as e:
        # Handle database connection errors or other infrastructure issues
        logger.error(f"Database or infrastructure error for client {client_id_str}: {e}")
        error_details = f"Infrastructure error: {str(e)}"
        data_source = "mock"

    response = {
        "client_id": client_id_str,
        "mtd": mtd,
        "ytd": {
            "revenue": mtd["revenue"]["mtd"] * 8.5,
            "orders": mtd["orders"]["mtd"] * 8.5,
            "emails_sent": mtd["email_performance"]["emails_sent"] * 8,
            "campaigns_sent": mtd["campaigns"]["sent"] * 8,
        },
        "data_source": data_source,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Include error details if any occurred
    if error_details:
        response["error_details"] = error_details
        response["warning"] = "Returning mock data due to configuration or connectivity issues"
    
    return response


@router.get("/historical/{client_id}")
async def get_historical_performance(
    client_id: Union[str, int],
    months: int = Query(default=12, ge=1, le=36, description="Number of months of historical data"),
) -> Dict[str, Any]:
    """Synthetic historical series (swap with your stored history when ready)."""
    id_num = _safe_int_from_client_id(client_id)
    now = datetime.now()
    series: List[Dict[str, Any]] = []

    for i in range(months):
        month_date = now - timedelta(days=30 * i)
        base_revenue = 35000 + (id_num * 400)
        series.append(
            {
                "year": month_date.year,
                "month": month_date.month,
                "month_name": month_date.strftime("%B"),
                "revenue": base_revenue + (i * 500) + (2000 * (1 if i % 2 == 0 else -1)),
                "orders": 160 + (id_num * 3) + (i * 5),
                "avg_order_value": 220 + (id_num * 2) + (i * 2),
                "emails_sent": 11000 + (id_num * 80) + (i * 200),
                "open_rate": 26 + (id_num % 8) + (i * 0.3),
                "click_rate": 4.2 + (id_num % 3) + (i * 0.1),
                "conversion_rate": 2.7 + (id_num % 4) * 0.1 + (i * 0.05),
            }
        )

    return {
        "client_id": str(client_id),
        "period": f"Last {months} months",
        "data": list(reversed(series)),
        "summary": {
            "average_monthly_revenue": sum(m["revenue"] for m in series) / len(series),
            "total_revenue": sum(m["revenue"] for m in series),
            "growth_rate": (
                ((series[0]["revenue"] - series[-1]["revenue"]) / series[-1]["revenue"]) * 100 if len(series) > 1 else 0
            ),
        },
    }


@router.get("/comparison")
async def get_performance_comparison(
    client_ids: str = Query(description="Comma-separated list of client IDs"),
) -> Dict[str, Any]:
    """Compare performance across multiple clients (mocked)."""
    ids = [cid.strip() for cid in client_ids.split(",") if cid.strip()]
    rows: List[Dict[str, Any]] = []

    for cid in ids:
        id_num = _safe_int_from_client_id(cid)
        rows.append(
            {
                "client_id": str(cid),
                "client_name": f"Client {cid}",
                "mtd_revenue": 35000 + (id_num * 3000),
                "mtd_orders": 160 + (id_num * 15),
                "avg_order_value": 220 + (id_num * 8),
                "open_rate": 26 + (id_num % 12),
                "click_rate": 4.2 + (id_num % 4) * 0.5,
                "conversion_rate": 2.7 + (id_num % 6) * 0.2,
            }
        )

    for metric in ("mtd_revenue", "mtd_orders", "avg_order_value", "open_rate", "click_rate", "conversion_rate"):
        ranked = sorted(rows, key=lambda x: x[metric], reverse=True)
        for rank, row in enumerate(ranked, 1):
            row[f"{metric}_rank"] = rank

    return {
        "comparison_date": datetime.now().isoformat(),
        "clients": rows,
        "best_performers": (
            {
                "revenue": max(rows, key=lambda x: x["mtd_revenue"])["client_name"],
                "orders": max(rows, key=lambda x: x["mtd_orders"])["client_name"],
                "engagement": max(rows, key=lambda x: x["open_rate"])["client_name"],
            }
            if rows
            else {}
        ),
    }


@router.get("/forecast/{client_id}")
async def get_revenue_forecast(
    client_id: Union[str, int],
    months_ahead: int = Query(default=3, ge=1, le=12, description="Number of months to forecast"),
) -> Dict[str, Any]:
    """Toy forecast with seasonal multipliers (replace with your model later)."""
    id_num = _safe_int_from_client_id(client_id)
    now = datetime.now()
    base_revenue = 35000 + (id_num * 400)
    seasonal = {1: 0.9, 2: 0.95, 3: 1.0, 4: 1.05, 5: 1.1, 6: 1.05, 7: 1.0, 8: 0.95, 9: 1.1, 10: 1.15, 11: 1.3, 12: 1.4}

    forecast = []
    for i in range(1, months_ahead + 1):
        month = (now.month + i - 1) % 12 + 1
        year = now.year + ((now.month + i - 1) // 12)
        s = seasonal.get(month, 1.0)
        g = 1.05 ** (i / 12)  # 5% annual growth
        y = base_revenue * s * g
        forecast.append(
            {
                "year": year,
                "month": month,
                "month_name": datetime(year, month, 1).strftime("%B"),
                "forecasted_revenue": round(y, 2),
                "confidence_interval": {"low": round(y * 0.85, 2), "high": round(y * 1.15, 2)},
                "seasonal_factor": s,
                "assumptions": ["5% annual growth rate", "Historical seasonal patterns", "Stable market conditions"],
            }
        )

    return {
        "client_id": str(client_id),
        "forecast_period": f"Next {months_ahead} months",
        "generated_at": now.isoformat(),
        "forecast": forecast,
        "total_forecasted_revenue": sum(x["forecasted_revenue"] for x in forecast),
        "methodology": "Time-series with seasonal adjustments (toy)",
    }


# ---- Report triggers (wire these to jobs/Cloud Functions when ready) ----
@router.post("/reports/weekly/generate")
async def generate_weekly_reports(background_tasks: BackgroundTasks, client_id: Optional[str] = None):
    try:
        logger.info("Weekly report generation requested for %s", client_id or "all")
        # background_tasks.add_task(run_weekly_reports, client_id)
        return {
            "status": "started",
            "message": f"Weekly report generation started for {client_id or 'all active clients'}",
            "timestamp": datetime.now().isoformat(),
            "note": "Hook to your report worker here",
        }
    except Exception as e:
        logger.error("Weekly report start failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/monthly/generate")
async def generate_monthly_reports(background_tasks: BackgroundTasks, client_id: Optional[str] = None):
    try:
        logger.info("Monthly report generation requested for %s", client_id or "all")
        # background_tasks.add_task(run_monthly_reports, client_id)
        return {
            "status": "started",
            "message": f"Monthly report generation started for {client_id or 'all active clients'}",
            "timestamp": datetime.now().isoformat(),
            "note": "Hook to your report worker here",
        }
    except Exception as e:
        logger.error("Monthly report start failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/weekly/scheduler-trigger")
async def scheduler_trigger_weekly():
    try:
        logger.info("Weekly reports scheduler trigger received")
        return {"status": "triggered", "message": "Weekly reports trigger received", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error("Weekly scheduler trigger failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/monthly/scheduler-trigger")
async def scheduler_trigger_monthly():
    try:
        logger.info("Monthly reports scheduler trigger received")
        return {"status": "triggered", "message": "Monthly reports trigger received", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error("Monthly scheduler trigger failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-endpoint")
async def test_endpoint():
    return {"status": "working", "message": "Performance API router is operational", "timestamp": datetime.now().isoformat()}


@router.get("/test-mtd-errors")
async def test_mtd_error_handling():
    """Test endpoint to validate error handling in MTD endpoint"""
    test_cases = []
    
    # Test 1: Empty client ID
    try:
        result = await get_mtd_performance("")
        test_cases.append({
            "test": "empty_client_id",
            "status": "success" if result["data_source"] == "mock" else "failed",
            "data_source": result["data_source"],
            "has_error_details": "error_details" in result
        })
    except Exception as e:
        test_cases.append({
            "test": "empty_client_id",
            "status": "exception",
            "error": str(e)
        })
    
    # Test 2: Special characters in client ID
    try:
        result = await get_mtd_performance("client@#$%")
        test_cases.append({
            "test": "special_chars_client_id",
            "status": "success" if result["data_source"] == "mock" else "failed",
            "data_source": result["data_source"],
            "has_error_details": "error_details" in result
        })
    except Exception as e:
        test_cases.append({
            "test": "special_chars_client_id",
            "status": "exception",
            "error": str(e)
        })
    
    # Test 3: Very long client ID
    try:
        long_id = "x" * 1000
        result = await get_mtd_performance(long_id)
        test_cases.append({
            "test": "long_client_id",
            "status": "success" if result["data_source"] == "mock" else "failed",
            "data_source": result["data_source"],
            "has_error_details": "error_details" in result
        })
    except Exception as e:
        test_cases.append({
            "test": "long_client_id",
            "status": "exception",
            "error": str(e)
        })
    
    return {
        "message": "MTD endpoint error handling test results",
        "timestamp": datetime.now().isoformat(),
        "test_cases": test_cases,
        "all_passed": all(case.get("status") == "success" for case in test_cases)
    }