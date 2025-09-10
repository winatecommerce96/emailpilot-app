"""
Historical Campaign Analyst Agent
Analyzes past campaign performance to identify patterns and insights
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

HISTORICAL_ANALYST_AGENT = {
    "name": "historical_analyst",
    "description": "Expert analyst specializing in historical campaign performance analysis and pattern recognition",
    "version": "1.0",
    "status": "active",
    "default_task": "Analyze historical campaign performance for {client_name} over the last {time_period}",
    "policy": {
        "max_tool_calls": 15,
        "timeout_seconds": 90,
        "allowed_tools": [
            "klaviyo_campaigns",
            "klaviyo_campaign_metrics", 
            "klaviyo_metrics_aggregate",
            "klaviyo_reporting_values",
            "firestore_ro",
            "calculate"
        ]
    },
    "variables": [
        {
            "name": "client_name",
            "type": "string",
            "required": True,
            "description": "Name of the client to analyze"
        },
        {
            "name": "time_period",
            "type": "string",
            "required": False,
            "default": "3 months",
            "description": "Time period to analyze (e.g., '3 months', '6 months', 'last quarter')"
        },
        {
            "name": "metrics_threshold",
            "type": "object",
            "required": False,
            "default": {
                "min_open_rate": 0.15,
                "min_click_rate": 0.02,
                "min_revenue": 1000
            },
            "description": "Thresholds for identifying successful campaigns"
        },
        {
            "name": "analysis_focus",
            "type": "string",
            "required": False,
            "default": "comprehensive",
            "description": "Focus area: comprehensive, revenue, engagement, timing, content"
        }
    ],
    "prompt_template": """You are an expert campaign analyst with 15 years of experience analyzing email marketing performance.

Your task is to analyze historical campaign data for {client_name} over {time_period} to identify:

1. **Performance Patterns**:
   - Best and worst performing campaigns
   - Average metrics across all campaigns
   - Trends over time (improving/declining)

2. **Timing Insights**:
   - Optimal send days and times
   - Seasonal patterns
   - Holiday campaign performance

3. **Content Analysis**:
   - Most successful subject line patterns
   - Best performing content types
   - Winning CTAs and offers

4. **Segment Performance**:
   - Which segments respond best
   - Segment-specific patterns
   - Cross-segment opportunities

5. **Revenue Drivers**:
   - Campaigns that drove highest revenue
   - Revenue per email patterns
   - Conversion rate insights

Use the metrics thresholds: {metrics_threshold}

Focus area: {analysis_focus}

Provide specific, data-driven insights that can inform future campaign planning.
Return your analysis in a structured format with clear sections and actionable recommendations.

IMPORTANT: Use actual data from Klaviyo tools, not hypothetical examples."""
}

def register_historical_analyst(registry):
    """Register the Historical Analyst agent with the registry"""
    return registry.register_agent(HISTORICAL_ANALYST_AGENT)

def analyze_campaign_history(campaigns: List[Dict[str, Any]], thresholds: Dict[str, float]) -> Dict[str, Any]:
    """
    Analyze campaign history and extract insights
    
    Args:
        campaigns: List of campaign data with metrics
        thresholds: Performance thresholds
        
    Returns:
        Dictionary with analysis results
    """
    if not campaigns:
        return {"error": "No campaigns to analyze"}
    
    # Calculate aggregate metrics
    total_campaigns = len(campaigns)
    avg_open_rate = sum(c.get("open_rate", 0) for c in campaigns) / total_campaigns
    avg_click_rate = sum(c.get("click_rate", 0) for c in campaigns) / total_campaigns
    total_revenue = sum(c.get("revenue", 0) for c in campaigns)
    
    # Find best performers
    best_by_revenue = max(campaigns, key=lambda x: x.get("revenue", 0))
    best_by_engagement = max(campaigns, key=lambda x: x.get("open_rate", 0) + x.get("click_rate", 0))
    
    # Identify patterns
    successful_campaigns = [
        c for c in campaigns 
        if c.get("open_rate", 0) >= thresholds.get("min_open_rate", 0.15)
        and c.get("click_rate", 0) >= thresholds.get("min_click_rate", 0.02)
    ]
    
    # Extract timing patterns
    send_times = {}
    for campaign in campaigns:
        if "send_time" in campaign:
            hour = campaign["send_time"].split(":")[0]
            send_times[hour] = send_times.get(hour, 0) + 1
    
    best_send_hour = max(send_times.items(), key=lambda x: x[1])[0] if send_times else "10"
    
    return {
        "summary": {
            "total_campaigns": total_campaigns,
            "avg_open_rate": round(avg_open_rate, 3),
            "avg_click_rate": round(avg_click_rate, 3),
            "total_revenue": round(total_revenue, 2),
            "success_rate": len(successful_campaigns) / total_campaigns if total_campaigns > 0 else 0
        },
        "top_performers": {
            "by_revenue": best_by_revenue,
            "by_engagement": best_by_engagement
        },
        "timing_insights": {
            "best_send_hour": f"{best_send_hour}:00",
            "send_time_distribution": send_times
        },
        "recommendations": [
            f"Focus on campaigns similar to '{best_by_revenue.get('name', 'top revenue campaign')}'",
            f"Optimal send time appears to be {best_send_hour}:00",
            f"Target minimum open rate of {thresholds['min_open_rate']*100}% for campaign success"
        ]
    }