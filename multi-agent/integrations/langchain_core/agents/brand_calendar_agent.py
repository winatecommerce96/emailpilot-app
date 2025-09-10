"""
Brand Calendar Agent
Pulls client collection fields from Firestore to inform calendar event planning
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json

BRAND_CALENDAR_AGENT = {
    "name": "brand_calendar",
    "description": "Brand specialist that retrieves client-specific brand events, affinity segments, and style preferences from Firestore",
    "version": "1.0",
    "status": "active",
    "default_task": "Retrieve brand configuration and affinity segments for {client_name} from Firestore",
    "policy": {
        "max_tool_calls": 8,
        "timeout_seconds": 30,
        "allowed_tools": [
            "firestore_ro",
            "firestore_rw",
            "calculate"
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
            "name": "client_id",
            "type": "string",
            "required": True,
            "description": "Client identifier for Firestore lookup"
        },
        {
            "name": "selected_month",
            "type": "string",
            "required": False,
            "pattern": "^\\d{4}-\\d{2}$",
            "description": "Target month for seasonal events (YYYY-MM)"
        },
        {
            "name": "additional_context",
            "type": "string",
            "required": False,
            "description": "Additional context about important dates, events, or business considerations"
        }
    ],
    "prompt_template": """You are a Brand Calendar Specialist responsible for retrieving and organizing brand-specific information.

Your task is to gather brand configuration for {client_name} (ID: {client_id}):

{additional_context}

Consider the above context when planning campaigns.

1. **Client Collection Data**:
   - Retrieve the client document from Firestore 'clients' collection
   - Extract brand events, product launches, and key dates
   - Identify affinity segments and their characteristics

2. **Affinity Segments to Look For**:
   - VIP Customers (high value, frequent purchasers)
   - Regular Buyers (consistent engagement)
   - New Subscribers (recent signups, < 90 days)
   - Re-engagement (dormant, need win-back)
   - Seasonal Shoppers (holiday-specific)
   - Loyalty Members (rewards program)

3. **Brand Events & Themes**:
   - Annual sales events (Black Friday, Anniversary, etc.)
   - Product launch schedules
   - Seasonal campaigns
   - Industry-specific events
   - Brand milestones

4. **Visual Identity**:
   - Brand colors (primary, secondary, accent)
   - Style preferences (modern, classic, playful, etc.)
   - Tone of voice indicators
   
5. **Calendar Preferences**:
   - Preferred send days/times
   - Blackout dates
   - Campaign frequency limits
   - Segment-specific rules

