"""
Admin Notifications API

Provides endpoints for viewing and managing admin notifications.
Replaces Slack spam with organized admin dashboard notifications.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from app.deps import get_db
from app.services.admin_notifications import AdminNotificationService, NotificationSeverity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/notifications", tags=["admin", "notifications"])

@router.get("/")
async def get_notifications(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of notifications to return"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (info, warning, critical, error)"),
    acknowledged: Optional[bool] = Query(default=None, description="Filter by acknowledgment status"),
    client_id: Optional[str] = Query(default=None, description="Filter by client ID"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get admin notifications with filtering options
    """
    try:
        admin_service = AdminNotificationService(db)
        
        # Parse severity filter
        severity_filter = None
        if severity:
            try:
                severity_filter = NotificationSeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity '{severity}'. Valid values: info, warning, critical, error"
                )
        
        notifications = await admin_service.get_notifications(
            limit=limit,
            severity_filter=severity_filter,
            acknowledged_filter=acknowledged,
            client_id_filter=client_id
        )
        
        return {
            "notifications": notifications,
            "count": len(notifications),
            "filters_applied": {
                "limit": limit,
                "severity": severity,
                "acknowledged": acknowledged,
                "client_id": client_id
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{notification_id}/acknowledge")
async def acknowledge_notification(
    notification_id: str,
    acknowledged_by: str = Query(description="User who is acknowledging the notification"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Acknowledge a specific notification
    """
    try:
        admin_service = AdminNotificationService(db)
        
        success = await admin_service.acknowledge_notification(
            notification_id=notification_id,
            acknowledged_by=acknowledged_by
        )
        
        if success:
            return {
                "success": True,
                "message": f"Notification {notification_id} acknowledged by {acknowledged_by}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Notification {notification_id} not found or could not be acknowledged"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge notification {notification_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_notification_summary(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summary statistics for admin notifications
    """
    try:
        admin_service = AdminNotificationService(db)
        summary = await admin_service.get_notification_summary()
        
        return {
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get notification summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup")
async def cleanup_old_notifications(
    days_to_keep: int = Query(default=30, ge=7, le=365, description="Number of days of notifications to keep"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Clean up old acknowledged notifications
    """
    try:
        admin_service = AdminNotificationService(db)
        deleted_count = await admin_service.cleanup_old_notifications(days_to_keep)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "days_kept": days_to_keep,
            "message": f"Cleaned up {deleted_count} old notifications (older than {days_to_keep} days)",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def create_test_notification(
    title: str = Query(description="Test notification title"),
    message: str = Query(description="Test notification message"),
    severity: str = Query(default="info", description="Notification severity"),
    client_id: Optional[str] = Query(default=None, description="Optional client ID"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a test notification (for development/testing)
    """
    try:
        # Parse severity
        try:
            severity_enum = NotificationSeverity(severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity '{severity}'. Valid values: info, warning, critical, error"
            )
        
        admin_service = AdminNotificationService(db)
        
        notification_id = await admin_service.create_notification(
            title=title,
            message=message,
            severity=severity_enum,
            source="test_api",
            client_id=client_id,
            data={"test": True, "created_via": "api"}
        )
        
        return {
            "success": True,
            "notification_id": notification_id,
            "message": f"Test notification created: {title}",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def notifications_health_check(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Health check for admin notifications system
    """
    try:
        admin_service = AdminNotificationService(db)
        
        # Test basic functionality
        test_summary = await admin_service.get_notification_summary()
        
        return {
            "service": "admin_notifications",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "summary_available": bool(test_summary),
            "message": "Admin notifications system is operational"
        }
        
    except Exception as e:
        logger.error(f"Admin notifications health check failed: {e}")
        return {
            "service": "admin_notifications",
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Admin notifications system has issues"
        }