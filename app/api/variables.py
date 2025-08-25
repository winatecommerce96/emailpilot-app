"""
Variables API for Agent Development
Provides comprehensive variables from Firestore clients and time frames
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from app.deps.firestore import get_db as get_firestore_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/variables", tags=["variables"])


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
    selected_month: Optional[str] = Query(None, description="Selected month in YYYY-MM format")
) -> Dict[str, Any]:
    """
    Get all available variables for agent development
    """
    try:
        # Gather all variable categories
        time_vars = get_time_frame_variables(selected_month)
        client_vars = await get_client_variables(client_id)
        perf_vars = get_performance_variables()
        campaign_vars = get_campaign_variables()
        
        # Combine all variables
        all_variables = {
            "time_frames": time_vars,
            "client": client_vars,
            "performance": perf_vars,
            "campaign": campaign_vars,
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
        
        return {
            "variables": all_variables,
            "metadata": {
                "total_variables": total_vars,
                "categories": list(all_variables.keys()),
                "generated_at": datetime.now().isoformat(),
                "selected_month": selected_month or datetime.now().strftime("%Y-%m")
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