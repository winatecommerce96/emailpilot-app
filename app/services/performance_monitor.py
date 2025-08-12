"""
Integrated Performance Monitoring Service
Combines weekly and monthly report generation from Cloud Functions
Uses Firestore for data storage and MCP service for Klaviyo API calls
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from google.cloud import firestore
from google.cloud.secretmanager import SecretManagerServiceClient
import google.generativeai as genai
import logging
import asyncio
import httpx
from calendar import monthrange

# Initialize clients
db = firestore.Client(project='emailpilot-438321')
secret_client = SecretManagerServiceClient()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Service URL
MCP_SERVICE_URL = "https://klaviyo-mcp-service-935786836546.us-central1.run.app"

@dataclass
class WeeklyMetrics:
    """Container for weekly performance metrics"""
    account_name: str
    week_ending: str
    weekly_revenue: float
    weekly_orders: int
    campaigns_sent: int
    active_flows: int
    email_sent: int
    email_opened: int
    email_clicked: int
    open_rate: float
    click_rate: float
    conversion_rate: float
    avg_order_value: float
    revenue_per_recipient: float
    month_to_date_revenue: float
    monthly_goal: Optional[float]
    goal_progress_percent: Optional[float]
    days_remaining_in_month: int
    required_daily_revenue: Optional[float]
    on_track_status: str
    top_campaigns: List[Dict[str, Any]]
    top_flows: List[Dict[str, Any]]
    performance_summary: str
    recommendations: List[str]
    campaign_breakdown: Dict[str, Any]
    flow_breakdown: Dict[str, Any]
    click_through_rate: float
    placed_order_rate: float
    week_over_week_change: Optional[float]
    ai_insights: List[str]
    ai_action_plan: List[str]

@dataclass
class MonthlyMetrics:
    """Container for monthly performance metrics"""
    account_name: str
    month: str
    year: int
    total_revenue: float
    total_orders: int
    total_campaigns: int
    total_flows: int
    total_emails_sent: int
    total_emails_opened: int
    total_emails_clicked: int
    avg_open_rate: float
    avg_click_rate: float
    avg_conversion_rate: float
    avg_order_value: float
    revenue_per_recipient: float
    monthly_goal: Optional[float]
    goal_achievement_percent: Optional[float]
    month_over_month_change: Optional[float]
    year_over_year_change: Optional[float]
    best_performing_week: Dict[str, Any]
    worst_performing_week: Dict[str, Any]
    top_campaigns: List[Dict[str, Any]]
    top_flows: List[Dict[str, Any]]
    customer_metrics: Dict[str, Any]
    segment_performance: List[Dict[str, Any]]
    performance_summary: str
    strategic_recommendations: List[str]
    ai_insights: List[str]
    next_month_projections: Dict[str, Any]

class PerformanceMonitorService:
    """Unified service for performance monitoring and reporting"""
    
    def __init__(self):
        self.db = db
        self.secret_client = secret_client
        self._setup_gemini()
        
    def _setup_gemini(self):
        """Initialize Gemini AI for insights generation"""
        api_key = self.get_secret('gemini-api-key')
        if api_key:
            genai.configure(api_key=api_key)
            # Use gemini-1.5-flash for better performance and availability
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            logger.warning("Gemini API key not found, AI insights will be limited")
            self.gemini_model = None
    
    def get_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from Google Secret Manager"""
        project_id = os.environ.get('GCP_PROJECT', 'emailpilot-438321')
        secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        try:
            response = self.secret_client.access_secret_version(request={"name": secret_name})
            return response.payload.data.decode('UTF-8')
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_id}: {e}")
            return None
    
    async def call_mcp_tool(self, api_key: str, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call the deployed MCP service via HTTP"""
        try:
            payload = {
                "api_key": api_key,
                "tool_name": tool_name,
                "parameters": parameters or {}
            }
            
            logger.info(f"Calling MCP service: {tool_name}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{MCP_SERVICE_URL}/call_tool",
                    json=payload
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"MCP service response success")
                return result
            else:
                logger.error(f"MCP service error {response.status_code}: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"MCP service call failed: {e}")
            return {}
    
    def calculate_on_track_status(self, current_revenue: float, goal: float, 
                                 days_passed: int, total_days: int) -> tuple[str, Optional[float]]:
        """Calculate if account is on track to meet goal"""
        if not goal or goal <= 0:
            return "no_goal", None
        
        expected_progress_percent = (days_passed / total_days) * 100
        actual_progress_percent = (current_revenue / goal) * 100
        
        remaining_days = total_days - days_passed
        remaining_revenue = goal - current_revenue
        
        if remaining_days > 0:
            required_daily = remaining_revenue / remaining_days
        else:
            required_daily = 0
        
        progress_ratio = actual_progress_percent / expected_progress_percent if expected_progress_percent > 0 else 0
        
        if progress_ratio >= 1.1:
            status = "ahead"
        elif progress_ratio >= 0.95:
            status = "on_track"
        elif progress_ratio >= 0.80:
            status = "behind"
        else:
            status = "at_risk"
        
        return status, required_daily if required_daily > 0 else None
    
    async def generate_ai_insights(self, metrics: Dict[str, Any], report_type: str = "weekly") -> tuple[List[str], List[str]]:
        """Generate AI insights and action plans using Gemini"""
        if not self.gemini_model:
            return [], []
        
        try:
            prompt = f"""
            Analyze these {report_type} email marketing metrics and provide insights:
            
            {json.dumps(metrics, indent=2)}
            
            Provide:
            1. Three key insights about the performance
            2. Three specific action items to improve results
            
            Format as JSON:
            {{
                "insights": ["insight1", "insight2", "insight3"],
                "actions": ["action1", "action2", "action3"]
            }}
            """
            
            response = self.gemini_model.generate_content(prompt)
            result = json.loads(response.text)
            
            return result.get("insights", []), result.get("actions", [])
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return [], []
    
    async def generate_weekly_report(self, client_id: str) -> Dict[str, Any]:
        """Generate weekly performance report for a client"""
        try:
            # Get client data from Firestore
            client_doc = self.db.collection('clients').document(client_id).get()
            if not client_doc.exists:
                raise ValueError(f"Client {client_id} not found")
            
            client_data = client_doc.to_dict()
            account_name = client_data.get('name', 'Unknown')
            
            # Try to get API key from Firestore first, then from Secret Manager
            api_key = client_data.get('klaviyo_private_key')
            
            if not api_key:
                # Try to get from Secret Manager using client name
                secret_name = f"klaviyo-api-{account_name.lower().replace(' ', '-')}"
                logger.info(f"Attempting to get API key from Secret Manager: {secret_name}")
                api_key = self.get_secret(secret_name)
            
            if not api_key:
                # Try using client ID as fallback
                secret_name = f"klaviyo-api-{client_id.lower()}"
                logger.info(f"Attempting fallback secret: {secret_name}")
                api_key = self.get_secret(secret_name)
            
            if not api_key:
                raise ValueError(f"No API key found for client {client_id} ({account_name})")
            
            # Calculate date ranges
            today = datetime.now()
            week_start = today - timedelta(days=7)
            month_start = today.replace(day=1)
            
            # Use direct Klaviyo API instead of MCP service
            from app.services.klaviyo_direct import KlaviyoDirectService
            klaviyo = KlaviyoDirectService(api_key)
            
            # Get campaign and flow data
            campaigns_data = klaviyo.get_campaigns(week_start, today)
            flows_data = klaviyo.get_flows()
            revenue_data = klaviyo.get_metrics([], week_start, today)
            
            # Calculate weekly metrics
            weekly_revenue = revenue_data.get('total_revenue', 0)
            weekly_orders = revenue_data.get('total_orders', 0)
            emails_sent = revenue_data.get('emails_sent', 0)
            emails_opened = revenue_data.get('emails_opened', 0)
            emails_clicked = revenue_data.get('emails_clicked', 0)
            
            open_rate = (emails_opened / emails_sent * 100) if emails_sent > 0 else 0
            click_rate = (emails_clicked / emails_opened * 100) if emails_opened > 0 else 0
            conversion_rate = (weekly_orders / emails_sent * 100) if emails_sent > 0 else 0
            avg_order_value = (weekly_revenue / weekly_orders) if weekly_orders > 0 else 0
            
            # Get month-to-date metrics
            mtd_revenue_data = klaviyo.get_metrics([], month_start, today)
            mtd_revenue = mtd_revenue_data.get('total_revenue', 0)
            
            # Get monthly goal from Firestore
            # Goals are stored per month/year, so filter for current month
            # Some goals use client document ID, others use client name as client_id
            goals_ref = self.db.collection('goals')\
                .where('client_id', '==', client_id)\
                .where('month', '==', today.month)\
                .where('year', '==', today.year)\
                .limit(1)
            goals = list(goals_ref.stream())
            
            # If no goal found by document ID, try by client name
            if not goals:
                goals_ref = self.db.collection('goals')\
                    .where('client_id', '==', account_name)\
                    .where('month', '==', today.month)\
                    .where('year', '==', today.year)\
                    .limit(1)
                goals = list(goals_ref.stream())
            
            monthly_goal = None
            for goal in goals:
                goal_data = goal.to_dict()
                # Goals collection uses 'revenue_goal' field, not 'monthly_revenue_goal'
                monthly_goal = goal_data.get('revenue_goal')
                if monthly_goal:
                    logger.info(f"Found goal for {account_name}: ${monthly_goal:,.2f} for {today.month}/{today.year}")
            
            # Calculate goal progress
            days_in_month = monthrange(today.year, today.month)[1]
            days_passed = today.day
            days_remaining = days_in_month - days_passed
            
            on_track_status, required_daily = self.calculate_on_track_status(
                mtd_revenue, monthly_goal, days_passed, days_in_month
            )
            
            goal_progress = (mtd_revenue / monthly_goal * 100) if monthly_goal else None
            
            # Generate AI insights
            metrics_for_ai = {
                "weekly_revenue": weekly_revenue,
                "weekly_orders": weekly_orders,
                "open_rate": open_rate,
                "click_rate": click_rate,
                "conversion_rate": conversion_rate,
                "mtd_revenue": mtd_revenue,
                "monthly_goal": monthly_goal,
                "on_track_status": on_track_status
            }
            
            ai_insights, ai_actions = await self.generate_ai_insights(metrics_for_ai, "weekly")
            
            # Create WeeklyMetrics object
            weekly_metrics = WeeklyMetrics(
                account_name=account_name,
                week_ending=today.strftime('%Y-%m-%d'),
                weekly_revenue=weekly_revenue,
                weekly_orders=weekly_orders,
                campaigns_sent=len(campaigns_data.get('campaigns', [])),
                active_flows=len(flows_data.get('flows', [])),
                email_sent=emails_sent,
                email_opened=emails_opened,
                email_clicked=emails_clicked,
                open_rate=open_rate,
                click_rate=click_rate,
                conversion_rate=conversion_rate,
                avg_order_value=avg_order_value,
                revenue_per_recipient=weekly_revenue / emails_sent if emails_sent > 0 else 0,
                month_to_date_revenue=mtd_revenue,
                monthly_goal=monthly_goal,
                goal_progress_percent=goal_progress,
                days_remaining_in_month=days_remaining,
                required_daily_revenue=required_daily,
                on_track_status=on_track_status,
                top_campaigns=campaigns_data.get('top_campaigns', [])[:3],
                top_flows=flows_data.get('top_flows', [])[:3],
                performance_summary=f"Generated {weekly_revenue:.2f} from {weekly_orders} orders",
                recommendations=self.generate_recommendations(on_track_status),
                campaign_breakdown=campaigns_data.get('breakdown', {}),
                flow_breakdown=flows_data.get('breakdown', {}),
                click_through_rate=click_rate,
                placed_order_rate=conversion_rate,
                week_over_week_change=None,  # TODO: Calculate from historical data
                ai_insights=ai_insights,
                ai_action_plan=ai_actions
            )
            
            # Store report in Firestore
            report_data = asdict(weekly_metrics)
            report_data['created_at'] = datetime.now()
            report_data['client_id'] = client_id
            report_data['report_type'] = 'weekly'
            
            self.db.collection('reports').add(report_data)
            
            # Send Slack notification if webhook configured
            await self.send_slack_notification(weekly_metrics, client_data)
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating weekly report for client {client_id}: {e}")
            raise
    
    async def generate_monthly_report(self, client_id: str) -> Dict[str, Any]:
        """Generate monthly performance report for a client"""
        try:
            # Get client data from Firestore
            client_doc = self.db.collection('clients').document(client_id).get()
            if not client_doc.exists:
                raise ValueError(f"Client {client_id} not found")
            
            client_data = client_doc.to_dict()
            account_name = client_data.get('name', 'Unknown')
            
            # Try to get API key from Firestore first, then from Secret Manager
            api_key = client_data.get('klaviyo_private_key')
            
            if not api_key:
                # Try to get from Secret Manager using client name
                secret_name = f"klaviyo-api-{account_name.lower().replace(' ', '-')}"
                logger.info(f"Attempting to get API key from Secret Manager: {secret_name}")
                api_key = self.get_secret(secret_name)
            
            if not api_key:
                # Try using client ID as fallback
                secret_name = f"klaviyo-api-{client_id.lower()}"
                logger.info(f"Attempting fallback secret: {secret_name}")
                api_key = self.get_secret(secret_name)
            
            if not api_key:
                raise ValueError(f"No API key found for client {client_id} ({account_name})")
            
            # Calculate date ranges
            today = datetime.now()
            month_start = today.replace(day=1)
            month_end = today
            
            # Previous month for comparison
            if today.month == 1:
                prev_month_start = today.replace(year=today.year-1, month=12, day=1)
                prev_month_end = datetime(today.year-1, 12, 31)
            else:
                prev_month_start = today.replace(month=today.month-1, day=1)
                prev_month_end = month_start - timedelta(days=1)
            
            # Last year same month for YoY comparison
            last_year_start = month_start.replace(year=today.year-1)
            last_year_end = month_end.replace(year=today.year-1)
            
            # Fetch current month metrics
            current_params = {
                "start_date": month_start.strftime('%Y-%m-%d'),
                "end_date": month_end.strftime('%Y-%m-%d')
            }
            
            campaigns_data = await self.call_mcp_tool(api_key, "get_campaigns", current_params)
            flows_data = await self.call_mcp_tool(api_key, "get_flows", current_params)
            revenue_data = await self.call_mcp_tool(api_key, "get_revenue_metrics", current_params)
            segment_data = await self.call_mcp_tool(api_key, "get_segment_performance", current_params)
            
            # Fetch previous month metrics for MoM
            prev_params = {
                "start_date": prev_month_start.strftime('%Y-%m-%d'),
                "end_date": prev_month_end.strftime('%Y-%m-%d')
            }
            prev_revenue_data = await self.call_mcp_tool(api_key, "get_revenue_metrics", prev_params)
            
            # Fetch last year metrics for YoY
            yoy_params = {
                "start_date": last_year_start.strftime('%Y-%m-%d'),
                "end_date": last_year_end.strftime('%Y-%m-%d')
            }
            yoy_revenue_data = await self.call_mcp_tool(api_key, "get_revenue_metrics", yoy_params)
            
            # Calculate monthly metrics
            total_revenue = revenue_data.get('total_revenue', 0)
            total_orders = revenue_data.get('total_orders', 0)
            emails_sent = revenue_data.get('emails_sent', 0)
            emails_opened = revenue_data.get('emails_opened', 0)
            emails_clicked = revenue_data.get('emails_clicked', 0)
            
            avg_open_rate = (emails_opened / emails_sent * 100) if emails_sent > 0 else 0
            avg_click_rate = (emails_clicked / emails_opened * 100) if emails_opened > 0 else 0
            avg_conversion_rate = (total_orders / emails_sent * 100) if emails_sent > 0 else 0
            avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
            
            # Calculate MoM and YoY changes
            prev_revenue = prev_revenue_data.get('total_revenue', 0)
            yoy_revenue = yoy_revenue_data.get('total_revenue', 0)
            
            mom_change = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else None
            yoy_change = ((total_revenue - yoy_revenue) / yoy_revenue * 100) if yoy_revenue > 0 else None
            
            # Get monthly goal from Firestore
            # Goals are stored per month/year, so filter for the report month
            # Some goals use client document ID, others use client name as client_id
            goals_ref = self.db.collection('goals')\
                .where('client_id', '==', client_id)\
                .where('month', '==', month_start.month)\
                .where('year', '==', month_start.year)\
                .limit(1)
            goals = list(goals_ref.stream())
            
            # If no goal found by document ID, try by client name
            if not goals:
                goals_ref = self.db.collection('goals')\
                    .where('client_id', '==', account_name)\
                    .where('month', '==', month_start.month)\
                    .where('year', '==', month_start.year)\
                    .limit(1)
                goals = list(goals_ref.stream())
            
            monthly_goal = None
            for goal in goals:
                goal_data = goal.to_dict()
                # Goals collection uses 'revenue_goal' field, not 'monthly_revenue_goal'
                monthly_goal = goal_data.get('revenue_goal')
                if monthly_goal:
                    logger.info(f"Found goal for {account_name}: ${monthly_goal:,.2f} for {month_start.month}/{month_start.year}")
            
            goal_achievement = (total_revenue / monthly_goal * 100) if monthly_goal else None
            
            # Get weekly performance data for best/worst week analysis
            weekly_reports = self.db.collection('reports')\
                .where('client_id', '==', client_id)\
                .where('report_type', '==', 'weekly')\
                .where('created_at', '>=', month_start)\
                .where('created_at', '<=', month_end)\
                .stream()
            
            weekly_performances = []
            for report in weekly_reports:
                report_data = report.to_dict()
                weekly_performances.append({
                    'week': report_data.get('week_ending'),
                    'revenue': report_data.get('weekly_revenue', 0)
                })
            
            best_week = max(weekly_performances, key=lambda x: x['revenue']) if weekly_performances else {}
            worst_week = min(weekly_performances, key=lambda x: x['revenue']) if weekly_performances else {}
            
            # Generate AI insights
            metrics_for_ai = {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "avg_open_rate": avg_open_rate,
                "avg_click_rate": avg_click_rate,
                "avg_conversion_rate": avg_conversion_rate,
                "monthly_goal": monthly_goal,
                "goal_achievement": goal_achievement,
                "mom_change": mom_change,
                "yoy_change": yoy_change
            }
            
            ai_insights, ai_actions = await self.generate_ai_insights(metrics_for_ai, "monthly")
            
            # Calculate next month projections
            growth_rate = mom_change / 100 if mom_change else 0.05  # Default 5% growth
            next_month_projection = {
                "projected_revenue": total_revenue * (1 + growth_rate),
                "projected_orders": int(total_orders * (1 + growth_rate)),
                "confidence": "high" if mom_change and mom_change > 0 else "medium"
            }
            
            # Create MonthlyMetrics object
            monthly_metrics = MonthlyMetrics(
                account_name=account_name,
                month=today.strftime('%B'),
                year=today.year,
                total_revenue=total_revenue,
                total_orders=total_orders,
                total_campaigns=len(campaigns_data.get('campaigns', [])),
                total_flows=len(flows_data.get('flows', [])),
                total_emails_sent=emails_sent,
                total_emails_opened=emails_opened,
                total_emails_clicked=emails_clicked,
                avg_open_rate=avg_open_rate,
                avg_click_rate=avg_click_rate,
                avg_conversion_rate=avg_conversion_rate,
                avg_order_value=avg_order_value,
                revenue_per_recipient=total_revenue / emails_sent if emails_sent > 0 else 0,
                monthly_goal=monthly_goal,
                goal_achievement_percent=goal_achievement,
                month_over_month_change=mom_change,
                year_over_year_change=yoy_change,
                best_performing_week=best_week,
                worst_performing_week=worst_week,
                top_campaigns=campaigns_data.get('top_campaigns', [])[:5],
                top_flows=flows_data.get('top_flows', [])[:5],
                customer_metrics=revenue_data.get('customer_metrics', {}),
                segment_performance=segment_data.get('segments', [])[:10],
                performance_summary=f"Generated ${total_revenue:,.2f} from {total_orders} orders in {today.strftime('%B %Y')}",
                strategic_recommendations=self.generate_strategic_recommendations(metrics_for_ai),
                ai_insights=ai_insights,
                next_month_projections=next_month_projection
            )
            
            # Store report in Firestore
            report_data = asdict(monthly_metrics)
            report_data['created_at'] = datetime.now()
            report_data['client_id'] = client_id
            report_data['report_type'] = 'monthly'
            
            self.db.collection('reports').add(report_data)
            
            # Send Slack notification
            await self.send_monthly_slack_notification(monthly_metrics, client_data)
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating monthly report for client {client_id}: {e}")
            raise
    
    def generate_recommendations(self, status: str) -> List[str]:
        """Generate actionable recommendations based on performance status"""
        recommendations = []
        
        if status == "at_risk":
            recommendations.extend([
                "🚨 Urgent: Launch flash sale or promotional campaign",
                "🎯 Increase email frequency to engaged segments",
                "📱 Activate SMS campaigns for quick conversions"
            ])
        elif status == "behind":
            recommendations.extend([
                "📈 Increase campaign frequency by 20%",
                "🎁 Test new promotional offers",
                "👥 Expand audience targeting"
            ])
        elif status == "on_track":
            recommendations.extend([
                "✅ Maintain current campaign cadence",
                "🔬 A/B test subject lines for improvement",
                "🎯 Focus on high-value customer segments"
            ])
        else:  # ahead
            recommendations.extend([
                "🚀 Test premium product offerings",
                "💎 Focus on customer retention",
                "📊 Optimize for higher AOV"
            ])
        
        return recommendations
    
    def generate_strategic_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate strategic recommendations for monthly reports"""
        recommendations = []
        
        # Revenue-based recommendations
        if metrics.get('goal_achievement', 0) < 90:
            recommendations.append("📈 Revenue fell short of goal - consider promotional calendar review")
        
        # Engagement-based recommendations
        if metrics.get('avg_open_rate', 0) < 20:
            recommendations.append("📧 Open rates below industry average - review subject line strategy")
        
        if metrics.get('avg_click_rate', 0) < 2:
            recommendations.append("🎯 Click rates need improvement - enhance email content and CTAs")
        
        # Growth-based recommendations
        if metrics.get('mom_change', 0) < 0:
            recommendations.append("📉 Month-over-month decline - investigate customer churn and win-back campaigns")
        
        if metrics.get('yoy_change', 0) > 20:
            recommendations.append("🎉 Strong YoY growth - scale successful strategies")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    async def send_slack_notification(self, metrics: WeeklyMetrics, client_data: Dict[str, Any]):
        """Send weekly report to Slack"""
        webhook_url = client_data.get('slack_webhook') or self.get_secret('slack-webhook')
        
        if not webhook_url:
            logger.info("No Slack webhook configured, skipping notification")
            return
        
        # Create status emoji
        status_emoji = {
            "ahead": "🚀",
            "on_track": "✅",
            "behind": "⚠️",
            "at_risk": "🚨",
            "no_goal": "📊"
        }.get(metrics.on_track_status, "📊")
        
        # Create progress bar
        progress = metrics.goal_progress_percent or 0
        progress_bar = self.create_progress_bar(progress)
        
        # Format Slack message
        slack_message = {
            "text": f"{status_emoji} Weekly Performance Update - {metrics.account_name}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} {metrics.account_name} - Weekly Update"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Week Ending:*\n{metrics.week_ending}"},
                        {"type": "mrkdwn", "text": f"*Status:*\n{metrics.on_track_status.replace('_', ' ').title()}"}
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📊 Weekly Performance*\n"
                               f"• Revenue: ${metrics.weekly_revenue:,.2f}\n"
                               f"• Orders: {metrics.weekly_orders}\n"
                               f"• Open Rate: {metrics.open_rate:.1f}%\n"
                               f"• Click Rate: {metrics.click_rate:.1f}%\n"
                               f"• Conversion Rate: {metrics.conversion_rate:.2f}%"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🎯 Monthly Goal Progress*\n"
                               f"{progress_bar} {progress:.1f}%\n"
                               f"• MTD Revenue: ${metrics.month_to_date_revenue:,.2f}\n"
                               f"• Goal: ${metrics.monthly_goal:,.2f}\n" if metrics.monthly_goal else ""
                               f"• Days Remaining: {metrics.days_remaining_in_month}"
                    }
                }
            ]
        }
        
        # Add AI insights if available
        if metrics.ai_insights:
            slack_message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🤖 AI Insights*\n" + "\n".join(f"• {insight}" for insight in metrics.ai_insights[:3])
                }
            })
        
        # Add recommendations
        if metrics.recommendations:
            slack_message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💡 Recommendations*\n" + "\n".join(metrics.recommendations[:3])
                }
            })
        
        # Send to Slack
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=slack_message)
                if response.status_code == 200:
                    logger.info(f"Slack notification sent for {metrics.account_name}")
                else:
                    logger.error(f"Failed to send Slack notification: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    async def send_monthly_slack_notification(self, metrics: MonthlyMetrics, client_data: Dict[str, Any]):
        """Send monthly report to Slack"""
        webhook_url = client_data.get('slack_webhook') or self.get_secret('slack-webhook')
        
        if not webhook_url:
            logger.info("No Slack webhook configured, skipping notification")
            return
        
        # Determine performance emoji
        if metrics.goal_achievement_percent:
            if metrics.goal_achievement_percent >= 100:
                status_emoji = "🎉"
            elif metrics.goal_achievement_percent >= 90:
                status_emoji = "✅"
            elif metrics.goal_achievement_percent >= 75:
                status_emoji = "⚠️"
            else:
                status_emoji = "🚨"
        else:
            status_emoji = "📊"
        
        # Format Slack message
        slack_message = {
            "text": f"{status_emoji} Monthly Performance Report - {metrics.account_name}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} {metrics.account_name} - {metrics.month} {metrics.year} Report"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": metrics.performance_summary
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Total Revenue:*\n${metrics.total_revenue:,.2f}"},
                        {"type": "mrkdwn", "text": f"*Total Orders:*\n{metrics.total_orders:,}"},
                        {"type": "mrkdwn", "text": f"*Avg Order Value:*\n${metrics.avg_order_value:.2f}"},
                        {"type": "mrkdwn", "text": f"*Goal Achievement:*\n{metrics.goal_achievement_percent:.1f}%" if metrics.goal_achievement_percent else {"type": "mrkdwn", "text": "*Goal:*\nNot Set"}}
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*MoM Change:*\n{metrics.month_over_month_change:+.1f}%" if metrics.month_over_month_change else {"type": "mrkdwn", "text": "*MoM:*\nN/A"}},
                        {"type": "mrkdwn", "text": f"*YoY Change:*\n{metrics.year_over_year_change:+.1f}%" if metrics.year_over_year_change else {"type": "mrkdwn", "text": "*YoY:*\nN/A"}},
                        {"type": "mrkdwn", "text": f"*Open Rate:*\n{metrics.avg_open_rate:.1f}%"},
                        {"type": "mrkdwn", "text": f"*Click Rate:*\n{metrics.avg_click_rate:.1f}%"}
                    ]
                }
            ]
        }
        
        # Add top campaigns
        if metrics.top_campaigns:
            campaign_text = "*🏆 Top Campaigns*\n"
            for i, campaign in enumerate(metrics.top_campaigns[:3], 1):
                campaign_text += f"{i}. {campaign.get('name', 'Unknown')} - ${campaign.get('revenue', 0):,.2f}\n"
            
            slack_message["blocks"].append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": campaign_text}
            })
        
        # Add AI insights
        if metrics.ai_insights:
            slack_message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🤖 AI Analysis*\n" + "\n".join(f"• {insight}" for insight in metrics.ai_insights)
                }
            })
        
        # Add strategic recommendations
        if metrics.strategic_recommendations:
            slack_message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 Strategic Recommendations*\n" + "\n".join(metrics.strategic_recommendations)
                }
            })
        
        # Add next month projection
        if metrics.next_month_projections:
            slack_message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔮 Next Month Projection*\n"
                           f"• Revenue: ${metrics.next_month_projections['projected_revenue']:,.2f}\n"
                           f"• Orders: {metrics.next_month_projections['projected_orders']:,}\n"
                           f"• Confidence: {metrics.next_month_projections['confidence'].title()}"
                }
            })
        
        # Send to Slack
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=slack_message)
                if response.status_code == 200:
                    logger.info(f"Monthly Slack notification sent for {metrics.account_name}")
                else:
                    logger.error(f"Failed to send monthly Slack notification: {response.text}")
        except Exception as e:
            logger.error(f"Error sending monthly Slack notification: {e}")
    
    def create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a visual progress bar for Slack"""
        filled = int(width * percentage / 100)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    async def generate_all_weekly_reports(self):
        """Generate weekly reports for all active clients"""
        try:
            # Get all active clients from Firestore
            clients = self.db.collection('clients').where('is_active', '==', True).stream()
            
            results = []
            for client in clients:
                client_data = client.to_dict()
                client_id = client.id
                
                try:
                    logger.info(f"Generating weekly report for {client_data.get('name')}")
                    report = await self.generate_weekly_report(client_id)
                    results.append({
                        "client_id": client_id,
                        "client_name": client_data.get('name'),
                        "status": "success",
                        "report_id": report.get('id')
                    })
                except Exception as e:
                    logger.error(f"Failed to generate report for {client_data.get('name')}: {e}")
                    results.append({
                        "client_id": client_id,
                        "client_name": client_data.get('name'),
                        "status": "failed",
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating weekly reports: {e}")
            raise
    
    async def generate_all_monthly_reports(self):
        """Generate monthly reports for all active clients"""
        try:
            # Get all active clients from Firestore
            clients = self.db.collection('clients').where('is_active', '==', True).stream()
            
            results = []
            for client in clients:
                client_data = client.to_dict()
                client_id = client.id
                
                try:
                    logger.info(f"Generating monthly report for {client_data.get('name')}")
                    report = await self.generate_monthly_report(client_id)
                    results.append({
                        "client_id": client_id,
                        "client_name": client_data.get('name'),
                        "status": "success",
                        "report_id": report.get('id')
                    })
                except Exception as e:
                    logger.error(f"Failed to generate monthly report for {client_data.get('name')}: {e}")
                    results.append({
                        "client_id": client_id,
                        "client_name": client_data.get('name'),
                        "status": "failed",
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating monthly reports: {e}")
            raise


# Export for use in FastAPI
performance_monitor = PerformanceMonitorService()