Return structured data including:
- affinity_segments: List of segments with criteria
- brand_events: Key dates and events for the selected month
- brand_colors: Color palette for visual consistency
- campaign_rules: Preferences and restrictions
- seasonal_themes: Month-specific themes and focus areas"""
}

def map_klaviyo_segments_to_affinity(klaviyo_segments: List[Dict]) -> List[Dict[str, Any]]:
    """
    Map Klaviyo segments to affinity categories for calendar planning
    
    Args:
        klaviyo_segments: Raw segments data from Klaviyo API
        
    Returns:
        List of affinity segment dictionaries
    """
    affinity_segments = []
    
    # Define mapping rules based on segment names/definitions
    for segment in klaviyo_segments:
        segment_name = segment.get("name", "").lower()
        segment_id = segment.get("id", "")
        profile_count = segment.get("profile_count", 0)
        
        # Map based on common naming patterns
        if any(vip in segment_name for vip in ["vip", "high value", "platinum", "gold"]):
            affinity_segments.append({
                "name": segment.get("name", "VIP Customers"),
                "id": segment_id,
                "klaviyo_id": segment_id,
                "criteria": {
                    "min_ltv": 500,
                    "min_orders": 3,
                    "engagement": "high",
                    "profile_count": profile_count
                },
                "color_opacity": 1.0,
                "priority": 1,
                "emoji": "⭐",
                "campaign_frequency": "weekly"
            })
        elif any(regular in segment_name for regular in ["regular", "active", "engaged", "repeat"]):
            affinity_segments.append({
                "name": segment.get("name", "Regular Buyers"),
                "id": segment_id,
                "klaviyo_id": segment_id,
                "criteria": {
                    "min_ltv": 100,
                    "min_orders": 1,
                    "engagement": "medium",
                    "profile_count": profile_count
                },
                "color_opacity": 0.75,
                "priority": 2,
                "emoji": "💎",
                "campaign_frequency": "bi-weekly"
            })
        elif any(new in segment_name for new in ["new", "welcome", "recent", "subscriber"]):
            affinity_segments.append({
                "name": segment.get("name", "New Subscribers"),
                "id": segment_id,
                "klaviyo_id": segment_id,
                "criteria": {
                    "days_since_signup": 90,
                    "orders": 0,
                    "engagement": "unknown",
                    "profile_count": profile_count
                },
                "color_opacity": 0.5,
                "priority": 3,
                "emoji": "🆕",
                "campaign_frequency": "weekly"
            })
        elif any(winback in segment_name for winback in ["winback", "re-engage", "dormant", "inactive", "lapsed"]):
            affinity_segments.append({
                "name": segment.get("name", "Re-engagement"),
                "id": segment_id,
                "klaviyo_id": segment_id,
                "criteria": {
                    "days_inactive": 180,
                    "past_purchaser": True,
                    "engagement": "low",
                    "profile_count": profile_count
                },
                "color_opacity": 0.35,
                "priority": 4,
                "emoji": "🔄",
                "campaign_frequency": "monthly"
            })
        else:
            # Generic segment mapping
            affinity_segments.append({
                "name": segment.get("name", "Custom Segment"),
                "id": segment_id,
                "klaviyo_id": segment_id,
                "criteria": {
                    "profile_count": profile_count,
                    "engagement": "varies"
                },
                "color_opacity": 0.6,
                "priority": 5,
                "emoji": "📧",
                "campaign_frequency": "weekly"
            })
    
    # Sort by priority
    affinity_segments.sort(key=lambda x: x.get("priority", 999))
    
    return affinity_segments[:10]  # Limit to top 10 segments

def register_brand_calendar(registry):
    """Register the Brand Calendar agent with the registry"""
    return registry.register_agent(BRAND_CALENDAR_AGENT)

def retrieve_brand_data(
    client_id: str,
    client_name: str,
    selected_month: Optional[str] = None,
    additional_context: str = "",
    use_real_data: bool = True
) -> Dict[str, Any]:
    """
    Retrieve brand configuration from Firestore and Klaviyo MCP
    
    Args:
        client_id: Client identifier
        client_name: Client display name
        selected_month: Target month for filtering events
        additional_context: Additional context from user about important dates/events
        use_real_data: Whether to fetch real data from MCP (default: True)
        
    Returns:
        Brand configuration dictionary
    """
    import asyncio
    import logging
    logger = logging.getLogger(__name__)
    
    # Parse month if provided
    if selected_month:
        year, month = map(int, selected_month.split('-'))
        month_name = datetime(year, month, 1).strftime("%B")
    else:
        month_name = "General"
    
    # Try to get real segments from MCP if enabled
    affinity_segments = []
    
    if use_real_data:
        try:
            # Import IntelligentQueryService for natural language queries
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "app" / "services"))
            from intelligent_query_service import IntelligentQueryService, QueryMode
            
            # Initialize query service
            query_service = IntelligentQueryService()
            
            # Fetch real segments from Klaviyo using natural language
            async def fetch_segments():
                try:
                    # Use natural language to get segments with engagement data
                    logger.info(f"Using intelligent query to fetch segments for {client_name}")
                    segments_result = await query_service.query(
                        natural_query="List all active segments with their sizes, engagement rates, and revenue metrics",
                        client_id=client_id,
                        mode=QueryMode.AUTO
                    )
                    
                    if segments_result.get("success") and segments_result.get("results"):
                        return segments_result["results"]
                    else:
                        logger.warning(f"Natural language query for segments returned no results")
                        return None
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch segments using intelligent query: {e}")
                    return None
            
            # Run async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If already in async context, create task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, fetch_segments())
                        segments_result = future.result(timeout=10)
                else:
                    segments_result = loop.run_until_complete(fetch_segments())
            except:
                segments_result = asyncio.run(fetch_segments())
            
            # Map Klaviyo segments to affinity categories
            if segments_result and isinstance(segments_result, list):
                affinity_segments = map_klaviyo_segments_to_affinity(segments_result)
                logger.info(f"Retrieved {len(affinity_segments)} segments from Klaviyo MCP")
            else:
                logger.warning("No segments retrieved from MCP, using defaults")
                
        except Exception as e:
            logger.warning(f"Could not fetch real segments from MCP: {e}, using defaults")
    
    # If no real segments or MCP disabled, use defaults
    if not affinity_segments:
        affinity_segments = [
            {
                "name": "VIP Customers",
                "id": "vip",
                "criteria": {
                    "min_ltv": 500,
                    "min_orders": 3,
                    "engagement": "high"
                },
                "color_opacity": 1.0,
                "priority": 1,
                "emoji": "⭐",
                "campaign_frequency": "weekly"
            },
            {
                "name": "Regular Buyers",
                "id": "regular",
                "criteria": {
                    "min_ltv": 100,
                    "min_orders": 1,
                    "engagement": "medium"
                },
                "color_opacity": 0.75,
                "priority": 2,
                "emoji": "💎",
                "campaign_frequency": "bi-weekly"
            },
            {
                "name": "New Subscribers",
                "id": "new",
                "criteria": {
                    "days_since_signup": 90,
                    "orders": 0,
                    "engagement": "unknown"
                },
                "color_opacity": 0.5,
                "priority": 3,
                "emoji": "🆕",
                "campaign_frequency": "weekly"
            },
            {
                "name": "Re-engagement",
                "id": "reengagement",
                "criteria": {
                    "days_inactive": 180,
                    "past_purchaser": True,
                    "engagement": "low"
                },
                "color_opacity": 0.35,
                "priority": 4,
                "emoji": "🔄",
                "campaign_frequency": "monthly"
            }
        ]
    
    # Default brand data structure
    brand_data = {
        "client_id": client_id,
        "client_name": client_name,
        "affinity_segments": affinity_segments,
        "brand_events": get_brand_events(client_id, selected_month),
        "brand_colors": {
            "promotional": {
                "primary": "#ff0080",
                "secondary": "#ff8c00",
                "gradient": "linear-gradient(45deg, #ff0080, #ff8c00)"
            },
            "content": {
                "primary": "#3369DC",
                "secondary": "#8A6CF7",
                "gradient": "linear-gradient(45deg, #3369DC, #8A6CF7)"
            },
            "engagement": {
                "primary": "#8A6CF7",
                "secondary": "#C5FF75",
                "gradient": "linear-gradient(45deg, #8A6CF7, #C5FF75)"
            },
            "seasonal": {
                "primary": "#C5FF75",
                "secondary": "#C5FF75",
                "gradient": "linear-gradient(45deg, #C5FF75, #8BED4F)"
            }
        },
        "campaign_rules": {
            "min_days_between": 3,
            "max_per_week": 3,
            "max_per_month": 12,
            "preferred_send_days": ["Tuesday", "Thursday", "Friday"],
            "preferred_send_times": ["10:00", "14:00", "19:00"],
            "blackout_dates": []
        },
        "seasonal_themes": get_seasonal_themes(selected_month),
        "additional_context": additional_context,  # Include user-provided context
        "retrieved_at": datetime.now().isoformat()
    }
    
    return brand_data

def get_brand_events(client_id: str, selected_month: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get brand-specific events for the month"""
    
    events = []
    
    # Parse month
    if selected_month:
        year, month = map(int, selected_month.split('-'))
        
        # Common retail events by month
        monthly_events = {
            1: [{"name": "New Year Sale", "date": 1, "type": "promotional"}],
            2: [{"name": "Valentine's Day", "date": 14, "type": "seasonal"}],
            3: [{"name": "Spring Launch", "date": 20, "type": "seasonal"}],
            4: [{"name": "Easter", "date": 15, "type": "seasonal"}],
            5: [{"name": "Mother's Day", "date": 12, "type": "seasonal"}],
            6: [{"name": "Summer Sale", "date": 21, "type": "promotional"}],
            7: [{"name": "Mid-Summer", "date": 15, "type": "promotional"}],
            8: [{"name": "Back to School", "date": 15, "type": "seasonal"}],
            9: [{"name": "Fall Launch", "date": 22, "type": "seasonal"}],
            10: [{"name": "Halloween", "date": 31, "type": "seasonal"}],
            11: [{"name": "Black Friday", "date": 29, "type": "promotional"},
                 {"name": "Cyber Monday", "date": 32, "type": "promotional"}],
            12: [{"name": "Holiday Sale", "date": 15, "type": "seasonal"}]
        }
        
        if month in monthly_events:
            for event in monthly_events[month]:
                events.append({
                    "name": event["name"],
                    "date": f"{selected_month}-{event['date']:02d}",
                    "type": event["type"],
                    "priority": "high"
                })
    
    # Add client-specific events
    if "rogue" in client_id.lower() or "creamery" in client_id.lower():
        events.append({
            "name": "Cheese of the Month",
            "date": f"{selected_month}-05" if selected_month else "monthly",
            "type": "content",
            "priority": "medium"
        })
    
    return events

