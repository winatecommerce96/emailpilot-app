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
        url = path if path.startswith("http") else f"{KLAVIYO_API_URL}{path}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            r = await client.get(url, headers=self._headers(), params=params or {})
            if r.status_code >= 400:
                detail = r.text
                logging.error(f"Klaviyo GET {url} failed {r.status_code}: {detail}")
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

    async def get_events(self, metric_id: str = None, since: str = None, until: str = None) -> Dict[str, Any]:
        """
        Get events data from Klaviyo for order monitoring.
        
        Args:
            metric_id: Specific metric ID to filter (e.g., 'Placed Order')
            since: ISO timestamp for start date
            until: ISO timestamp for end date
            
        Returns:
            Dict containing events data
        """
        try:
            params = {"page[size]": 100}
            
            if metric_id:
                params["filter"] = f"equals(metric_id,\"{metric_id}\")"
            if since:
                params["filter"] = f"greater-or-equal(datetime,{since})"
            if until:
                current_filter = params.get("filter", "")
                time_filter = f"less-or-equal(datetime,{until})"
                params["filter"] = f"{current_filter},{time_filter}" if current_filter else time_filter
                
            data = await self._get("/events/", params)
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return {"data": [], "error": str(e)}

    async def get_metrics(self) -> Dict[str, Any]:
        """Get available metrics from Klaviyo"""
        try:
            data = await self._get("/metrics/")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            return {"data": [], "error": str(e)}

    async def get_metric_by_name(self, metric_name: str) -> Dict[str, Any]:
        """
        Find a metric by name (e.g., 'Placed Order')
        
        Args:
            metric_name: Name of the metric to find
            
        Returns:
            Dict containing metric info or None if not found
        """
        try:
            metrics_data = await self.get_metrics()
            
            for metric in metrics_data.get("data", []):
                attributes = metric.get("attributes", {})
                if attributes.get("name") == metric_name:
                    return metric
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to find metric {metric_name}: {e}")
            return None

    async def get_order_events_by_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get order events for a specific date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dict containing order events and summary
        """
        try:
            # Convert dates to ISO format for API
            start_iso = f"{start_date}T00:00:00Z"
            end_iso = f"{end_date}T23:59:59Z"
            
            # First, try to find the "Placed Order" metric
            order_metric = await self.get_metric_by_name("Placed Order")
            metric_id = order_metric.get("id") if order_metric else None
            
            # Get events for the date range
            events_data = await self.get_events(
                metric_id=metric_id,
                since=start_iso,
                until=end_iso
            )
            
            # Process events to extract order information
            events = events_data.get("data", [])
            total_orders = len(events)
            total_revenue = 0.0
            
            # Calculate revenue from events
            for event in events:
                properties = event.get("attributes", {}).get("properties", {})
                # Look for common revenue/value fields
                order_value = (
                    properties.get("$value") or
                    properties.get("Value") or
                    properties.get("total") or
                    properties.get("revenue") or 0
                )
                if isinstance(order_value, (int, float)):
                    total_revenue += float(order_value)
                elif isinstance(order_value, str):
                    try:
                        total_revenue += float(order_value.replace("$", "").replace(",", ""))
                    except ValueError:
                        pass  # Skip invalid values
            
            return {
                "success": True,
                "period": {"start": start_date, "end": end_date},
                "orders": total_orders,
                "revenue": total_revenue,
                "events": events[:50],  # Limit events in response
                "total_events": len(events)
            }
            
        except Exception as e:
            logger.error(f"Failed to get order events for {start_date} to {end_date}: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders": 0,
                "revenue": 0.0
            }
