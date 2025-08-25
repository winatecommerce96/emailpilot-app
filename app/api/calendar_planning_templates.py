"""
Calendar Planning Prompt Templates API

Manages and stores calendar planning prompt templates in the AI Models system.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from datetime import datetime
from google.cloud import firestore
from app.deps import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/templates", tags=["Calendar Templates"])

# Calendar Planning Master Template
CALENDAR_PLANNING_TEMPLATE = """Connection Check
Connect to "{mcp_connector_name}" via the MCP connector.
If connection fails, immediately return: ERROR – Unable to access {client_name} Klaviyo via MCP.
Run Data Integrity Check:
Validate that Shopify Placed Order Revenue (metric ID: {placed_order_metric_id}) for {comparison_month} {comparison_year_1} and {comparison_month} {comparison_year_2} > 0.
If revenue is zero for either year, STOP and return:
ERROR – Revenue metric "Shopify Placed Order" ({placed_order_metric_id}) returned zero for [Year]. Cannot proceed. Validate MCP/Klaviyo data.
⸻
2 · Data to Pull
Pull all {comparison_month} {comparison_year_1} & {comparison_month} {comparison_year_2} email and SMS campaigns, returning for each send:
Metric    Required
Sends    ✔
Successful deliveries    ✔
Open %    ✔
Click %    ✔
Placed-order %    ✔
Revenue    ✔
Revenue-per-recipient    ✔
Average-order-value    ✔
Unsubscribe / spam %    ✔
Send date & exact send time    ✔
Send-time-optimization score (if available)    ✓
Also pull:
    •    Segment performance for {affinity_segments}.
    •    Top 5 UTM source cohorts by revenue.
    •    Mobile vs. desktop split and time-zone distribution (flag if >15 % outside {primary_timezone}).
    •    Inventory & launch data for SKUs with ≥ 10 units forecasted for {target_month}, plus any limited-time products.
⸻
3 · Planning Rules
Topic    Rule
Calendar scope    Create {email_campaign_count} email and {sms_campaign_count} SMS campaign ideas for {target_month} {target_year}.
Send-caps    Standard: max {max_emails_per_week} total emails per account per week. Exception: subscribers tagged unengaged or churn-risk may receive 2 + promotional sends over the course of a month to drive re-engagement.
List health    Include at least one send to the entire mailable list; monitor % unengaged and flag deliverability risks.
Promos vs nurture    {promo_strategy}
Sales target    Hit ${revenue_goal:,.0f} Klaviyo-attributed revenue (campaigns/SMS = ${campaign_revenue_goal:,.0f}). Revenue mix: {revenue_distribution}.
Affinity groups    Every send must clearly map to one (or more) of: {affinity_segments}.
Subscription push    Include dedicated {subscription_product} growth flows/campaigns if applicable.
⸻
4 · Key {target_month} Hooks
{key_dates}
⸻
5 · Required Output (Canvas-Ready Table)
Create a canvas table with one row per campaign ({total_campaigns} rows) using these columns in order:
    1.    Week #
    2.    Send Date (YYYY-MM-DD)
    3.    Send Time (HH:MM local)
    4.    Segment(s)
    5.    Subject Line A / B
    6.    Preview Text
    7.    Hero H1
    8.    Sub-head
    9.    Hero Image – file name + 1-sentence tone/shot note
    10.    CTA Copy
    11.    Offer (if any)
    12.    A/B Test Idea (copy, creative, or timing)
    13.    Secondary Message Suggestion / SMS variant
