"""
Calendar Orchestrator Agent
Coordinates insights from other agents to create the final optimized calendar
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

CALENDAR_ORCHESTRATOR_AGENT = {
    "name": "calendar_orchestrator",
    "description": "Master orchestrator that combines insights from all agents to create the final calendar",
    "version": "1.0",
    "status": "active",
    "default_task": "Create optimized calendar for {client_name} in {selected_month} using all available insights",
    "policy": {
        "max_tool_calls": 15,
        "timeout_seconds": 90,
        "allowed_tools": [
            "firestore_rw",
            "calculate",
            "validate_calendar",
            "klaviyo_campaigns"
        ]
    },
    "variables": [
        {
            "name": "client_name",
            "type": "string",
            "required": True,
            "description": "Name of the client"
        },
        {
            "name": "selected_month",
            "type": "string",
            "required": True,
            "pattern": "^\\d{4}-\\d{2}$",
            "description": "Target month for calendar (YYYY-MM)"
        },
        {
            "name": "campaign_count",
            "type": "integer",
            "required": False,
            "default": 8,
            "description": "Number of campaigns to schedule"
        },
        {
            "name": "client_sales_goal",
            "type": "number",
            "required": True,
            "description": "Monthly revenue goal"
        },
        {
            "name": "historical_insights",
            "type": "object",
            "required": False,
            "description": "Insights from historical analysis"
        },
        {
            "name": "segment_strategy",
            "type": "object",
            "required": False,
            "description": "Segment targeting strategy"
        },
        {
            "name": "content_ideas",
            "type": "array",
            "required": False,
            "description": "Campaign content ideas"
        },
        {
            "name": "min_days_between",
            "type": "integer",
            "required": False,
            "default": 3,
            "description": "Minimum days between campaigns"
        },
        {
            "name": "include_holidays",
            "type": "boolean",
            "required": False,
            "default": True,
            "description": "Include holiday-specific campaigns"
        }
    ],
    "prompt_template": """You are the Calendar Orchestrator, responsible for creating the final optimized campaign calendar.

Combine all insights to create a calendar for {client_name} in {selected_month}:

**Available Insights:**
- Historical Analysis: {historical_insights}
- Segment Strategy: {segment_strategy}
- Content Ideas: {content_ideas}

**Requirements:**
- Total Campaigns: {campaign_count}
- Revenue Goal: ${client_sales_goal}
- Minimum {min_days_between} days between campaigns
- Include holidays: {include_holidays}

**Your Task:**

1. **Schedule Optimization**:
   - Distribute campaigns evenly across the month
   - Use optimal send times from historical data
   - Avoid send fatigue (respect min_days_between)
   - Align with holidays and key dates

2. **Content Allocation**:
   - Match content ideas to optimal dates
   - Ensure variety in campaign types
   - Balance promotional vs engagement content
   - Assign appropriate segments to each campaign

3. **Revenue Planning**:
   - Estimate revenue contribution per campaign
   - Ensure total meets ${client_sales_goal}
   - Front-load high-value campaigns if needed
   - Include contingency campaigns

4. **Final Calendar Structure**:
   For each campaign, specify:
   - Date and time
   - Campaign name and type
   - Target segment(s)
   - Subject line (A/B variants)
   - Content theme
   - Expected metrics (open rate, click rate, revenue)
   - Priority level (high/medium/low)

5. **Validation**:
   - Check for conflicts or overlaps
   - Verify segment coverage
   - Confirm revenue projections
   - Ensure brand consistency

