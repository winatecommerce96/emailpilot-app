"""
Calendar Planner Agent for Email and SMS Campaign Planning
"""
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta
import calendar

CALENDAR_PLANNER_AGENT = {
    "name": "calendar_planner",
    "description": "Expert calendar planner for email and SMS campaigns with 10 years experience",
    "version": "1.0",
    "status": "active",
    "default_task": "Create campaign calendar for {client_name} for {selected_month}",
    "policy": {
        "max_tool_calls": 20,
        "timeout_seconds": 120,
        "allowed_tools": [
            "klaviyo_campaigns", 
            "klaviyo_segments", 
            "firestore_ro", 
            "calculate",
            "generate_campaign_ideas"
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
            "description": "Month to plan campaigns for (YYYY-MM format)"
        },
        {
            "name": "client_sales_goal",
            "type": "number",
            "required": True,
            "description": "Sales goal for the month in dollars"
        },
        {
            "name": "affinity_segment_1_name",
            "type": "string",
            "required": True,
            "description": "Primary affinity segment name"
        },
        {
            "name": "affinity_segment_1_target",
            "type": "number",
            "default": 70,
            "description": "Revenue percentage target for primary segment"
        },
        {
            "name": "affinity_segment_2_name",
            "type": "string",
            "required": True,
            "description": "Secondary affinity segment name"
        },
        {
            "name": "affinity_segment_2_target",
            "type": "number",
            "default": 30,
            "description": "Revenue percentage target for secondary segment"
        },
        {
            "name": "affinity_segment_3_name",
            "type": "string",
            "required": False,
            "description": "Tertiary affinity segment name (optional)"
        },
        {
            "name": "affinity_segment_3_target",
            "type": "number",
            "default": 15,
            "description": "Revenue percentage target for tertiary segment"
        },
        {
            "name": "key_growth_objective",
            "type": "string",
            "required": True,
            "description": "Primary objective to promote above all else"
        },
        {
            "name": "key_dates",
            "type": "string",
            "required": False,
            "description": "Important dates for promotions (JSON format)"
        },
        {
            "name": "unengaged_segment_size",
            "type": "number",
            "required": False,
            "default": 0,
            "description": "Size of unengaged/churn-risk segment"
        }
    ],
    "prompt_template": """You have 10 years experience as a calendar planner for email and SMS campaigns. You know the best days of the week to send and to have full coverage across the month of the campaigns you plan. Below are your rules to create the absolute best plan for {client_name}:

Topic    Rule
Calendar scope    Create 20 email and 4 SMS campaign ideas for {selected_month}.
Send-caps    Standard: max 2 total emails per account per week. Exception: subscribers tagged unengaged or churn-risk may receive 2 + promotional sends over the course of a month to drive re-engagement.
List health    Include at least one send to the entire mailable list; monitor % unengaged and flag deliverability risks.
Promos vs nurture    Only one multi-day promo (see "Key Dates"); all other sends are nurture/education with no discount.
Sales target    Hit ${client_sales_goal} in revenue Klaviyo-attributed revenue. Revenue mix (for clients with 3 affinity values): {affinity_segment_1_name} {affinity_segment_1_target}% · {affinity_segment_2_name} {affinity_segment_2_target}% · {affinity_segment_3_name} {affinity_segment_3_target}%.
Revenue mix (for clients with 2 affinity values): {affinity_segment_1_name} {affinity_segment_1_target}% · {affinity_segment_2_name} {affinity_segment_2_target}%.
Pull affinity segment descriptions if necessary.
Affinity groups    Every send must clearly map to one (or more) of: {affinity_segment_1_name}, {affinity_segment_2_name}, {affinity_segment_3_name} if it exists.
Primary Objective    Above all else, it's important to promote the {key_growth_objective}

Additional context:
- Current unengaged segment size: {unengaged_segment_size}
- Key promotional dates: {key_dates}

Create a comprehensive campaign calendar with:
1. Strategic distribution across the month
2. Optimal send times based on historical performance
3. Clear segmentation strategy
4. A/B testing recommendations
5. Subject lines and preview text that drive engagement
6. Hero content and CTAs aligned with objectives

Once done with the plan:
Parse the campaign items table rows into a JSON array. Each line is a tab-separated row.
                    
Field order: Week | Send Date | Send Time | Segment(s) | Subject Line A/B | Preview Text | Hero H1 | Sub-head | Hero Image | CTA Copy | Offer | A/B Test Idea | Secondary Message/SMS
                    
Return JSON with camelCase keys: week, sendDate, sendTime, segments, subjectLineAB, previewText, heroH1, subhead, heroImage, ctaCopy, offer, abTestIdea, secondaryMessageSMS"""
}


def register_calendar_planner(registry):
    """Register the Calendar Planner agent with the registry"""
    return registry.register_agent(CALENDAR_PLANNER_AGENT)


def format_campaign_plan(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parse the agent's output into structured campaign data
    """
    campaigns = []
    lines = raw_output.strip().split('\n')
    
    for line in lines:
        if '\t' in line:  # Tab-separated values
            parts = line.split('\t')
            if len(parts) >= 13:
                campaign = {
                    "week": parts[0],
                    "sendDate": parts[1],
                    "sendTime": parts[2],
                    "segments": parts[3],
                    "subjectLineAB": parts[4],
                    "previewText": parts[5],
                    "heroH1": parts[6],
                    "subhead": parts[7],
                    "heroImage": parts[8],
                    "ctaCopy": parts[9],
                    "offer": parts[10],
                    "abTestIdea": parts[11] if len(parts) > 11 else "",
                    "secondaryMessageSMS": parts[12] if len(parts) > 12 else ""
                }
                campaigns.append(campaign)
    
    return campaigns


def validate_campaign_plan(plan: List[Dict[str, Any]], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the campaign plan against requirements
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    
    # Count campaigns by type
    email_count = sum(1 for c in plan if 'SMS' not in c.get('secondaryMessageSMS', ''))
    sms_count = sum(1 for c in plan if 'SMS' in c.get('secondaryMessageSMS', ''))
    
    validation["stats"]["email_campaigns"] = email_count
    validation["stats"]["sms_campaigns"] = sms_count
    
    # Check requirements
    if email_count < 20:
        validation["errors"].append(f"Only {email_count} email campaigns planned (required: 20)")
        validation["valid"] = False
    
    if sms_count < 4:
        validation["warnings"].append(f"Only {sms_count} SMS campaigns planned (recommended: 4)")
    
    # Check weekly send limits
    weekly_sends = {}
    for campaign in plan:
        week = campaign.get("week", "")
        if week:
            weekly_sends[week] = weekly_sends.get(week, 0) + 1
    
    for week, count in weekly_sends.items():
        if count > 2:
            validation["warnings"].append(f"Week {week} has {count} sends (limit: 2 per week)")
    
    return validation