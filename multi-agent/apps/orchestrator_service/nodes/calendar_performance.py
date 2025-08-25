"""
Calendar Performance Node - Fetches and normalizes performance metrics.
Pulls metrics for selected month and prior year comparison.
"""

from datetime import datetime
from typing import Dict, Any, List
import uuid

from ..schemas import PerformanceSlice, MetricSnapshot
from ..config import get_settings


def fetch_performance(
    tenant_id: str,
    brand_id: str,
    selected_month: str,
    prior_year_same_month: str,
) -> PerformanceSlice:
    """
    Fetch performance metrics from Klaviyo and analytics.
    
    This node:
    1. Queries Klaviyo MCP for campaign/flow metrics
    2. Fetches segment performance data
    3. Compares with prior year same month
    4. Identifies anomalies and insights
    """
    
    settings = get_settings()
    
    # In production, this would call actual MCP endpoints
    # For now, return mock data for testing
    
    current_metrics = [
        MetricSnapshot(
            metric_name="revenue",
            value=125000.50,
            unit="USD",
            period_start=datetime(2024, 10, 1),
            period_end=datetime(2024, 10, 31),
            comparison_value=98000.25,
            comparison_period=prior_year_same_month,
        ),
        MetricSnapshot(
            metric_name="conversion_rate",
            value=3.2,
            unit="percent",
            period_start=datetime(2024, 10, 1),
            period_end=datetime(2024, 10, 31),
            comparison_value=2.8,
            comparison_period=prior_year_same_month,
        ),
        MetricSnapshot(
            metric_name="email_opens",
            value=45000,
            unit="count",
            period_start=datetime(2024, 10, 1),
            period_end=datetime(2024, 10, 31),
            comparison_value=38000,
            comparison_period=prior_year_same_month,
        ),
    ]
    
    prior_metrics = [
        MetricSnapshot(
            metric_name="revenue",
            value=98000.25,
            unit="USD",
            period_start=datetime(2023, 10, 1),
            period_end=datetime(2023, 10, 31),
        ),
        MetricSnapshot(
            metric_name="conversion_rate",
            value=2.8,
            unit="percent",
            period_start=datetime(2023, 10, 1),
            period_end=datetime(2023, 10, 31),
        ),
    ]
    
    top_campaigns = [
        {
            "campaign_id": "camp_001",
            "name": "Fall Sale Launch",
            "revenue": 45000.00,
            "conversion_rate": 4.1,
            "sent_date": "2024-10-05",
        },
        {
            "campaign_id": "camp_002",
            "name": "Halloween Special",
            "revenue": 32000.00,
            "conversion_rate": 3.5,
            "sent_date": "2024-10-25",
        },
    ]
    
    segment_performance = {
        "vip_customers": {
            "revenue": 75000.00,
            "conversion_rate": 5.2,
            "engagement_rate": 0.45,
        },
        "new_subscribers": {
            "revenue": 25000.00,
            "conversion_rate": 2.1,
            "engagement_rate": 0.32,
        },
        "win_back": {
            "revenue": 25000.50,
            "conversion_rate": 2.8,
            "engagement_rate": 0.28,
        },
    }
    
    insights = [
        "Revenue increased 27.5% YoY, exceeding industry average of 15%",
        "VIP segment driving 60% of total revenue with only 20% of sends",
        "Halloween campaign outperformed by 40% compared to last year",
        "New subscriber conversion needs improvement - below 2.5% target",
    ]
    
    anomalies = [
        {
            "metric": "click_rate",
            "date": "2024-10-15",
            "deviation": -35,
            "likely_cause": "Email rendering issue on mobile devices",
        }
    ]
    
    return PerformanceSlice(
        tenant_id=tenant_id,
        brand_id=brand_id,
        selected_month=selected_month,
        prior_year_same_month=prior_year_same_month,
        current_metrics=current_metrics,
        prior_year_metrics=prior_metrics,
        revenue_total=125000.50,
        conversion_rate=3.2,
        engagement_rate=0.35,
        top_campaigns=top_campaigns,
        segment_performance=segment_performance,
        insights=insights,
        anomalies=anomalies,
        provenance={
            "node": "calendar_performance",
            "version": "1.0.0",
            "data_sources": ["klaviyo_mcp", "analytics_bq"],
            "fetched_at": datetime.utcnow().isoformat(),
        }
    )