If Canvas is unavailable, output the same table in Markdown.
⸻
6 · Promo Brief (1-pager per marquee promo)
After the table, generate a compact Markdown brief for any multi-day promotions that includes: goal, audience, offer mechanics, asset checklist, send cadence, KPI targets, and test plan.
⸻
7 · Success Criteria
    •    Meet or exceed the revenue goal distribution.
    •    Stay within send-caps and promo limits.
    •    Provide data-backed justification for every send-time and segment choice.
    •    Flag any deliverability or inventory risks."""

@router.post("/initialize-calendar-template")
async def initialize_calendar_planning_template(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Initialize the calendar planning template in the AI prompts system
    """
    try:
        # Check if template already exists
        existing = db.collection("ai_prompts").where("name", "==", "Calendar Planning Master Template").limit(1).stream()
        
        for doc in existing:
            return {
                "success": True,
                "message": "Calendar planning template already exists",
                "prompt_id": doc.id,
                "existing": True
            }
        
        # Create the template
        template_data = {
            "name": "Calendar Planning Master Template",
            "description": "Comprehensive calendar planning prompt for generating data-driven email and SMS campaigns using MCP Klaviyo integration",
            "prompt_template": CALENDAR_PLANNING_TEMPLATE,
            "model_provider": "claude",
            "model_name": "claude-3-opus-20240229",
            "category": "calendar",
            "variables": [
                "mcp_connector_name",
                "client_name",
                "placed_order_metric_id",
                "comparison_month",
                "comparison_year_1",
                "comparison_year_2",
                "affinity_segments",
                "primary_timezone",
                "target_month",
                "target_year",
                "email_campaign_count",
                "sms_campaign_count",
                "max_emails_per_week",
                "promo_strategy",
                "revenue_goal",
                "campaign_revenue_goal",
                "revenue_distribution",
                "subscription_product",
                "key_dates",
                "total_campaigns"
            ],
            "active": True,
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "usage_count": 0,
            "metadata": {
                "source": "calendar_planning_ai",
                "requires_mcp": True,
                "output_format": "markdown_table",
                "campaign_types": ["email", "sms"],
                "integration": "klaviyo"
            }
        }
        
        # Add to Firestore
        doc_ref = db.collection("ai_prompts").add(template_data)[1]
        
        logger.info(f"Calendar planning template created: {doc_ref.id}")
        
        return {
            "success": True,
            "message": "Calendar planning template created successfully",
            "prompt_id": doc_ref.id,
            "template_name": template_data["name"],
            "variables_count": len(template_data["variables"])
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize calendar template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar-template")
async def get_calendar_template(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the calendar planning master template
    """
    try:
        # Find the calendar planning template
        templates = db.collection("ai_prompts").where("name", "==", "Calendar Planning Master Template").where("active", "==", True).limit(1).stream()
        
        for doc in templates:
            template_data = doc.to_dict()
            template_data["id"] = doc.id
            
            return {
                "success": True,
                "template": template_data
            }
        
        # Template not found
        return {
            "success": False,
            "message": "Calendar planning template not found. Use /initialize-calendar-template to create it.",
            "template": None
        }
        
    except Exception as e:
        logger.error(f"Failed to get calendar template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/render-calendar-prompt")
async def render_calendar_prompt(
    client_id: str,
    target_month: str,
    target_year: int,
    custom_variables: Dict[str, Any] = None,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Render the calendar planning template with actual client data
    """
    try:
        # Get the template
        templates = db.collection("ai_prompts").where("name", "==", "Calendar Planning Master Template").where("active", "==", True).limit(1).stream()
        
        template = None
        for doc in templates:
            template = doc.to_dict()
            break
        
        if not template:
            raise HTTPException(status_code=404, detail="Calendar planning template not found")
        
        # Get client data
        client_doc = db.collection("clients").document(client_id).get()
        if not client_doc.exists:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
        
        client_data = client_doc.to_dict()
        
        # Get MCP configuration
        mcp_doc = db.collection("mcp_clients").document(client_id).get()
        mcp_data = mcp_doc.to_dict() if mcp_doc.exists else {}
        
        # Get segments
        segments_doc = db.collection("clients").document(client_id).collection("segments").document("affinity").get()
        affinity_segments = []
        if segments_doc.exists:
            segments_data = segments_doc.to_dict()
            affinity_segments = segments_data.get("segments", ["General Audience"])
        
        # Get revenue goal
        goals_doc = db.collection("clients").document(client_id).collection("goals").document(f"{target_year}_{target_month.lower()}").get()
        revenue_goal = 50000  # Default
        if goals_doc.exists:
            goals_data = goals_doc.to_dict()
            revenue_goal = goals_data.get("revenue_target", 50000)
        
        # Get key dates
        events_query = db.collection("clients").document(client_id).collection("calendar_events").where("month", "==", target_month).where("year", "==", target_year).stream()
        key_dates_list = []
        for event_doc in events_query:
            event_data = event_doc.to_dict()
            key_dates_list.append(f"    •    {event_data.get('date', 'TBD')} – {event_data.get('title', 'Event')} {event_data.get('description', '')}")
        
        # Prepare variables
        comparison_year_1 = target_year - 2
        comparison_year_2 = target_year - 1
        campaign_revenue = revenue_goal * 0.83  # 83% from campaigns
        
        variables = {
            "mcp_connector_name": mcp_data.get("connector_name", f"{client_data.get('name', client_id)} Klaviyo"),
            "client_name": client_data.get("name", client_id),
            "placed_order_metric_id": "TPWsCU",  # Default Klaviyo metric ID
            "comparison_month": target_month,
            "comparison_year_1": comparison_year_1,
            "comparison_year_2": comparison_year_2,
            "affinity_segments": " · ".join(affinity_segments),
            "primary_timezone": client_data.get("timezone", "America/Los_Angeles"),
            "target_month": target_month,
            "target_year": target_year,
            "email_campaign_count": 20,
            "sms_campaign_count": 4,
            "max_emails_per_week": 2,
            "promo_strategy": "Balance promotional and nurture content based on historical performance",
            "revenue_goal": revenue_goal,
            "campaign_revenue_goal": campaign_revenue,
            "revenue_distribution": "70% primary products · 20% secondary · 10% new offerings",
            "subscription_product": client_data.get("subscription_product", "subscription"),
            "key_dates": "\n".join(key_dates_list) if key_dates_list else "    •    No specific key dates configured",
            "total_campaigns": 24
        }
        
        # Override with custom variables if provided
        if custom_variables:
            variables.update(custom_variables)
        
        # Render the template
        rendered_prompt = template["prompt_template"]
        for var_name, var_value in variables.items():
            rendered_prompt = rendered_prompt.replace(f"{{{var_name}}}", str(var_value))
        
        return {
            "success": True,
            "client_id": client_id,
            "period": f"{target_month} {target_year}",
            "rendered_prompt": rendered_prompt,
            "variables_used": variables,
            "template_version": template.get("version", 1)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to render calendar prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar-templates/list")
async def list_calendar_templates(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all calendar-related prompt templates
    """
    try:
        templates = db.collection("ai_prompts").where("category", "==", "calendar").where("active", "==", True).stream()
        
        template_list = []
        for doc in templates:
            template_data = doc.to_dict()
            template_list.append({
                "id": doc.id,
                "name": template_data.get("name"),
                "description": template_data.get("description"),
                "model_provider": template_data.get("model_provider"),
                "variables_count": len(template_data.get("variables", [])),
                "version": template_data.get("version", 1),
                "usage_count": template_data.get("usage_count", 0),
                "last_used": template_data.get("last_used"),
                "created_at": template_data.get("created_at")
            })
        
        return {
            "success": True,
            "count": len(template_list),
            "templates": template_list
        }
        
    except Exception as e:
        logger.error(f"Failed to list calendar templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendar-template/quick-prompts")
async def create_quick_calendar_prompts(
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create additional quick calendar planning prompts
    """
    quick_prompts = [
        {
            "name": "Quick Campaign Analysis",
            "description": "Analyze previous month's campaign performance for insights",
            "prompt_template": "Analyze {client_name}'s {analysis_month} {analysis_year} email campaigns:\n1. Top 5 by revenue\n2. Best engagement rates\n3. Optimal send times\n4. Segment performance\n5. Key insights for {target_month} {target_year}",
            "variables": ["client_name", "analysis_month", "analysis_year", "target_month", "target_year"]
        },
        {
            "name": "Segment Performance Review",
            "description": "Review affinity segment engagement and revenue",
            "prompt_template": "Review segment performance for {client_name}:\nSegments: {affinity_segments}\nPeriod: {analysis_period}\nMetrics: Opens, Clicks, Revenue\nProvide optimization recommendations.",
            "variables": ["client_name", "affinity_segments", "analysis_period"]
        },
        {
            "name": "Revenue Forecast",
            "description": "Generate revenue forecast based on planned campaigns",
            "prompt_template": "Forecast revenue for {client_name} {target_month} {target_year}:\nPlanned campaigns: {campaign_count}\nHistorical average: ${historical_avg}\nGrowth target: {growth_percentage}%\nProvide weekly breakdown.",
            "variables": ["client_name", "target_month", "target_year", "campaign_count", "historical_avg", "growth_percentage"]
        }
    ]
    
    created_count = 0
    
    try:
        for prompt_config in quick_prompts:
            # Check if already exists
            existing = db.collection("ai_prompts").where("name", "==", prompt_config["name"]).limit(1).stream()
            
            exists = False
            for doc in existing:
                exists = True
                break
            
            if not exists:
                template_data = {
                    "name": prompt_config["name"],
                    "description": prompt_config["description"],
                    "prompt_template": prompt_config["prompt_template"],
                    "model_provider": "claude",
                    "model_name": "claude-3-sonnet-20240229",  # Use faster model for quick prompts
                    "category": "calendar",
                    "variables": prompt_config["variables"],
                    "active": True,
                    "version": 1,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "usage_count": 0,
                    "metadata": {
                        "type": "quick_prompt",
                        "source": "calendar_planning_ai"
                    }
                }
                
                db.collection("ai_prompts").add(template_data)
                created_count += 1
        
        return {
            "success": True,
            "message": f"Created {created_count} quick calendar prompts",
            "total_prompts": len(quick_prompts)
        }
        
    except Exception as e:
        logger.error(f"Failed to create quick prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))