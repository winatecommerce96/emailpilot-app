from __future__ import annotations
from typing import Dict, Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

KLAVIYO_API_URL = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2023-10-15"

class KlaviyoClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Klaviyo API key is required")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Klaviyo-API-Key {self.api_key}",
            "accept": "application/json",
            "revision": KLAVIYO_REVISION,
        }

    async def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            r = await client.get(f"{KLAVIYO_API_URL}{path}", headers=self._headers(), params=params or {})
            r.raise_for_status()
            return r.json()

    async def campaigns_summary(self) -> Dict[str, Any]:
        out = {"revenue": 0.0, "orders": 0, "emails_sent": 0, "unique_opens": 0, "unique_clicks": 0, "bounced": 0, "unsubscribed": 0}
        data = await self._get("/campaigns/", {"page[size]": 50})
        for c in data.get("data", []):
            stats = (c.get("attributes") or {}).get("statistics", {})
            out["revenue"] += float(stats.get("revenue", 0) or 0)
            out["orders"] += int(stats.get("orders", 0) or 0)
            out["emails_sent"] += int(stats.get("recipients", 0) or 0)
            out["unique_opens"] += int(stats.get("unique_opens", 0) or 0)
            out["unique_clicks"] += int(stats.get("unique_clicks", 0) or 0)
            out["bounced"] += int(stats.get("bounced", 0) or 0)
            out["unsubscribed"] += int(stats.get("unsubscribed", 0) or 0)
        return out

    async def flows_summary(self) -> Dict[str, Any]:
        out = {"revenue": 0.0, "orders": 0, "emails_sent": 0, "unique_opens": 0, "unique_clicks": 0}
        data = await self._get("/flows/", {"page[size]": 50})
        for f in data.get("data", []):
            stats = (f.get("attributes") or {}).get("statistics", {})
            out["revenue"] += float(stats.get("revenue", 0) or 0)
            out["orders"] += int(stats.get("orders", 0) or 0)
            out["emails_sent"] += int(stats.get("recipients", 0) or 0)
            out["unique_opens"] += int(stats.get("unique_opens", 0) or 0)
            out["unique_clicks"] += int(stats.get("unique_clicks", 0) or 0)
        return out

    async def mtd_summary(self) -> Dict[str, Any]:
        c = await self.campaigns_summary()
        f = await self.flows_summary()
        return {
            "revenue": c["revenue"] + f["revenue"],
            "orders": c["orders"] + f["orders"],
            "emails_sent": c["emails_sent"] + f["emails_sent"],
            "unique_opens": c["unique_opens"] + f["unique_opens"],
            "unique_clicks": c["unique_clicks"] + f["unique_clicks"],
            "bounced": c["bounced"],
            "unsubscribed": c["unsubscribed"],
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test if the API key is valid by fetching account info"""
        try:
            data = await self._get("/accounts/")
            return {"success": True, "accounts": len(data.get("data", []))}
        except Exception as e:
            return {"success": False, "error": str(e)}