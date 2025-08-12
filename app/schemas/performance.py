"""
Performance-related Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

class PeriodInfo(BaseModel):
    """Time period information"""
    start: str
    end: str
    days_passed: int
    days_remaining: int
    days_in_month: int
    progress_percentage: float

class RevenueMetrics(BaseModel):
    """Revenue performance metrics"""
    mtd: float
    daily_average: float
    projected_eom: float
    last_30_days: float
    yoy_change: float

class OrderMetrics(BaseModel):
    """Order performance metrics"""
    mtd: int
    daily_average: float
    average_order_value: float
    conversion_rate: float

class EmailPerformance(BaseModel):
    """Email performance metrics"""
    emails_sent: int
    unique_opens: int
    unique_clicks: int
    open_rate: float
    click_rate: float
    click_to_open_rate: float
    bounced: int
    unsubscribed: int

class BestPerformer(BaseModel):
    """Best performing campaign/flow"""
    name: str
    revenue: float
    open_rate: Optional[float] = None
    click_rate: Optional[float] = None
    messages_sent: Optional[int] = None

class CampaignMetrics(BaseModel):
    """Campaign metrics"""
    sent: int
    scheduled: int
    draft: int
    best_performer: BestPerformer

class FlowMetrics(BaseModel):
    """Flow metrics"""
    active: int
    total_revenue: float
    top_performer: BestPerformer

class SegmentMetrics(BaseModel):
    """Segment metrics"""
    vip_customers: int
    engaged_30_days: int
    at_risk: int
    win_back_eligible: int

class MTDData(BaseModel):
    """Month-to-date performance data"""
    period: PeriodInfo
    revenue: RevenueMetrics
    orders: OrderMetrics
    email_performance: EmailPerformance
    campaigns: CampaignMetrics
    flows: FlowMetrics
    segments: SegmentMetrics

class YTDData(BaseModel):
    """Year-to-date summary"""
    revenue: float
    orders: float
    emails_sent: int
    campaigns_sent: int

class PerformanceResponse(BaseModel):
    """Performance API response"""
    client_id: str
    mtd: MTDData
    ytd: YTDData
    data_source: str = "mock"
    timestamp: str
    error: Optional[str] = None

class HistoricalMonth(BaseModel):
    """Historical monthly data"""
    year: int
    month: int
    month_name: str
    revenue: float
    orders: int
    avg_order_value: float
    emails_sent: int
    open_rate: float
    click_rate: float
    conversion_rate: float

class HistoricalSummary(BaseModel):
    """Historical data summary"""
    average_monthly_revenue: float
    total_revenue: float
    growth_rate: float

class HistoricalResponse(BaseModel):
    """Historical performance response"""
    client_id: str
    period: str
    data: List[HistoricalMonth]
    summary: HistoricalSummary