def get_seasonal_themes(selected_month: Optional[str] = None) -> Dict[str, Any]:
    """Get seasonal themes based on month"""
    
    if not selected_month:
        return {"theme": "general", "focus": "brand awareness"}
    
    year, month = map(int, selected_month.split('-'))
    
    seasonal_map = {
        1: {"theme": "new_year", "focus": "fresh starts", "emoji": "🎊"},
        2: {"theme": "valentine", "focus": "love & gifts", "emoji": "❤️"},
        3: {"theme": "spring", "focus": "renewal", "emoji": "🌸"},
        4: {"theme": "spring", "focus": "growth", "emoji": "🌱"},
        5: {"theme": "spring", "focus": "mothers", "emoji": "🌷"},
        6: {"theme": "summer", "focus": "adventure", "emoji": "☀️"},
        7: {"theme": "summer", "focus": "vacation", "emoji": "🏖️"},
        8: {"theme": "summer", "focus": "back-to-school", "emoji": "📚"},
        9: {"theme": "fall", "focus": "harvest", "emoji": "🍂"},
        10: {"theme": "fall", "focus": "halloween", "emoji": "🎃"},
        11: {"theme": "fall", "focus": "thanksgiving", "emoji": "🦃"},
        12: {"theme": "winter", "focus": "holidays", "emoji": "❄️"}
    }
    
    return seasonal_map.get(month, {"theme": "general", "focus": "engagement", "emoji": "📧"})

