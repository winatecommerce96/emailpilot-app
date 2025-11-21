"""
Slack Alert Service for Order Monitoring

Handles sending formatted alerts to Slack when zero-value order days
are detected. Supports different severity levels and rich formatting.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging
import httpx
from datetime import datetime

from app.services.secret_manager import SecretManagerService

logger = logging.getLogger(__name__)

class SlackAlertService:
    """Service for sending Slack alerts about order monitoring issues"""
    
    def __init__(self, secret_manager: SecretManagerService):
        self.secret_manager = secret_manager
    
    async def send_order_alert(
        self, 
        client_id: str, 
        zero_order_days: List[str], 
        zero_revenue_days: List[str],
        severity: str = "warning"
    ) -> bool:
        """
        Send Slack alert for zero-value order days
        
        Args:
            client_id: Client identifier
            zero_order_days: List of dates with zero orders
            zero_revenue_days: List of dates with zero revenue
            severity: Alert severity ("warning" or "critical")
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            webhook_url = await self._get_slack_webhook_url()
            if not webhook_url:
                logger.warning("Slack webhook URL not configured - alerts disabled")
                return False
            
            # Get client name for better formatting
            client_name = await self._get_client_name(client_id)
            
            # Build alert message
            message = self._build_alert_message(
                client_id, client_name, zero_order_days, zero_revenue_days, severity
            )
            
            # Send to Slack
            success = await self._send_to_slack(webhook_url, message)
            
            if success:
                logger.info(f"Slack alert sent for client {client_id} ({severity})")
            else:
                logger.error(f"Failed to send Slack alert for client {client_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Slack alert failed for client {client_id}: {e}")
            return False
    
    async def send_system_alert(self, message: str, severity: str = "info") -> bool:
        """Send general system alert to Slack"""
        try:
            webhook_url = await self._get_slack_webhook_url()
            if not webhook_url:
                return False
            
            alert = {
                "text": f"EmailPilot System Alert ({severity.upper()})",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🤖 *EmailPilot System Alert*\n\n{message}"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Severity: {severity.upper()} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                            }
                        ]
                    }
                ]
            }
            
            return await self._send_to_slack(webhook_url, alert)
            
        except Exception as e:
            logger.error(f"System alert failed: {e}")
            return False
    
    async def _get_slack_webhook_url(self) -> Optional[str]:
        """Get Slack webhook URL from Secret Manager"""
        try:
            webhook_url = self.secret_manager.get_secret("emailpilot-slack-webhook-url")
            return webhook_url.strip() if webhook_url else None
        except Exception as e:
            logger.debug(f"Failed to get Slack webhook URL: {e}")
            return None
    
    async def _get_client_name(self, client_id: str) -> str:
        """Get client display name (would query Firestore in production)"""
        # This is a simplified implementation
        # In production, you'd query Firestore for the client's display name
        return f"Client {client_id}"
    
    def _build_alert_message(
        self,
        client_id: str,
        client_name: str,
        zero_order_days: List[str],
        zero_revenue_days: List[str],
        severity: str
    ) -> Dict[str, Any]:
        """Build formatted Slack message for order alerts"""
        
        # Choose emoji based on severity
        severity_emoji = "🚨" if severity == "critical" else "⚠️"
        color = "danger" if severity == "critical" else "warning"
        
        # Build main message text
        issues = []
        if zero_order_days:
            issues.append(f"• *{len(zero_order_days)} days with zero orders*: {', '.join(zero_order_days)}")
        if zero_revenue_days:
            issues.append(f"• *{len(zero_revenue_days)} days with zero revenue*: {', '.join(zero_revenue_days)}")
        
        issues_text = "\n".join(issues)
        
        # Determine priority message
        if severity == "critical":
            priority_msg = "🔴 *CRITICAL* - Multiple zero-value days detected. Immediate attention required."
        else:
            priority_msg = "🟡 *WARNING* - Zero-value days detected. Review recommended."
        
        message = {
            "text": f"{severity_emoji} Order Alert: {client_name}",
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{severity_emoji} Order Monitoring Alert"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Client:* {client_name} (`{client_id}`)\n{priority_msg}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Issues Detected:*\n{issues_text}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Recommended Actions:*\n• Check Klaviyo integration status\n• Verify data pipeline connections\n• Review client campaign activity\n• Contact client if issue persists"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Alert triggered: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Severity: {severity.upper()}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        return message
    
    async def _send_to_slack(self, webhook_url: str, message: Dict[str, Any]) -> bool:
        """Send message to Slack webhook"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.post(webhook_url, json=message)
                
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Slack webhook returned status {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    async def send_monitoring_summary(self, results: List[Dict[str, Any]]) -> bool:
        """Send daily/periodic monitoring summary to Slack"""
        try:
            webhook_url = await self._get_slack_webhook_url()
            if not webhook_url:
                return False
            
            total_clients = len(results)
            successful = len([r for r in results if r.get("success", False)])
            with_alerts = len([r for r in results if r.get("alert_triggered", False)])
            
            message = {
                "text": "📊 Daily Order Monitoring Summary",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 Daily Order Monitoring Summary"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Monitoring Results:*\n• Total clients monitored: {total_clients}\n• Successful checks: {successful}\n• Alerts triggered: {with_alerts}"
                        }
                    }
                ]
            }
            
            # Add details for clients with issues
            if with_alerts > 0:
                alert_details = []
                for result in results:
                    if result.get("alert_triggered", False):
                        client_id = result.get("client_id", "unknown")
                        zero_orders = len(result.get("zero_order_days", []))
                        zero_revenue = len(result.get("zero_revenue_days", []))
                        alert_details.append(f"• {client_id}: {zero_orders} zero-order days, {zero_revenue} zero-revenue days")
                
                if alert_details:
                    message["blocks"].append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Clients with Issues:*\n" + "\n".join(alert_details[:10])  # Limit to 10 for readability
                        }
                    })
            
            message["blocks"].append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            })
            
            return await self._send_to_slack(webhook_url, message)
            
        except Exception as e:
            logger.error(f"Failed to send monitoring summary: {e}")
            return False

    async def send_weekly_report(self, report_message: Dict[str, Any]) -> bool:
        """Send weekly revenue report to Slack"""
        try:
            webhook_url = await self._get_slack_webhook_url()
            if not webhook_url:
                logger.warning("Slack webhook URL not configured - weekly report not sent")
                return False
            
            # Send the pre-formatted weekly report message
            success = await self._send_to_slack(webhook_url, report_message)
            
            if success:
                logger.info("Weekly revenue report sent to Slack successfully")
            else:
                logger.error("Failed to send weekly revenue report to Slack")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}")
            return False