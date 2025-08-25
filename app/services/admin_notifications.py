"""
Admin Notification Service for EmailPilot

Handles error notifications and alerts for system administrators.
Stores notifications in Firestore and provides API endpoints for viewing.
Replaces Slack spam with organized admin dashboard notifications.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from google.cloud import firestore

logger = logging.getLogger(__name__)

class NotificationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"

@dataclass
class AdminNotification:
    """Data class for admin notifications"""
    id: str
    title: str
    message: str
    severity: NotificationSeverity
    source: str
    client_id: Optional[str]
    data: Optional[Dict[str, Any]]
    timestamp: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None

class AdminNotificationService:
    """Service for managing admin notifications in EmailPilot"""
    
    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection_name = "admin_notifications"
    
    async def create_notification(
        self,
        title: str,
        message: str,
        severity: NotificationSeverity,
        source: str,
        client_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new admin notification
        
        Args:
            title: Brief notification title
            message: Detailed notification message
            severity: Notification severity level
            source: Source system that generated the notification
            client_id: Optional client ID if notification is client-specific
            data: Optional additional data payload
            
        Returns:
            Notification ID
        """
        try:
            notification_id = f"{source}_{int(datetime.now().timestamp())}"
            
            notification_data = {
                "id": notification_id,
                "title": title,
                "message": message,
                "severity": severity.value,
                "source": source,
                "client_id": client_id,
                "data": data or {},
                "timestamp": datetime.now().isoformat(),
                "acknowledged": False,
                "acknowledged_by": None,
                "acknowledged_at": None,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            
            # Store in Firestore
            doc_ref = self.db.collection(self.collection_name).document(notification_id)
            doc_ref.set(notification_data)
            
            logger.info(f"Created admin notification: {notification_id} ({severity.value})")
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to create admin notification: {e}")
            raise
    
    async def order_monitoring_alert(
        self,
        client_id: str,
        zero_revenue_days: List[str],
        total_days: int = 5,
        client_name: Optional[str] = None
    ) -> str:
        """
        Create order monitoring alert notification
        
        Args:
            client_id: Client identifier
            zero_revenue_days: List of dates with zero revenue
            total_days: Total monitoring period
            client_name: Optional client display name
            
        Returns:
            Notification ID
        """
        try:
            severity = NotificationSeverity.CRITICAL if len(zero_revenue_days) >= 3 else NotificationSeverity.WARNING
            
            title = f"Order Monitoring Alert: {client_name or client_id}"
            message = f"Client has {len(zero_revenue_days)} out of {total_days} days with zero revenue in the last {total_days} days."
            
            data = {
                "zero_revenue_days": zero_revenue_days,
                "total_monitoring_days": total_days,
                "alert_type": "order_monitoring",
                "affected_days_count": len(zero_revenue_days),
                "severity_reason": f"{len(zero_revenue_days)} zero-revenue days detected"
            }
            
            return await self.create_notification(
                title=title,
                message=message,
                severity=severity,
                source="order_monitor",
                client_id=client_id,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Failed to create order monitoring alert: {e}")
            raise
    
    async def system_error_alert(
        self,
        title: str,
        error_message: str,
        source: str,
        client_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create system error alert notification
        
        Args:
            title: Error title
            error_message: Detailed error message
            source: Source system that encountered the error
            client_id: Optional client ID if error is client-specific
            additional_data: Optional additional error context
            
        Returns:
            Notification ID
        """
        try:
            data = {
                "error_type": "system_error",
                "error_details": additional_data or {},
                "timestamp": datetime.now().isoformat()
            }
            
            return await self.create_notification(
                title=title,
                message=error_message,
                severity=NotificationSeverity.ERROR,
                source=source,
                client_id=client_id,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Failed to create system error alert: {e}")
            raise
    
    async def get_notifications(
        self,
        limit: int = 50,
        severity_filter: Optional[NotificationSeverity] = None,
        acknowledged_filter: Optional[bool] = None,
        client_id_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve admin notifications with filtering
        
        Args:
            limit: Maximum number of notifications to return
            severity_filter: Filter by severity level
            acknowledged_filter: Filter by acknowledgment status
            client_id_filter: Filter by client ID
            
        Returns:
            List of notification dictionaries
        """
        try:
            query = self.db.collection(self.collection_name)
            
            # Apply filters
            if severity_filter:
                query = query.where("severity", "==", severity_filter.value)
            
            if acknowledged_filter is not None:
                query = query.where("acknowledged", "==", acknowledged_filter)
            
            if client_id_filter:
                query = query.where("client_id", "==", client_id_filter)
            
            # Order by timestamp descending and limit
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = query.stream()
            notifications = []
            
            for doc in docs:
                notification_data = doc.to_dict()
                notifications.append(notification_data)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to retrieve notifications: {e}")
            return []
    
    async def acknowledge_notification(
        self,
        notification_id: str,
        acknowledged_by: str
    ) -> bool:
        """
        Acknowledge a notification
        
        Args:
            notification_id: Notification to acknowledge
            acknowledged_by: User who acknowledged the notification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(notification_id)
            
            update_data = {
                "acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.now().isoformat(),
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            
            doc_ref.update(update_data)
            logger.info(f"Acknowledged notification {notification_id} by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge notification {notification_id}: {e}")
            return False
    
    async def get_notification_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for admin notifications
        
        Returns:
            Summary statistics dictionary
        """
        try:
            # Get all notifications from last 7 days
            seven_days_ago = datetime.now() - timedelta(days=7)
            query = self.db.collection(self.collection_name).where(
                "timestamp", ">=", seven_days_ago.isoformat()
            )
            
            docs = list(query.stream())
            
            total_notifications = len(docs)
            unacknowledged = len([doc for doc in docs if not doc.to_dict().get("acknowledged", False)])
            
            # Count by severity
            severity_counts = {severity.value: 0 for severity in NotificationSeverity}
            for doc in docs:
                severity = doc.to_dict().get("severity", "info")
                if severity in severity_counts:
                    severity_counts[severity] += 1
            
            # Count by source
            source_counts = {}
            for doc in docs:
                source = doc.to_dict().get("source", "unknown")
                source_counts[source] = source_counts.get(source, 0) + 1
            
            return {
                "total_notifications": total_notifications,
                "unacknowledged_notifications": unacknowledged,
                "severity_breakdown": severity_counts,
                "source_breakdown": source_counts,
                "time_period": "last_7_days",
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate notification summary: {e}")
            return {}
    
    async def cleanup_old_notifications(self, days_to_keep: int = 30) -> int:
        """
        Clean up old notifications to prevent database bloat
        
        Args:
            days_to_keep: Number of days of notifications to keep
            
        Returns:
            Number of notifications deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Find old notifications
            query = self.db.collection(self.collection_name).where(
                "timestamp", "<", cutoff_date.isoformat()
            ).where("acknowledged", "==", True)  # Only delete acknowledged notifications
            
            docs = list(query.stream())
            deleted_count = 0
            
            # Delete in batches to avoid timeout
            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Commit batch every 100 operations
                if deleted_count % 100 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining operations
            if deleted_count % 100 != 0:
                batch.commit()
            
            logger.info(f"Cleaned up {deleted_count} old notifications (older than {days_to_keep} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")
            return 0