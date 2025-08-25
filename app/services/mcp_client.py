from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx


class MCPClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 20.0):
        self.base_url = base_url or os.getenv("MCP_DATA_SERVICE_URL", "http://0.0.0.0:8080")
        self._timeout = httpx.Timeout(timeout, connect=8.0)

    async def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(url, json=json)
            r.raise_for_status()
            return r.json()

    async def list_campaigns(self, client_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        payload = {
            "client_id": client_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        data = await self._post("/campaigns/list", payload)
        # Some MCP implementations may return a dict; normalize to list
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        # Fallback to empty list
        return []

    async def metrics_performance(self, client_id: str, start_date: datetime, end_date: datetime, metric_name: str = "Placed Order") -> Dict[str, Any]:
        payload = {
            "client_id": client_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metric_name": metric_name,
        }
        return await self._post("/metrics/performance", payload)

    async def list_segments(self, client_id: str) -> List[Dict[str, Any]]:
        payload = {"client_id": client_id}
        data = await self._post("/segments/list", payload)
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        return []

