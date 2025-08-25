import os
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException

from .secret_manager import get_secret_value, get_project_id, SecretLoadError # Import the new secret manager

logger = logging.getLogger(__name__)

class KlaviyoAPIClient:
    def __init__(self, klaviyo_api_key: str): # API key will now be passed in
        self.api_key = klaviyo_api_key
        self.base_url = os.getenv("KLAVIYO_API_BASE_URL", "https://a.klaviyo.com/api")
        
        if not self.api_key:
            logger.error("Klaviyo API key not provided to KlaviyoAPIClient.")
            raise ValueError("Klaviyo API Key is required.")

        self.headers = {
            "Authorization": f"Klaviyo-API-Key {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Revision": "2024-02-15" # Specify API revision
        }
        self.client = httpx.AsyncClient()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making Klaviyo API request: {method} {url}")
        try:
            response = await self.client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status() # Raise an exception for 4xx or 5xx responses
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Klaviyo API HTTP error for {url}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Klaviyo API request error for {url}: {e}")
            raise HTTPException(status_code=500, detail=f"Klaviyo API request failed: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Klaviyo API request to {url}: {e}")
            raise HTTPException(status_code=500, detail=f"Unexpected Klaviyo API error: {e}")

    async def get_campaigns(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetches a list of email campaigns (channel-filtered). Date window filtering is applied by the caller."""
        params = {"filter": "equals(messages.channel,'email')"}
        all_campaigns: List[Dict[str, Any]] = []
        next_url: Optional[str] = None
        while True:
            if next_url:
                # Follow absolute next link
                response = await self._make_request("GET", next_url.replace(self.base_url, ""))
            else:
                response = await self._make_request("GET", "/campaigns", params=params)
            all_campaigns.extend(response.get("data", []))
            next_url = response.get("links", {}).get("next")
            if not next_url:
                break
        return all_campaigns

    async def get_metrics_performance(self, start_date: datetime, end_date: datetime, metric_name: str = "Placed Order") -> Dict[str, Any]:
        """Fetches performance data for a specific metric."""
        # Klaviyo API v2 uses /metric-aggregates for performance
        # This is a simplified example, real implementation might need more complex filtering
        payload = {
            "data": {
                "type": "metric-aggregate",
                "attributes": {
                    "metric_id": metric_name, # This needs to be a metric ID, not name
                    "interval": "day",
                    "page_size": 500,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "measurements": ["count"]
                }
            }
        }
        # Note: Klaviyo API v2 requires metric_id, not metric_name.
        # We'll need a way to map metric names to IDs or fetch all metrics first.
        # For now, this is a placeholder.
        logger.warning("Klaviyo API: get_metrics_performance uses placeholder metric_id. Real implementation needs metric ID mapping.")
        
        # This endpoint is POST
        response = await self._make_request("POST", "/metric-aggregates", json=payload)
        return response

    async def get_segments(self) -> List[Dict[str, Any]]:
        """Fetches a list of segments."""
        # Klaviyo API v2 segments endpoint is /segments
        all_segments = []
        next_cursor = None
        while True:
            current_params = {}
            if next_cursor:
                current_params["page[cursor]"] = next_cursor
            
            response = await self._make_request("GET", "/segments", params=current_params)
            all_segments.extend(response.get("data", []))
            
            next_cursor = response.get("links", {}).get("next")
            if not next_cursor:
                break
            next_cursor = next_cursor.split("page[cursor]=")[-1]
        return all_segments