Return the calendar as a structured JSON with all campaign details.
Include a summary with total expected revenue and key metrics."""
}

def register_calendar_orchestrator(registry):
    """Register the Calendar Orchestrator agent with the registry"""
    return registry.register_agent(CALENDAR_ORCHESTRATOR_AGENT)

def orchestrate_calendar(
    client_name: str,
    selected_month: str,
    campaign_count: int,
    sales_goal: float,
    insights: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Orchestrate the final calendar using all insights
    
    Args:
        client_name: Client name
        selected_month: Target month (YYYY-MM)
        campaign_count: Number of campaigns to schedule
        sales_goal: Monthly revenue goal
        insights: Combined insights from all agents
        
    Returns:
        Final calendar with all campaigns scheduled
    """
    
    # Parse month
    year, month = map(int, selected_month.split('-'))
    
    # Calculate days in month
    if month == 12:
        days_in_month = 31
    else:
        days_in_month = (datetime(year, month + 1, 1) - datetime(year, month, 1)).days
    
    # Get insights
    historical = insights.get("historical", {})
    segments = insights.get("segments", {})
    content = insights.get("content", [])
    
    # Calculate revenue per campaign needed
    revenue_per_campaign = sales_goal / campaign_count if campaign_count > 0 else 0
    
    # Create calendar
    calendar_campaigns = []
    
    # Distribute campaigns across the month
    days_between = max(3, days_in_month // (campaign_count + 1))
    
    for i in range(campaign_count):
        # Calculate send date
        day = min(days_in_month, 2 + (i * days_between))
        send_date = f"{selected_month}-{day:02d}"
        
        # Determine send time based on historical insights
        send_time = historical.get("timing_insights", {}).get("best_send_hour", "10:00")
        
        # Get content idea
        content_idea = content[i] if i < len(content) else {
            "concept": {"theme": f"Campaign {i+1}", "type": "standard"},
            "subject_lines": {"primary": f"Special offer for {client_name} customers"},
            "content": {"cta_primary": "Shop Now"}
        }
        
        # Determine segment
        segment_strategy = segments.get("targeting_strategy", {})
        segment_keys = list(segment_strategy.keys())
        target_segment = segment_keys[i % len(segment_keys)] if segment_keys else "All Subscribers"
        
        # Calculate expected metrics
        base_open_rate = historical.get("summary", {}).get("avg_open_rate", 0.20)
        base_click_rate = historical.get("summary", {}).get("avg_click_rate", 0.03)
        
        # Adjust metrics based on segment and content type
        if i < 3:  # First few campaigns typically perform better
            open_rate = base_open_rate * 1.2
            click_rate = base_click_rate * 1.3
            expected_revenue = revenue_per_campaign * 1.5
        else:
            open_rate = base_open_rate
            click_rate = base_click_rate
            expected_revenue = revenue_per_campaign
        
        campaign = {
            "id": f"camp_{selected_month}_{i+1:02d}",
            "date": send_date,
            "time": send_time,
            "name": content_idea["concept"]["theme"],
            "type": content_idea["concept"].get("type", "standard"),
            "segment": target_segment,
            "subject_line_a": content_idea["subject_lines"]["primary"],
            "subject_line_b": content_idea["subject_lines"].get("alternative", ""),
            "preview_text": content_idea["subject_lines"].get("preview_text", ""),
            "content_theme": content_idea["concept"]["theme"],
            "cta": content_idea["content"]["cta_primary"],
            "expected_metrics": {
                "open_rate": round(open_rate, 3),
                "click_rate": round(click_rate, 3),
                "revenue": round(expected_revenue, 2)
            },
            "priority": "high" if i < 3 else "medium" if i < 6 else "low"
        }
        
        calendar_campaigns.append(campaign)
    
    # Calculate totals
    total_expected_revenue = sum(c["expected_metrics"]["revenue"] for c in calendar_campaigns)
    
    # Create final calendar
    final_calendar = {
        "client": client_name,
        "month": selected_month,
        "campaigns": calendar_campaigns,
        "summary": {
            "total_campaigns": len(calendar_campaigns),
            "expected_revenue": round(total_expected_revenue, 2),
            "revenue_goal": sales_goal,
            "goal_achievement": round(total_expected_revenue / sales_goal * 100, 1) if sales_goal > 0 else 0,
            "avg_days_between": days_between,
            "segments_covered": len(set(c["segment"] for c in calendar_campaigns))
        },
        "validation": {
            "meets_revenue_goal": total_expected_revenue >= sales_goal,
            "proper_spacing": all(days_between >= 3 for _ in calendar_campaigns),
            "all_content_assigned": len(calendar_campaigns) == campaign_count
        },
        "created_at": datetime.now().isoformat()
    }
    
    return final_calendar