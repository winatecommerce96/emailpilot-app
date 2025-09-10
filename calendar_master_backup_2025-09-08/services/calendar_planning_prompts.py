"""
Calendar Planning Prompt Templates for EmailPilot AI Agent Service

This module contains the prompt templates for generating calendar plans
using MCP Klaviyo data and AI agents.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class CalendarPlanningPrompts:
    """Manages prompt templates for calendar planning with MCP integration"""
    
    @staticmethod
    def generate_monthly_planning_prompt(
        client_name: str,
        client_id: str,
        target_month: str,  # Format: "September 2025"
        target_year: int,
        affinity_segments: List[str],
        revenue_goal: float,
        klaviyo_account_id: str,
        mcp_connector_name: str,
        placed_order_metric_id: str = "TPWsCU",
        utm_sources: Optional[List[str]] = None,
        special_products: Optional[List[Dict[str, Any]]] = None,
        key_dates: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate a comprehensive monthly planning prompt for calendar campaigns
        
        Args:
            client_name: Display name of the client
            client_id: Internal client ID
            target_month: Target month name (e.g., "September")
            target_year: Target year (e.g., 2025)
            affinity_segments: List of customer affinity segments
            revenue_goal: Monthly revenue target
            klaviyo_account_id: Klaviyo account identifier
            mcp_connector_name: MCP connector name for this client
            placed_order_metric_id: Metric ID for placed orders
            utm_sources: Optional list of UTM sources to analyze
            special_products: Optional list of special products/SKUs
            key_dates: Optional list of key dates and events
            
        Returns:
            Formatted prompt string for AI agent
        """
        
        # Calculate previous year for comparison
        previous_year = target_year - 1
        comparison_year = target_year - 2
        
        # Format affinity segments
        segments_list = " · ".join(affinity_segments) if affinity_segments else "General Audience"
        segments_bullet = "\n".join([f"    •    {seg}" for seg in affinity_segments])
        
        # Format key dates if provided
        key_dates_section = ""
        if key_dates:
            dates_list = "\n".join([
                f"    •    {date.get('date', 'TBD')} – {date.get('event', 'Event')} {date.get('notes', '')}"
                for date in key_dates
            ])
            key_dates_section = f"""
⸻
4 · Key {target_month} Hooks
{dates_list}
"""
        
        # Format special products if provided
        inventory_section = ""
        if special_products:
            products_list = ", ".join([p.get('name', 'Product') for p in special_products])
            inventory_section = f"    •    Inventory & launch data for: {products_list}"
        
        # Calculate revenue distribution (default if not specified)
        campaign_revenue = revenue_goal * 0.83  # 83% from campaigns
        flow_revenue = revenue_goal * 0.17  # 17% from flows
        
        prompt = f"""Connection Check
Connect to "{mcp_connector_name}" via the MCP connector.
If connection fails, immediately return: ERROR – Unable to access {client_name} Klaviyo via MCP.
Run Data Integrity Check:
Validate that Shopify Placed Order Revenue (metric ID: {placed_order_metric_id}) for {target_month} {comparison_year} and {target_month} {previous_year} > 0.
If revenue is zero for either year, STOP and return:
ERROR – Revenue metric "Shopify Placed Order" ({placed_order_metric_id}) returned zero for [Year]. Cannot proceed. Validate MCP/Klaviyo data.
⸻
2 · Data to Pull
Pull all {target_month} {comparison_year} & {target_month} {previous_year} email and SMS campaigns, returning for each send:
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
{segments_bullet}
    •    Top 5 UTM source cohorts by revenue.
    •    Mobile vs. desktop split and time-zone distribution (flag if >15 % outside client's primary timezone).
{inventory_section}
⸻
3 · Planning Rules
Topic    Rule
Calendar scope    Create 20 email and 4 SMS campaign ideas for {target_month} {target_year}.
Send-caps    Standard: max 2 total emails per account per week. Exception: subscribers tagged unengaged or churn-risk may receive 2 + promotional sends over the course of a month to drive re-engagement.
List health    Include at least one send to the entire mailable list; monitor % unengaged and flag deliverability risks.
Promos vs nurture    Balance promotional and nurture content based on historical performance.
Sales target    Hit ${revenue_goal:,.0f} Klaviyo-attributed revenue (campaigns/SMS = ${campaign_revenue:,.0f}).
Affinity groups    Every send must clearly map to one (or more) of: {segments_list}.
Subscription push    Include dedicated growth flows/campaigns for subscription products if applicable.
{key_dates_section}⸻
5 · Required Output (Canvas-Ready Table)
Create a canvas table with one row per campaign (24 rows) using these columns in order:
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
        
        return prompt
    
    @staticmethod
    def generate_quick_analysis_prompt(
        client_name: str,
        mcp_connector_name: str,
        target_month: str,
        target_year: int
    ) -> str:
        """
        Generate a quick analysis prompt for basic calendar insights
        
        Args:
            client_name: Display name of the client
            mcp_connector_name: MCP connector name
            target_month: Target month name
            target_year: Target year
            
        Returns:
            Formatted prompt for quick analysis
        """
        previous_year = target_year - 1
        
        return f"""Connect to "{mcp_connector_name}" via MCP and analyze {target_month} {previous_year} performance:

1. Pull top 5 campaigns by revenue
2. Identify best performing segments
3. Calculate average send frequency
4. Determine optimal send times based on engagement
5. Provide 3 key insights for {target_month} {target_year} planning

