"""
Variables API for Agent Development
Provides comprehensive variables from Firestore clients and time frames
Now includes LIVE Klaviyo data via MCP Gateway integration
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import httpx
import asyncio
from app.deps.firestore import get_db as get_firestore_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/variables", tags=["variables"])

# MCP Gateway configuration
MCP_GATEWAY_URL = "http://localhost:8000/api/mcp/gateway"

# Cache for MCP data (5 minute TTL)
mcp_cache = {}
cache_timestamps = {}


def get_time_frame_variables(selected_month: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate comprehensive time frame variables
    
    Args:
        selected_month: Format YYYY-MM (e.g., "2025-06")
    """
    now = datetime.now()
    
    # Parse selected month or use current
    if selected_month:
        try:
            selected_date = datetime.strptime(selected_month, "%Y-%m")
        except ValueError:
            selected_date = now
    else:
        selected_date = now
    
    # Calculate various time frames
    time_frames = {
        # Current time
        "current_date": now.strftime("%Y-%m-%d"),
        "current_datetime": now.isoformat(),
        "current_year": now.year,
        "current_month": now.month,
        "current_month_name": calendar.month_name[now.month],
        "current_quarter": (now.month - 1) // 3 + 1,
        
        # Selected month
        "selected_month": selected_date.strftime("%Y-%m"),
        "selected_month_full": selected_date.strftime("%B %Y"),
        "selected_month_start": selected_date.replace(day=1).strftime("%Y-%m-%d"),
        "selected_month_end": (selected_date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
        "selected_month_days": calendar.monthrange(selected_date.year, selected_date.month)[1],
        
        # Selected month - 1 year
        "selected_month_1y_ago": (selected_date - relativedelta(years=1)).strftime("%Y-%m"),
        "selected_month_1y_ago_full": (selected_date - relativedelta(years=1)).strftime("%B %Y"),
        "selected_month_1y_ago_start": (selected_date - relativedelta(years=1)).replace(day=1).strftime("%Y-%m-%d"),
        "selected_month_1y_ago_end": ((selected_date - relativedelta(years=1)).replace(day=1) + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
        
        # Selected month - 2 years
        "selected_month_2y_ago": (selected_date - relativedelta(years=2)).strftime("%Y-%m"),
        "selected_month_2y_ago_full": (selected_date - relativedelta(years=2)).strftime("%B %Y"),
        "selected_month_2y_ago_start": (selected_date - relativedelta(years=2)).replace(day=1).strftime("%Y-%m-%d"),
        "selected_month_2y_ago_end": ((selected_date - relativedelta(years=2)).replace(day=1) + relativedelta(months=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
        
        # Recent periods
        "last_30_days_start": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        "last_30_days_end": now.strftime("%Y-%m-%d"),
        "last_60_days_start": (now - timedelta(days=60)).strftime("%Y-%m-%d"),
        "last_90_days_start": (now - timedelta(days=90)).strftime("%Y-%m-%d"),
        "last_7_days_start": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
        
        # Previous periods
        "previous_month": (selected_date - relativedelta(months=1)).strftime("%Y-%m"),
        "previous_month_full": (selected_date - relativedelta(months=1)).strftime("%B %Y"),
        "previous_quarter_start": (selected_date - relativedelta(months=3)).replace(day=1).strftime("%Y-%m-%d"),
        "previous_year": selected_date.year - 1,
        
        # Year-to-date
        "ytd_start": selected_date.replace(month=1, day=1).strftime("%Y-%m-%d"),
        "ytd_end": selected_date.strftime("%Y-%m-%d"),
        
        # Fiscal periods (assuming fiscal year = calendar year)
        "fiscal_year": selected_date.year,
        "fiscal_quarter": (selected_date.month - 1) // 3 + 1,
        "fiscal_year_start": selected_date.replace(month=1, day=1).strftime("%Y-%m-%d"),
        "fiscal_year_end": selected_date.replace(month=12, day=31).strftime("%Y-%m-%d"),
        
        # Seasonal
        "season": get_season(selected_date.month),
        "is_holiday_season": selected_date.month in [11, 12],  # Nov-Dec
        "is_summer_season": selected_date.month in [6, 7, 8],
        
        # Week numbers
        "current_week_number": now.isocalendar()[1],
        "selected_month_week_start": selected_date.replace(day=1).isocalendar()[1],
    }
    
    return time_frames


def get_season(month: int) -> str:
    """Get season name for month"""
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Fall"


async def get_client_variables(client_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch all fields from Firestore clients collection
    
    Args:
        client_id: Optional specific client ID
    """
    try:
        db = get_firestore_client()
        
        if client_id:
            # Get specific client
            doc = db.collection('clients').document(client_id).get()
            if doc.exists:
                client_data = doc.to_dict()
                # Prefix all fields with client_
                return {f"client_{k}": v for k, v in client_data.items()}
            else:
                return {}
        else:
            # Get first client as example or aggregate
            clients = db.collection('clients').limit(1).stream()
            for client in clients:
                client_data = client.to_dict()
                # Prefix all fields with client_
                return {f"client_{k}": v for k, v in client_data.items()}
            
            # If no clients, return schema
            return {
                "client_id": "{{client_id}}",
                "client_name": "{{client_name}}",
                "client_email": "{{client_email}}",
                "client_status": "{{client_status}}",
                "client_klaviyo_api_key": "{{encrypted}}",
                "client_klaviyo_public_key": "{{public_key}}",
                "client_created_at": "{{timestamp}}",
                "client_updated_at": "{{timestamp}}",
                "client_industry": "{{industry}}",
                "client_timezone": "{{timezone}}",
                "client_currency": "{{currency}}",
                "client_monthly_email_limit": "{{limit}}",
                "client_monthly_sms_limit": "{{limit}}",
                "client_active_campaigns": "{{count}}",
                "client_total_revenue": "{{revenue}}",
                "client_average_order_value": "{{aov}}",
                "client_list_size": "{{subscribers}}",
                "client_engagement_rate": "{{percentage}}",
                "client_churn_rate": "{{percentage}}",
                "client_lifetime_value": "{{ltv}}",
                "client_segments": "{{segments}}",
                "client_tags": "{{tags}}",
                "client_notes": "{{notes}}"
            }
            
    except Exception as e:
        logger.error(f"Error fetching client variables: {e}")
        return {}


def get_performance_variables() -> Dict[str, Any]:
    """
    Generate performance metric variables
    """
    return {
        # Email metrics
        "email_open_rate": "{{email_open_rate}}",
        "email_click_rate": "{{email_click_rate}}",
        "email_conversion_rate": "{{email_conversion_rate}}",
        "email_bounce_rate": "{{email_bounce_rate}}",
        "email_unsubscribe_rate": "{{email_unsubscribe_rate}}",
        "email_spam_rate": "{{email_spam_rate}}",
        "email_revenue_per_recipient": "{{email_rpr}}",
        
        # SMS metrics
        "sms_click_rate": "{{sms_click_rate}}",
        "sms_conversion_rate": "{{sms_conversion_rate}}",
        "sms_opt_out_rate": "{{sms_opt_out_rate}}",
        "sms_revenue_per_recipient": "{{sms_rpr}}",
        
        # Revenue metrics
        "total_revenue": "{{total_revenue}}",
        "revenue_growth_rate": "{{revenue_growth}}",
        "revenue_per_customer": "{{revenue_per_customer}}",
        "average_order_value": "{{aov}}",
        "customer_lifetime_value": "{{clv}}",
        
        # List metrics
        "total_subscribers": "{{total_subscribers}}",
        "list_growth_rate": "{{list_growth_rate}}",
        "engaged_subscribers": "{{engaged_subscribers}}",
        "inactive_subscribers": "{{inactive_subscribers}}",
        
        # Segment metrics
        "vip_segment_size": "{{vip_segment_size}}",
        "at_risk_segment_size": "{{at_risk_segment_size}}",
        "new_customer_segment_size": "{{new_customer_segment_size}}",
        "repeat_customer_segment_size": "{{repeat_customer_segment_size}}"
    }


async def get_klaviyo_live_variables(client_id: str) -> Dict[str, Any]:
    """
    Fetch LIVE Klaviyo data via MCP Gateway
    Returns actual values from Klaviyo API, not placeholders
    """
    cache_key = f"klaviyo_{client_id}"
    now = datetime.now()
    
    # Check cache (5 minute TTL)
    if cache_key in mcp_cache and cache_key in cache_timestamps:
        if (now - cache_timestamps[cache_key]).seconds < 300:
            logger.info(f"Using cached Klaviyo data for client {client_id}")
            return mcp_cache[cache_key]
    
    logger.info(f"Fetching live Klaviyo data for client {client_id}")
    
    variables = {}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch campaigns
            try:
                campaigns_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "campaigns.list",
                        "arguments": {"page_size": 50},
                        "use_enhanced": True
                    }
                )
                if campaigns_response.status_code == 200:
                    campaigns_data = campaigns_response.json()
                    if campaigns_data.get("success") and campaigns_data.get("data"):
                        # Handle nested response structure from MCP gateway
                        inner_data = campaigns_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            campaign_list = inner_data["data"].get("data", [])
                        else:
                            campaign_list = []
                        
                        variables["klaviyo_campaign_count"] = len(campaign_list)
                        if campaign_list:
                            variables["klaviyo_campaign_names"] = [c.get("attributes", {}).get("name", "") for c in campaign_list[:5] if c.get("attributes", {}).get("name")]
                            variables["klaviyo_recent_campaigns"] = [c.get("attributes", {}).get("name", "") for c in campaign_list[:3] if c.get("attributes", {}).get("name")]
                        
                        # Get metrics for the most recent campaign
                        if campaign_list:
                            latest_campaign_id = campaign_list[0].get("id")
                            if latest_campaign_id:
                                metrics_response = await client.post(
                                    f"{MCP_GATEWAY_URL}/invoke",
                                    json={
                                        "client_id": client_id,
                                        "tool_name": "reporting.performance",
                                        "arguments": {
                                            "id": latest_campaign_id,
                                            "metrics": ["open_rate", "click_rate", "delivered"]
                                        },
                                        "use_enhanced": True
                                    }
                                )
                                if metrics_response.status_code == 200:
                                    metrics_data = metrics_response.json()
                                    if metrics_data.get("data"):
                                        attrs = metrics_data["data"].get("attributes", {})
                                        variables["klaviyo_latest_campaign_open_rate"] = attrs.get("open_rate", 0)
                                        variables["klaviyo_latest_campaign_click_rate"] = attrs.get("click_rate", 0)
            except Exception as e:
                logger.warning(f"Failed to fetch campaigns: {e}")
                
            # Fetch flows
            try:
                flows_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "flows.list",
                        "arguments": {"page_size": 50},
                        "use_enhanced": True
                    }
                )
                if flows_response.status_code == 200:
                    flows_data = flows_response.json()
                    if flows_data.get("success") and flows_data.get("data"):
                        inner_data = flows_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            flow_list = inner_data["data"].get("data", [])
                        else:
                            flow_list = []
                        variables["klaviyo_flows_count"] = len(flow_list)
                        variables["klaviyo_flows_live_count"] = sum(1 for f in flow_list if f.get("attributes", {}).get("status") == "live")
                        variables["klaviyo_flows_draft_count"] = sum(1 for f in flow_list if f.get("attributes", {}).get("status") == "draft")
                        variables["klaviyo_flow_names"] = [f.get("attributes", {}).get("name", "") for f in flow_list[:5]]
            except Exception as e:
                logger.warning(f"Failed to fetch flows: {e}")
                
            # Fetch metrics list
            try:
                metrics_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "metrics.list",
                        "arguments": {"page_size": 100},
                        "use_enhanced": True
                    }
                )
                if metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    if metrics_data.get("success") and metrics_data.get("data"):
                        inner_data = metrics_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            metric_list = inner_data["data"].get("data", [])
                        else:
                            metric_list = []
                        variables["klaviyo_available_metrics"] = [m.get("attributes", {}).get("name", "") for m in metric_list[:10]]
                        variables["klaviyo_metric_count"] = len(metric_list)
            except Exception as e:
                logger.warning(f"Failed to fetch metrics: {e}")
                
            # Fetch lists
            try:
                lists_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "lists.list",
                        "arguments": {"page_size": 50},
                        "use_enhanced": True
                    }
                )
                if lists_response.status_code == 200:
                    lists_data = lists_response.json()
                    if lists_data.get("success") and lists_data.get("data"):
                        inner_data = lists_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            list_list = inner_data["data"].get("data", [])
                        else:
                            list_list = []
                        variables["klaviyo_lists_count"] = len(list_list)
                        variables["klaviyo_list_names"] = [l.get("attributes", {}).get("name", "") for l in list_list[:5]]
                        # Get largest list size
                        list_sizes = [l.get("attributes", {}).get("profile_count", 0) for l in list_list]
                        if list_sizes:
                            variables["klaviyo_largest_list_size"] = max(list_sizes)
            except Exception as e:
                logger.warning(f"Failed to fetch lists: {e}")
                
            # Fetch segments
            try:
                segments_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "segments.list",
                        "arguments": {"page_size": 50},
                        "use_enhanced": True
                    }
                )
                if segments_response.status_code == 200:
                    segments_data = segments_response.json()
                    if segments_data.get("success") and segments_data.get("data"):
                        inner_data = segments_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            segment_list = inner_data["data"].get("data", [])
                        else:
                            segment_list = []
                        variables["klaviyo_segments_count"] = len(segment_list)
                        variables["klaviyo_segment_names"] = [s.get("attributes", {}).get("name", "") for s in segment_list[:5]]
            except Exception as e:
                logger.warning(f"Failed to fetch segments: {e}")
                
            # Fetch templates
            try:
                templates_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "templates.list",
                        "arguments": {"page_size": 50},
                        "use_enhanced": True
                    }
                )
                if templates_response.status_code == 200:
                    templates_data = templates_response.json()
                    if templates_data.get("success") and templates_data.get("data"):
                        inner_data = templates_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            template_list = inner_data["data"].get("data", [])
                        else:
                            template_list = []
                        variables["klaviyo_templates_count"] = len(template_list)
                        variables["klaviyo_template_names"] = [t.get("attributes", {}).get("name", "") for t in template_list[:5]]
            except Exception as e:
                logger.warning(f"Failed to fetch templates: {e}")
                
            # Fetch forms
            try:
                forms_response = await client.post(
                    f"{MCP_GATEWAY_URL}/invoke",
                    json={
                        "client_id": client_id,
                        "tool_name": "forms.list",
                        "arguments": {"page_size": 50},
                        "use_enhanced": True
                    }
                )
                if forms_response.status_code == 200:
                    forms_data = forms_response.json()
                    if forms_data.get("success") and forms_data.get("data"):
                        inner_data = forms_data["data"]
                        if isinstance(inner_data, dict) and "data" in inner_data:
                            form_list = inner_data["data"].get("data", [])
                        else:
                            form_list = []
                        variables["klaviyo_forms_count"] = len(form_list)
                        variables["klaviyo_form_names"] = [f.get("attributes", {}).get("name", "") for f in form_list[:5]]
            except Exception as e:
                logger.warning(f"Failed to fetch forms: {e}")
                
    except Exception as e:
        logger.error(f"Error fetching live Klaviyo data: {e}")
        # Return empty dict on total failure
        return {}
    
    # Cache the results
    if variables:
        mcp_cache[cache_key] = variables
        cache_timestamps[cache_key] = now
        logger.info(f"Cached {len(variables)} live Klaviyo variables for client {client_id}")
    
    return variables


def get_campaign_variables() -> Dict[str, Any]:
    """
    Generate campaign-related variables
    """
    return {
        # Campaign types
        "campaign_type_promotional": "Promotional",
        "campaign_type_educational": "Educational",
        "campaign_type_transactional": "Transactional",
        "campaign_type_newsletter": "Newsletter",
        "campaign_type_announcement": "Announcement",
        "campaign_type_survey": "Survey",
        
        # Campaign goals
        "goal_revenue": "Drive Revenue",
        "goal_engagement": "Increase Engagement",
        "goal_retention": "Improve Retention",
        "goal_acquisition": "Customer Acquisition",
        "goal_reactivation": "Win Back Customers",
        
        # Sending times
        "best_send_time_morning": "09:00",
        "best_send_time_afternoon": "14:00",
        "best_send_time_evening": "19:00",
        "best_send_day_b2c": "Thursday",
        "best_send_day_b2b": "Tuesday",
        
        # Subject line variables
        "first_name": "{{first_name}}",
        "last_name": "{{last_name}}",
        "company_name": "{{company_name}}",
        "product_name": "{{product_name}}",
        "discount_amount": "{{discount_amount}}",
        "urgency_days": "{{urgency_days}}"
    }


@router.get("/all")
async def get_all_variables(
    client_id: Optional[str] = Query(None, description="Client ID for specific client variables"),
    selected_month: Optional[str] = Query(None, description="Selected month in YYYY-MM format"),
    include_live_data: bool = Query(True, description="Include live Klaviyo data (may be slower)")
) -> Dict[str, Any]:
    """
    Get all available variables for agent development
    Now includes LIVE Klaviyo data when client_id is provided
    """
    try:
        # Gather all variable categories
        time_vars = get_time_frame_variables(selected_month)
        client_vars = await get_client_variables(client_id)
        perf_vars = get_performance_variables()
        campaign_vars = get_campaign_variables()
        
        # Fetch LIVE Klaviyo data if client_id provided
        klaviyo_live_vars = {}
        if client_id and include_live_data:
            try:
                klaviyo_live_vars = await get_klaviyo_live_variables(client_id)
                logger.info(f"Retrieved {len(klaviyo_live_vars)} live Klaviyo variables for client {client_id}")
            except Exception as e:
                logger.warning(f"Could not fetch live Klaviyo data: {e}")
                # Continue without live data
        
        # Combine all variables
        all_variables = {
            "time_frames": time_vars,
            "client": client_vars,
            "performance": perf_vars,
            "campaign": campaign_vars,
            "klaviyo_live": klaviyo_live_vars,  # New: LIVE data from MCP
            "system": {
                "environment": "{{environment}}",
                "api_version": "{{api_version}}",
                "user_id": "{{user_id}}",
                "user_email": "{{user_email}}",
                "user_role": "{{user_role}}",
                "session_id": "{{session_id}}",
                "request_id": "{{request_id}}"
            }
        }
        
        # Add summary
        total_vars = sum(len(v) if isinstance(v, dict) else 0 for v in all_variables.values())
        live_vars_count = len(klaviyo_live_vars)
        
        return {
            "variables": all_variables,
            "metadata": {
                "total_variables": total_vars,
                "live_variables": live_vars_count,
                "categories": list(all_variables.keys()),
                "generated_at": datetime.now().isoformat(),
                "selected_month": selected_month or datetime.now().strftime("%Y-%m"),
                "client_id": client_id,
                "has_live_data": live_vars_count > 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting variables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_variable_categories() -> List[str]:
    """
    Get list of available variable categories
    """
    return [
        "time_frames",
        "client",
        "performance",
        "campaign",
        "klaviyo_live",  # New: LIVE data from MCP
        "system"
    ]


@router.get("/{category}")
async def get_variables_by_category(
    category: str,
    client_id: Optional[str] = Query(None),
    selected_month: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Get variables for a specific category
    """
    if category == "time_frames":
        return get_time_frame_variables(selected_month)
    elif category == "client":
        return await get_client_variables(client_id)
    elif category == "performance":
        return get_performance_variables()
    elif category == "campaign":
        return get_campaign_variables()
    elif category == "klaviyo_live":
        # New: Return LIVE Klaviyo data
        if not client_id:
            raise HTTPException(status_code=400, detail="client_id is required for live Klaviyo data")
        return await get_klaviyo_live_variables(client_id)
    elif category == "system":
        return {
            "environment": "{{environment}}",
            "api_version": "{{api_version}}",
            "user_id": "{{user_id}}",
            "user_email": "{{user_email}}",
            "user_role": "{{user_role}}",
            "session_id": "{{session_id}}",
            "request_id": "{{request_id}}"
        }
    else:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found")


@router.get("/search/{term}")
async def search_variables(term: str) -> List[Dict[str, Any]]:
    """
    Search for variables by name or description
    """
    all_vars = await get_all_variables()
    results = []
    
    term_lower = term.lower()
    for category, variables in all_vars["variables"].items():
        if isinstance(variables, dict):
            for var_name, var_value in variables.items():
                if term_lower in var_name.lower():
                    results.append({
                        "name": var_name,
                        "value": var_value,
                        "category": category,
                        "syntax": f"{{{{{var_name}}}}}"
                    })
    
    return results