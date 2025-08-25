"""
Calendar tools for LangGraph workflow
Provides safe read and mock write operations
"""
from typing import Dict, Any, List
from langchain_core.tools import tool
import json
import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


@tool
def analyze_metrics(brand: str, timeframe: str = "last_30_days") -> Dict[str, Any]:
    """
    Analyze campaign metrics for a brand
    
    Args:
        brand: Brand name to analyze
        timeframe: Time period for analysis (e.g., "last_30_days", "last_quarter")
    
    Returns:
        Dict containing analyzed metrics
    """
    logger.info(f"Analyzing metrics for brand: {brand}, timeframe: {timeframe}")
    
    # Mock metrics data (safe read operation)
    return {
        "brand": brand,
        "timeframe": timeframe,
        "metrics": {
            "open_rate": round(random.uniform(0.15, 0.35), 3),
            "click_rate": round(random.uniform(0.02, 0.08), 3),
            "conversion_rate": round(random.uniform(0.01, 0.04), 3),
            "revenue": round(random.uniform(10000, 50000), 2),
            "sends": random.randint(5000, 50000),
            "best_performing_day": random.choice(["Tuesday", "Wednesday", "Thursday"]),
            "best_performing_time": f"{random.randint(9, 11)}:00 AM"
        },
        "trends": {
            "open_rate_trend": random.choice(["increasing", "stable", "decreasing"]),
            "engagement_score": round(random.uniform(0.6, 0.9), 2)
        },
        "analyzed_at": datetime.now().isoformat()
    }


@tool
def generate_calendar(brand: str, month: str, campaign_types: List[str] = None) -> Dict[str, Any]:
    """
    Generate a campaign calendar for a brand and month
    
    Args:
        brand: Brand name
        month: Target month (e.g., "March 2025")
        campaign_types: List of campaign types to include
    
    Returns:
        Dict containing generated calendar
    """
    logger.info(f"Generating calendar for brand: {brand}, month: {month}")
    
    if campaign_types is None:
        campaign_types = ["promotional", "newsletter", "product_launch", "seasonal"]
    
    # Generate mock calendar events
    events = []
    base_date = datetime.now().replace(day=1)
    
    for i in range(4):  # Generate 4 events
        event_date = base_date + timedelta(days=random.randint(1, 28))
        events.append({
            "id": f"event_{i+1}",
            "date": event_date.strftime("%Y-%m-%d"),
            "time": f"{random.randint(9, 16)}:00",
            "type": random.choice(campaign_types),
            "subject": f"{brand} {random.choice(['Sale', 'Newsletter', 'Product Launch', 'Special Offer'])}",
            "status": "planned",
            "estimated_sends": random.randint(1000, 10000)
        })
    
    return {
        "brand": brand,
        "month": month,
        "events": sorted(events, key=lambda x: x["date"]),
        "total_campaigns": len(events),
        "generated_at": datetime.now().isoformat()
    }


@tool
def read_calendar_events(brand: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """
    Read calendar events with optional filters (safe read operation)
    
    Args:
        brand: Optional brand filter
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        List of calendar events
    """
    logger.info(f"Reading calendar events - brand: {brand}, start: {start_date}, end: {end_date}")
    
    # Mock existing events (safe read)
    mock_events = [
        {
            "id": "existing_1",
            "brand": "TestBrand",
            "date": "2025-01-15",
            "type": "newsletter",
            "subject": "January Newsletter",
            "status": "sent"
        },
        {
            "id": "existing_2",
            "brand": "TestBrand",
            "date": "2025-01-22",
            "type": "promotional",
            "subject": "Winter Sale",
            "status": "scheduled"
        }
    ]
    
    # Apply filters
    filtered_events = mock_events
    if brand:
        filtered_events = [e for e in filtered_events if e.get("brand") == brand]
    
    return filtered_events


@tool
def mock_create_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock write operation for creating calendar events (doesn't actually persist)
    
    Args:
        event_data: Event data to create
    
    Returns:
        Dict with creation confirmation
    """
    logger.info(f"Mock creating event: {json.dumps(event_data, indent=2)}")
    
    # This is a mock write - doesn't actually persist
    return {
        "status": "mock_created",
        "message": "Event created in mock mode (not persisted)",
        "event": {
            **event_data,
            "id": f"mock_{datetime.now().timestamp()}",
            "created_at": datetime.now().isoformat()
        }
    }


@tool
def optimize_send_time(brand: str, campaign_type: str, historical_data: bool = True) -> Dict[str, Any]:
    """
    Optimize send time for a campaign based on historical data
    
    Args:
        brand: Brand name
        campaign_type: Type of campaign
        historical_data: Whether to use historical data
    
    Returns:
        Dict with optimized send time recommendations
    """
    logger.info(f"Optimizing send time for {brand} - {campaign_type}")
    
    # Mock optimization results
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    recommendations = {
        "brand": brand,
        "campaign_type": campaign_type,
        "recommendations": {
            "best_day": random.choice(days_of_week),
            "best_time": f"{random.randint(9, 11)}:00 AM",
            "timezone": "EST",
            "confidence_score": round(random.uniform(0.7, 0.95), 2)
        },
        "alternative_times": [
            {
                "day": random.choice(days_of_week),
                "time": f"{random.randint(14, 16)}:00 PM",
                "score": round(random.uniform(0.6, 0.8), 2)
            }
        ],
        "based_on": "historical_data" if historical_data else "industry_benchmarks",
        "analyzed_at": datetime.now().isoformat()
    }
    
    return recommendations


def get_calendar_tools():
    """
    Get all calendar tools for the workflow
    
    Returns:
        List of tool functions
    """
    return [
        analyze_metrics,
        generate_calendar,
        read_calendar_events,
        mock_create_event,
        optimize_send_time
    ]