Format as brief bullet points."""
    
    @staticmethod
    def prepare_prompt_context(
        db,
        client_id: str,
        target_month: str,
        target_year: int
    ) -> Dict[str, Any]:
        """
        Prepare context data from Firestore for prompt generation
        
        Args:
            db: Firestore database connection
            client_id: Client identifier
            target_month: Target month name
            target_year: Target year
            
        Returns:
            Dictionary with all context needed for prompt generation
        """
        try:
            # Get client document
            client_doc = db.collection("clients").document(client_id).get()
            if not client_doc.exists:
                raise ValueError(f"Client {client_id} not found")
            
            client_data = client_doc.to_dict()
            
            # Get MCP configuration
            mcp_doc = db.collection("mcp_clients").document(client_id).get()
            mcp_data = mcp_doc.to_dict() if mcp_doc.exists else {}
            
            # Get calendar configuration
            calendar_config_doc = db.collection("clients").document(client_id).collection("calendar_config").document("settings").get()
            calendar_config = calendar_config_doc.to_dict() if calendar_config_doc.exists else {}
            
            # Get affinity segments
            segments_doc = db.collection("clients").document(client_id).collection("segments").document("affinity").get()
            affinity_segments = []
            if segments_doc.exists:
                segments_data = segments_doc.to_dict()
                affinity_segments = segments_data.get("segments", [])
            
            # Get revenue goals
            goals_doc = db.collection("clients").document(client_id).collection("goals").document(f"{target_year}_{target_month.lower()}").get()
            revenue_goal = 50000  # Default
            if goals_doc.exists:
                goals_data = goals_doc.to_dict()
                revenue_goal = goals_data.get("revenue_target", 50000)
            
            # Get key dates for the month
            events_query = db.collection("clients").document(client_id).collection("calendar_events").where("month", "==", target_month).where("year", "==", target_year).stream()
            key_dates = []
            for event_doc in events_query:
                event_data = event_doc.to_dict()
                key_dates.append({
                    "date": event_data.get("date"),
                    "event": event_data.get("title"),
                    "notes": event_data.get("description", "")
                })
            
            # Compile context
            context = {
                "client_name": client_data.get("name", client_data.get("client_name", client_id)),
                "client_id": client_id,
                "target_month": target_month,
                "target_year": target_year,
                "affinity_segments": affinity_segments or ["General Audience"],
                "revenue_goal": revenue_goal,
                "klaviyo_account_id": client_data.get("klaviyo_account_id", ""),
                "mcp_connector_name": mcp_data.get("connector_name", f"{client_data.get('name', client_id)} Klaviyo"),
                "placed_order_metric_id": calendar_config.get("placed_order_metric_id", "TPWsCU"),
                "utm_sources": calendar_config.get("utm_sources", []),
                "special_products": calendar_config.get("special_products", []),
                "key_dates": key_dates,
                "primary_timezone": client_data.get("timezone", "America/Los_Angeles"),
                "send_frequency": calendar_config.get("send_frequency", {
                    "max_emails_per_week": 2,
                    "max_sms_per_week": 1
                })
            }
            
            logger.info(f"Prepared prompt context for client {client_id}, {target_month} {target_year}")
            return context
            
        except Exception as e:
            logger.error(f"Error preparing prompt context: {e}")
            raise
    
    @staticmethod
    def format_campaign_table_markdown(campaigns: List[Dict[str, Any]]) -> str:
        """
        Format campaign data as a markdown table
        
        Args:
            campaigns: List of campaign dictionaries
            
        Returns:
            Markdown formatted table
        """
        if not campaigns:
            return "No campaigns to display"
        
        header = """| Week | Date | Time | Segment | Subject A/B | Preview | Hero H1 | Subhead | Image | CTA | Offer | A/B Test | SMS |
|------|------|------|---------|-------------|---------|---------|---------|-------|-----|-------|----------|-----|"""
        
        rows = []
        for campaign in campaigns:
            row = f"""| {campaign.get('week', '')} | {campaign.get('date', '')} | {campaign.get('time', '')} | {campaign.get('segment', '')} | {campaign.get('subject', '')} | {campaign.get('preview', '')} | {campaign.get('hero_h1', '')} | {campaign.get('subhead', '')} | {campaign.get('image', '')} | {campaign.get('cta', '')} | {campaign.get('offer', 'None')} | {campaign.get('ab_test', '')} | {campaign.get('sms', '')} |"""
            rows.append(row)
        
        return f"{header}\n" + "\n".join(rows)
    
    @staticmethod
    def validate_prompt_response(response: str) -> Dict[str, Any]:
        """
        Validate and parse AI response to calendar planning prompt
        
        Args:
            response: Raw AI response text
            
        Returns:
            Parsed and validated response data
        """
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "data": None
        }
        
        try:
            # Check for error responses
            if "ERROR" in response and "Cannot proceed" in response:
                validation_result["errors"].append("MCP connection or data validation failed")
                return validation_result
            
            # Check for required sections
            required_sections = ["Required Output", "Success Criteria"]
            for section in required_sections:
                if section not in response:
                    validation_result["warnings"].append(f"Missing section: {section}")
            
            # Try to extract campaign table
            if "| Week |" in response or "| Week #|" in response:
                validation_result["data"] = {
                    "has_table": True,
                    "raw_response": response
                }
                validation_result["valid"] = True
            else:
                validation_result["warnings"].append("No campaign table found in response")
            
            # Check for promo briefs if mentioned
            if "Promo Brief" in response:
                validation_result["data"]["has_promo_brief"] = True
            
            return validation_result
            
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            return validation_result