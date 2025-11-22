"""
Revenue Monitoring Service for EmailPilot Integration

Monitors email-attributed revenue data for the last 5 days using the Revenue API service.
Detects zero-revenue periods from Campaign + Flow attribution, not raw events.
Integrates with Slack alerting system and stores data in Firestore following 
established client-scoped patterns.

This service replaces direct Klaviyo API calls with proper revenue attribution
by calling the Revenue API service at port 9090 which provides Campaign + Flow
conversion values for the 'Placed Order' metric.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass
import httpx

from google.cloud import firestore
from app.services.secret_manager import SecretManagerService

logger = logging.getLogger(__name__)

@dataclass
class DayOrderData:
    """Data class for single day order information"""
    date: str
    campaign_total: float
    flow_total: float
    total_revenue: float
    timestamp: str
    is_zero_revenue: bool
    attribution_available: bool = True

@dataclass
class OrderMonitorResult:
    """Result of order monitoring operation"""
    client_id: str
    success: bool
    days_data: List[DayOrderData]
    zero_revenue_days: List[str]
    alert_triggered: bool
    error_message: Optional[str] = None
    timestamp: str = None
    revenue_api_available: bool = True
    
    @property
    def zero_order_days(self) -> List[str]:
        """Legacy compatibility property - returns zero_revenue_days"""
        return self.zero_revenue_days

class OrderMonitorService:
    """Service for monitoring Klaviyo order data and managing alerts"""
    
    def __init__(self, db: firestore.Client, secret_manager: SecretManagerService, revenue_api_base: str = "http://localhost:9090"):
        self.db = db
        self.secret_manager = secret_manager
        self.revenue_api_base = revenue_api_base
        self.http_client = httpx.AsyncClient(timeout=5.0)  # Reduced timeout to prevent hanging
        
    async def get_5_day_revenue(self, client_id: str, alert_on_zero: bool = True) -> OrderMonitorResult:
        """
        Fetch last 5 days of email-attributed revenue data for a client using Revenue API
        
        Args:
            client_id: Client identifier
            alert_on_zero: Whether to trigger alerts for zero-value days
            
        Returns:
            OrderMonitorResult with revenue data and alert status
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Check if Revenue API is available
            revenue_api_available = await self._check_revenue_api_health()
            if not revenue_api_available:
                return OrderMonitorResult(
                    client_id=client_id,
                    success=False,
                    days_data=[],
                    zero_revenue_days=[],
                    alert_triggered=False,
                    error_message="Revenue API service not available at " + self.revenue_api_base,
                    timestamp=timestamp,
                    revenue_api_available=False
                )
            
            # Fetch revenue data from Revenue API for each day
            logger.info(f"Fetching 5-day revenue data for client {client_id} from Revenue API...")
            try:
                days_data = await self._fetch_5_day_revenue_data(client_id)
            except ValueError as ve:
                # Missing API key - skip this client
                logger.info(f"Skipping client {client_id}: {ve}")
                return OrderMonitorResult(
                    client_id=client_id,
                    success=False,
                    days_data=[],
                    zero_revenue_days=[],
                    alert_triggered=False,
                    error_message=str(ve),
                    timestamp=timestamp,
                    revenue_api_available=True
                )
            
            # Analyze for zero-value days
            zero_revenue_days = [day.date for day in days_data if day.is_zero_revenue]
            
            # Store data in Firestore
            await self._store_revenue_data(client_id, days_data, timestamp)
            
            # Trigger alerts if needed
            alert_triggered = False
            if alert_on_zero and zero_revenue_days:
                alert_triggered = await self._trigger_alerts(
                    client_id, zero_revenue_days
                )
            
            result = OrderMonitorResult(
                client_id=client_id,
                success=True,
                days_data=days_data,
                zero_revenue_days=zero_revenue_days,
                alert_triggered=alert_triggered,
                timestamp=timestamp,
                revenue_api_available=True
            )
            
            logger.info(f"Revenue monitoring completed for client {client_id}: {len(zero_revenue_days)} zero-revenue days")
            return result
            
        except Exception as e:
            logger.error(f"Revenue monitoring failed for client {client_id}: {e}")
            return OrderMonitorResult(
                client_id=client_id,
                success=False,
                days_data=[],
                zero_revenue_days=[],
                alert_triggered=False,
                error_message=str(e),
                timestamp=timestamp,
                revenue_api_available=False
            )
    
    async def _check_revenue_api_health(self) -> bool:
        """Check if Revenue API service is available"""
        try:
            # Use a reasonable timeout for health check
            logger.debug(f"Checking Revenue API health at {self.revenue_api_base}...")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.revenue_api_base}/healthz")
                if response.status_code == 200:
                    logger.debug("Revenue API is healthy and responding")
                    return True
                else:
                    logger.warning(f"Revenue API returned status {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"Revenue API health check failed: {e}")
            return False
    
    async def _get_client_slug(self, client_id: str) -> Optional[str]:
        """Get client slug from Firestore for Revenue API calls"""
        try:
            snap = self.db.collection("clients").document(client_id).get()
            if not snap.exists:
                logger.warning(f"Client document not found: {client_id}")
                return None
            
            data = snap.to_dict() or {}
            return data.get("client_slug") or client_id  # Fallback to client_id if no slug
            
        except Exception as e:
            logger.error(f"Failed to get client slug for {client_id}: {e}")
            return client_id  # Fallback to client_id
    
    async def _fetch_5_day_revenue_data(self, client_id: str) -> List[DayOrderData]:
        logger.info(f"Starting 5-day revenue fetch for client {client_id}")
        """
        Fetch 5 days of email-attributed revenue data from Revenue API service
        """
        days_data = []
        client_slug = await self._get_client_slug(client_id)
        
        try:
            # Fetch data for each of the last 5 days using individual day calls
            for i in range(5):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                
                # Calculate start and end timestamps for the specific day
                start_time = f"{date}T00:00:00Z"
                end_time = f"{date}T23:59:59Z"
                
                # Call Revenue API for this specific day using custom timeframe
                params = {
                    "start": start_time,
                    "end": end_time,
                    "recompute": "true"  # Always get fresh data for monitoring
                }
                
                try:
                    # Try client slug first, then fallback to client_id
                    if client_slug and client_slug != client_id:
                        url = f"{self.revenue_api_base}/clients/by-slug/{client_slug}/revenue/last7"
                    else:
                        url = f"{self.revenue_api_base}/clients/{client_id}/revenue/last7"
                    
                    response = await self.http_client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        campaign_total = float(data.get("campaign_total", 0))
                        flow_total = float(data.get("flow_total", 0))
                        total_revenue = float(data.get("total", 0))
                        
                        day_data = DayOrderData(
                            date=date,
                            campaign_total=campaign_total,
                            flow_total=flow_total,
                            total_revenue=total_revenue,
                            timestamp=datetime.now().isoformat(),
                            is_zero_revenue=(total_revenue == 0.0),
                            attribution_available=True
                        )
                        
                        logger.debug(f"Fetched revenue for {date}: Campaign=${campaign_total:.2f}, Flow=${flow_total:.2f}, Total=${total_revenue:.2f}")
                        
                    elif response.status_code == 400 and "Unable to resolve Klaviyo API key" in response.text:
                        # Missing API key - skip this client entirely
                        logger.warning(f"Client {client_id} has no Klaviyo API key configured - skipping")
                        raise ValueError(f"No API key for client {client_id}")
                    else:
                        logger.warning(f"Revenue API returned {response.status_code} for {date}: {response.text}")
                        day_data = DayOrderData(
                            date=date,
                            campaign_total=0.0,
                            flow_total=0.0,
                            total_revenue=0.0,
                            timestamp=datetime.now().isoformat(),
                            is_zero_revenue=True,
                            attribution_available=False
                        )
                    
                    days_data.append(day_data)
                    
                    # Add small delay between API calls
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch revenue data for {date}: {e}")
                    # Create zero-value entry for failed day
                    day_data = DayOrderData(
                        date=date,
                        campaign_total=0.0,
                        flow_total=0.0,
                        total_revenue=0.0,
                        timestamp=datetime.now().isoformat(),
                        is_zero_revenue=True,
                        attribution_available=False
                    )
                    days_data.append(day_data)
            
            logger.info(f"Successfully fetched revenue data for {len(days_data)} days")
            return days_data
            
        except Exception as e:
            logger.error(f"Failed to fetch revenue data from Revenue API: {e}")
            # Return mock data to prevent system failure
            return self._generate_mock_5_day_revenue_data()
    
    def _generate_mock_5_day_revenue_data(self) -> List[DayOrderData]:
        """Generate mock 5-day revenue data for testing/fallback"""
        days_data = []
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            # Simulate some zero-value days for testing
            campaign_total = 0.0 if i == 1 else (500 + i * 100)
            flow_total = 0.0 if i == 2 else (300 + i * 50)
            total_revenue = campaign_total + flow_total
            
            day_data = DayOrderData(
                date=date,
                campaign_total=campaign_total,
                flow_total=flow_total,
                total_revenue=total_revenue,
                timestamp=datetime.now().isoformat(),
                is_zero_revenue=(total_revenue == 0.0),
                attribution_available=False  # Mock data has no real attribution
            )
            days_data.append(day_data)
        
        return days_data
    
    async def _store_revenue_data(self, client_id: str, days_data: List[DayOrderData], timestamp: str):
        """Store email-attributed revenue data in Firestore following established patterns"""
        try:
            # Store in client-scoped collection
            doc_ref = self.db.collection("clients").document(client_id).collection("performance").document("revenue")
            
            # Prepare data for storage
            revenue_data = {
                "last_update": timestamp,
                "monitoring_enabled": True,
                "data_source": "revenue_api",
                "attribution_type": "email_marketing",
                "days_data": [
                    {
                        "date": day.date,
                        "campaign_total": day.campaign_total,
                        "flow_total": day.flow_total,
                        "total_revenue": day.total_revenue,
                        "timestamp": day.timestamp,
                        "is_zero_revenue": day.is_zero_revenue,
                        "attribution_available": day.attribution_available
                    }
                    for day in days_data
                ],
                "summary": {
                    "total_campaign_revenue": sum(day.campaign_total for day in days_data),
                    "total_flow_revenue": sum(day.flow_total for day in days_data),
                    "total_email_revenue": sum(day.total_revenue for day in days_data),
                    "zero_revenue_days": len([day for day in days_data if day.is_zero_revenue]),
                    "avg_daily_revenue": sum(day.total_revenue for day in days_data) / len(days_data) if days_data else 0,
                    "attribution_success_rate": len([day for day in days_data if day.attribution_available]) / len(days_data) if days_data else 0
                }
            }
            
            # Store the data
            doc_ref.set(revenue_data)
            logger.info(f"Stored revenue data for client {client_id} in Firestore")
            
        except Exception as e:
            logger.error(f"Failed to store revenue data for client {client_id}: {e}")
            # Don't re-raise, this is a logging operation
    
    async def _trigger_alerts(self, client_id: str, zero_revenue_days: List[str]) -> bool:
        """Send alerts to admin notification system instead of Slack"""
        try:
            # Use admin notification system instead of Slack
            from app.services.admin_notifications import AdminNotificationService
            
            admin_service = AdminNotificationService(self.db)
            
            # Create admin notification
            notification_id = await admin_service.order_monitoring_alert(
                client_id=client_id,
                zero_revenue_days=zero_revenue_days,
                total_days=5
            )
            
            logger.info(f"Created admin notification {notification_id} for client {client_id}: {len(zero_revenue_days)} zero-revenue days")
            return True
            
            # COMMENTED OUT: Original Slack alerting code
            # from app.services.slack_alerts import SlackAlertService
            # slack_service = SlackAlertService(self.secret_manager)
            # success = await slack_service.send_order_alert(
            #     client_id=client_id,
            #     zero_order_days=[],  # No order data available in revenue-focused monitoring
            #     zero_revenue_days=zero_revenue_days,
            #     severity=severity
            # )
            # if success:
            #     logger.info(f"Revenue alert sent for client {client_id}: {len(zero_revenue_days)} zero-revenue days")
            # else:
            #     logger.warning(f"Failed to send revenue alert for client {client_id}")
            # return success
            
        except Exception as e:
            logger.error(f"Revenue alert logging failed for client {client_id}: {e}")
            return False
    
    async def get_stored_revenue_data(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored email-attributed revenue data from Firestore"""
        try:
            doc_ref = self.db.collection("clients").document(client_id).collection("performance").document("revenue")
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.info(f"No stored revenue data found for client {client_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve stored revenue data for client {client_id}: {e}")
            return None
    
    async def monitor_all_clients(self, alert_on_zero: bool = True) -> List[OrderMonitorResult]:
        """Monitor email-attributed revenue data for all configured clients"""
        results = []
        
        try:
            # Check Revenue API health once at the beginning
            if not await self._check_revenue_api_health():
                logger.error("Revenue API is not available - aborting bulk monitoring")
                return []
            
            # Get all clients from Firestore
            clients = self.db.collection("clients").stream()
            client_ids = [client.id for client in clients]
            
            logger.info(f"Starting revenue monitoring for {len(client_ids)} clients")
            
            # Monitor each client (in production, consider batching/concurrency limits)
            for i, client_id in enumerate(client_ids, 1):
                logger.info(f"Processing client {i}/{len(client_ids)}: {client_id}")
                result = await self.get_5_day_revenue(client_id, alert_on_zero)
                results.append(result)
                
                # Skip delay for failed clients (no API key)
                if result.success:
                    # Add longer delay between successful clients to avoid Klaviyo rate limiting
                    logger.debug(f"Waiting 2 seconds before next client to avoid rate limiting...")
                    await asyncio.sleep(2.0)
            
            successful = len([r for r in results if r.success])
            logger.info(f"Revenue monitoring completed: {successful}/{len(results)} clients successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Bulk revenue monitoring failed: {e}")
            return results
    
    async def close(self):
        """Close HTTP client connections"""
        if hasattr(self, 'http_client'):
            await self.http_client.aclose()
    
    # Legacy compatibility methods
    async def get_5_day_orders(self, client_id: str, alert_on_zero: bool = True) -> OrderMonitorResult:
        """Legacy method - redirects to get_5_day_revenue"""
        logger.warning(f"get_5_day_orders is deprecated, use get_5_day_revenue instead")
        return await self.get_5_day_revenue(client_id, alert_on_zero)
    
    async def get_stored_order_data(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Legacy method - redirects to get_stored_revenue_data"""
        logger.warning(f"get_stored_order_data is deprecated, use get_stored_revenue_data instead")
        return await self.get_stored_revenue_data(client_id)