def get_email_type_emoji(email_type: str, segment: str = None) -> str:
    """Get emoji based on email type and segment"""
    
    # Type-based emojis
    type_emojis = {
        "promotional": "🎁",
        "content": "📝",
        "engagement": "💬",
        "seasonal": "🌟",
        "product_launch": "🚀",
        "loyalty": "💎",
        "survey": "📊",
        "welcome": "👋",
        "winback": "🔄",
        "flash_sale": "⚡",
        "exclusive": "🔐"
    }
    
    # Override with segment-specific emojis for VIP/New
    if segment == "vip":
        return "⭐"
    elif segment == "new":
        return "🆕"
    elif segment == "reengagement":
        return "🔄"
    
    return type_emojis.get(email_type, "📧")

def format_campaign_markdown(campaign: Dict[str, Any]) -> str:
    """Format campaign details as markdown"""
    
    markdown = f"""## {campaign.get('emoji', '📧')} {campaign.get('name', 'Campaign')}

**Date**: {campaign.get('date', 'TBD')} at {campaign.get('time', '10:00')}  
**Type**: {campaign.get('type', 'general')}  
**Segment**: {campaign.get('segment', 'All Subscribers')}  

### Subject Lines
- **A**: {campaign.get('subject_line_a', 'Subject A')}
- **B**: {campaign.get('subject_line_b', 'Subject B')}

### Content
{campaign.get('content_theme', 'General content')}

**CTA**: {campaign.get('cta', 'Shop Now')}

### Expected Performance
- **Open Rate**: {campaign.get('expected_metrics', {}).get('open_rate', 0.2):.1%}
- **Click Rate**: {campaign.get('expected_metrics', {}).get('click_rate', 0.03):.1%}
- **Revenue**: ${campaign.get('expected_metrics', {}).get('revenue', 0):,.0f}

**Priority**: {campaign.get('priority', 'medium')}
"""
    
    return markdown