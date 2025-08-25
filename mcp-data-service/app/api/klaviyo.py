from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from ..services.klaviyo_api import KlaviyoAPIClient
import os
from ..services.secret_manager import get_secret_value, get_project_id, SecretLoadError

router = APIRouter()

async def get_klaviyo_client_for_client_id(client_id: str):
    try:
        # DEV override: use hardcoded Christopher Bean Coffee key when provided
        dev_key = os.getenv("DEV_CHRISTOPHER_BEAN_KLAVIYO")
        if dev_key and client_id.replace('_','-').lower() == 'christopher-bean-coffee':
            return KlaviyoAPIClient(dev_key)
        project_id = get_project_id()
        klaviyo_api_key_secret_id = f"klaviyo-api-{client_id.lower().replace('_', '-')}"
        klaviyo_api_key = get_secret_value(project_id, klaviyo_api_key_secret_id)
        return KlaviyoAPIClient(klaviyo_api_key)
    except SecretLoadError as e:
        raise HTTPException(status_code=400, detail=f"Klaviyo API key not configured for client {client_id}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving Klaviyo API key for client {client_id}: {e}")

class DateRangeRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    client_id: str # Keep client_id here

class CampaignListRequest(DateRangeRequest):
    pass

class MetricsPerformanceRequest(DateRangeRequest):
    metric_name: str = Field("Placed Order", description="Name of the metric to fetch performance for (e.g., 'Placed Order')")

class SegmentListRequest(BaseModel):
    client_id: str # Keep client_id here

@router.post("/campaigns/list")
async def list_campaigns(
    request_data: CampaignListRequest,
) -> List[Dict[str, Any]]:
    """
    Fetches a list of campaigns from Klaviyo within a specified date range for a specific client.
    """
    try:
        klaviyo_client = await get_klaviyo_client_for_client_id(request_data.client_id)
        campaigns = await klaviyo_client.get_campaigns(request_data.start_date, request_data.end_date)
        return campaigns
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch campaigns: {e}")

@router.post("/metrics/performance")
async def get_metrics_performance(
    request_data: MetricsPerformanceRequest,
) -> Dict[str, Any]:
    """
    Fetches performance data for a specific metric from Klaviyo within a specified date range for a specific client.
    """
    try:
        klaviyo_client = await get_klaviyo_client_for_client_id(request_data.client_id)
        performance_data = await klaviyo_client.get_metrics_performance(
            request_data.start_date, request_data.end_date, request_data.metric_name
        )
        return performance_data
    except HTTPException as e:
        # Gracefully degrade when metric-id mapping isn't configured yet
        if getattr(e, "status_code", 500) in (400, 401, 403, 404, 422):
            return {
                "data": {},
                "warning": "Metric aggregates unavailable (missing metric_id mapping); continuing without performance data.",
            }
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics performance: {e}")

@router.post("/segments/list")
async def list_segments(
    request_data: SegmentListRequest,
) -> List[Dict[str, Any]]:
    """
    Fetches a list of segments from Klaviyo for a specific client.
    """
    try:
        klaviyo_client = await get_klaviyo_client_for_client_id(request_data.client_id)
        segments = await klaviyo_client.get_segments()
        return segments
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch segments: {e}")
