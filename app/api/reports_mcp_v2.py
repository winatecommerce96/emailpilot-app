# app/api/reports_mcp_v2.py
"""
MCP-based Reports API using Revenue API's MCP capabilities
Uses the Revenue API's built-in MCP endpoints for generating comprehensive weekly reports
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import logging
import asyncio
import httpx
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass

from google.cloud import firestore
from app.deps.firestore import get_db
from app.deps.secrets import get_secret_manager_service
from app.utils.klaviyo_api import ensure_klaviyo_api_available, get_base_url
from app.services.performance_monitor import performance_monitor

# Import AI Orchestrator as primary interface
try:
    from app.core.ai_orchestrator import get_ai_orchestrator, ai_complete
    AI_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    AI_ORCHESTRATOR_AVAILABLE = False
    # Fallback to legacy AI Models Service - runtime import only
    from app.services.ai_models_service import get_ai_models_service

# Type checking imports
if TYPE_CHECKING:
    from app.services.secrets import SecretManagerService
    from app.services.ai_models_service import AIModelsService
    from app.services.slack_alerts import SlackAlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/mcp/v2", tags=["MCP Reports V2"])

@dataclass
class MCPWeeklyReport:
    """Data class for MCP-based weekly report"""
    total_revenue: float
    total_campaign_revenue: float
    total_flow_revenue: float
    client_count: int
    clients_with_revenue: int
    client_details: List[Dict[str, Any]]
    generated_at: str
    report_period: str


@router.get("/self-test")
async def weekly_insights_self_test(
    limit_clients: int = 2,
    metrics_only: bool = True,
    concurrency: int = 5,
    per_client_timeout: float = 8.0,
    db: firestore.Client = Depends(get_db)
):
    """Lightweight smoke-test for the weekly insights pipeline.

    - Fetches up to `limit_clients` client docs.
    - Calls Klaviyo API weekly/full per client with concurrency and timeouts.
    - Returns summary and per-client metrics/errors without AI or Slack.
    """
    await ensure_klaviyo_api_available()
    api_base = get_base_url()

    clients = list(db.collection("clients").stream())
    if not clients:
        raise HTTPException(status_code=404, detail="No clients found")

    clients = clients[: max(1, int(limit_clients))]
    sem = asyncio.Semaphore(max(1, int(concurrency)))

    async def fetch_one(name: str, slug: str, cid: str) -> Dict[str, Any]:
        async with sem:
            try:
                timeout = httpx.Timeout(per_client_timeout, connect=per_client_timeout / 3)
                async with httpx.AsyncClient(timeout=timeout) as c:
                    r = await c.get(f"{api_base}/clients/{slug}/weekly/full")
                    if r.status_code == 404 and slug != cid:
                        r = await c.get(f"{api_base}/clients/{cid}/weekly/full")
                    full = r.json() if r.status_code == 200 else {}
                return {
                    "account_name": name,
                    "weekly_revenue": float(full.get("weekly_revenue", 0) or 0),
                    "weekly_orders": int(full.get("weekly_orders", 0) or 0),
                    "campaign_revenue": float(full.get("campaign_revenue", 0) or 0),
                    "flow_revenue": float(full.get("flow_revenue", 0) or 0),
                    "status": "ok" if full else "empty",
                }
            except Exception as e:
                return {"account_name": name, "error": str(e), "weekly_revenue": 0.0, "weekly_orders": 0}

    tasks = []
    for doc in clients:
        cid = doc.id
        data = doc.to_dict() or {}
        name = data.get("name", cid)
        slug = data.get("client_slug", cid)
        tasks.append(fetch_one(name, slug, cid))

    results = await asyncio.gather(*tasks, return_exceptions=False)

    total_revenue = 0.0
    total_orders = 0
    total_campaign_revenue = 0.0
    total_flow_revenue = 0.0
    for r in results:
        try:
            total_revenue += float(r.get("weekly_revenue", 0) or 0)
            total_orders += int(r.get("weekly_orders", 0) or 0)
            total_campaign_revenue += float(r.get("campaign_revenue", 0) or 0)
            total_flow_revenue += float(r.get("flow_revenue", 0) or 0)
        except Exception:
            pass

    return {
        "success": True,
        "summary": {
            "clients": len(results),
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_campaign_revenue": total_campaign_revenue,
            "total_flow_revenue": total_flow_revenue,
        },
        "client_metrics": results,
        "note": "Self-test performs metrics fetch only; AI and Slack are skipped.",
    }

@router.post("/weekly/generate")
async def generate_weekly_report_mcp_v2(
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """
    Generate weekly report using the Revenue API's MCP process.
    This calls the Revenue API which already has MCP capabilities built in.
    """
    try:
        logger.info("Starting MCP-based weekly report generation via Revenue API...")
        
        # Get all clients from Firestore
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        
        if not clients:
            logger.warning("No clients found in Firestore")
            return JSONResponse(
                status_code=404,
                content={"error": "No clients found in database"}
            )
        
        logger.info(f"Found {len(clients)} clients to process")
        
        # Ensure Klaviyo API is available and get base URL
        await ensure_klaviyo_api_available()
        revenue_api_base = get_base_url()

        # Best-effort: start OpenAPI MCP inside the Revenue API, ignore failures
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                mcp_status_response = await client.get(f"{revenue_api_base}/admin/mcp/status")
                if mcp_status_response.status_code == 200:
                    status = mcp_status_response.json()
                    if status.get("openapi_revenue") != "running":
                        _ = await client.post(
                            f"{revenue_api_base}/admin/mcp/start",
                            json={"kind": "openapi_revenue"}
                        )
        except Exception:
            # Non-fatal: continue without MCP running
            pass
        
        # Process each client through Revenue API
        client_results = []
        total_revenue = 0.0
        total_campaign_revenue = 0.0
        total_flow_revenue = 0.0
        clients_with_revenue = 0
        
        # Calculate date range for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        for client_doc in clients:
            client_id = client_doc.id
            client_data = client_doc.to_dict() or {}
            client_name = client_data.get("name", client_data.get("client_name", f"Client {client_id}"))
            client_slug = client_data.get("client_slug", client_id)
            
            logger.info(f"Processing {client_name} (slug: {client_slug}) via Revenue API MCP...")
            
            try:
                # Call Revenue API for this client using last 7 days
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Use the Revenue API endpoint directly
                    url = f"{revenue_api_base}/clients/{client_slug}/revenue/last7"
                    params = {
                        "start": start_date.strftime("%Y-%m-%dT00:00:00Z"),
                        "end": end_date.strftime("%Y-%m-%dT23:59:59Z"),
                        "recompute": "true"
                    }
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        campaign_rev = float(data.get("campaign_total", 0))
                        flow_rev = float(data.get("flow_total", 0))
                        total_rev = float(data.get("total", 0))
                        
                        client_results.append({
                            "client_id": client_id,
                            "client_name": client_name,
                            "client_slug": client_slug,
                            "campaign_revenue": campaign_rev,
                            "flow_revenue": flow_rev,
                            "total_revenue": total_rev,
                            "success": True
                        })
                        
                        total_revenue += total_rev
                        total_campaign_revenue += campaign_rev
                        total_flow_revenue += flow_rev
                        
                        if total_rev > 0:
                            clients_with_revenue += 1
                        
                        logger.info(f"✅ {client_name}: ${total_rev:,.2f} (Campaign: ${campaign_rev:,.2f}, Flow: ${flow_rev:,.2f})")
                        
                    elif response.status_code == 400 and "Unable to resolve Klaviyo API key" in response.text:
                        logger.info(f"🔑 {client_name}: No API key configured")
                        client_results.append({
                            "client_id": client_id,
                            "client_name": client_name,
                            "client_slug": client_slug,
                            "campaign_revenue": 0,
                            "flow_revenue": 0,
                            "total_revenue": 0,
                            "success": False,
                            "error": "No API key"
                        })
                    else:
                        logger.warning(f"❌ {client_name}: API returned {response.status_code}")
                        client_results.append({
                            "client_id": client_id,
                            "client_name": client_name,
                            "client_slug": client_slug,
                            "campaign_revenue": 0,
                            "flow_revenue": 0,
                            "total_revenue": 0,
                            "success": False,
                            "error": f"API error {response.status_code}"
                        })
                        
                # Add delay between clients to avoid rate limiting
                await asyncio.sleep(1.0)
                
            except asyncio.TimeoutError:
                logger.error(f"❌ {client_name}: Request timeout")
                client_results.append({
                    "client_id": client_id,
                    "client_name": client_name,
                    "client_slug": client_slug,
                    "campaign_revenue": 0,
                    "flow_revenue": 0,
                    "total_revenue": 0,
                    "success": False,
                    "error": "Timeout"
                })
            except Exception as e:
                logger.error(f"❌ {client_name}: {e}")
                client_results.append({
                    "client_id": client_id,
                    "client_name": client_name,
                    "client_slug": client_slug,
                    "campaign_revenue": 0,
                    "flow_revenue": 0,
                    "total_revenue": 0,
                    "success": False,
                    "error": str(e)
                })
        
        # Sort clients by revenue
        client_results.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)
        
        # Create report summary
        report = MCPWeeklyReport(
            total_revenue=total_revenue,
            total_campaign_revenue=total_campaign_revenue,
            total_flow_revenue=total_flow_revenue,
            client_count=len(client_results),
            clients_with_revenue=clients_with_revenue,
            client_details=client_results,
            generated_at=datetime.now().isoformat(),
            report_period=f"Last 7 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
        )
        
        logger.info(f"MCP Weekly report compiled: ${total_revenue:,.2f} from {clients_with_revenue} clients")
        
        # Send to Slack in background
        background_tasks.add_task(_send_mcp_report_to_slack_v2, report, secret_manager)
        
        # Return success response
        return {
            "success": True,
            "message": "MCP-based weekly report generated successfully",
            "summary": {
                "total_revenue": total_revenue,
                "total_campaign_revenue": total_campaign_revenue,
                "total_flow_revenue": total_flow_revenue,
                "client_count": len(client_results),
                "clients_with_revenue": clients_with_revenue,
                "generated_at": report.generated_at,
                "report_period": report.report_period
            },
            "client_details": client_results
        }
        
    except Exception as e:
        logger.error(f"MCP weekly report generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate MCP weekly report: {str(e)}"
        )

async def _send_mcp_report_to_slack_v2(report: MCPWeeklyReport, secret_manager: "SecretManagerService"):
    """Send the MCP-generated weekly report to Slack"""
    try:
        logger.info("Sending MCP weekly report to Slack...")
        
        # Get Slack webhook URL from Secret Manager (standard name), with fallbacks
        try:
            # Preferred secret id
            webhook_url = secret_manager.get_secret("emailpilot-slack-webhook-url")
            if not webhook_url:
                # Legacy/alternate secret id
                webhook_url = secret_manager.get_secret("slack-webhook-url")
        except Exception:
            webhook_url = None
        if not webhook_url:
            # Fallback to environment variable
            import os
            webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            
        if not webhook_url:
            logger.warning("No Slack webhook URL configured")
            return
        
        # Format client details
        client_blocks = []
        for client in report.client_details[:10]:  # Top 10 clients
            if client.get("success") and client.get("total_revenue", 0) > 0:
                emoji = "💰" if client["total_revenue"] > 5000 else "💵" if client["total_revenue"] > 1000 else "💸"
                client_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{client['client_name']}*\n"
                                f"Total: ${client['total_revenue']:,.2f}\n"
                                f"• Campaigns: ${client['campaign_revenue']:,.2f}\n"
                                f"• Flows: ${client['flow_revenue']:,.2f}"
                    }
                })
        
        # Determine performance status
        avg_revenue = report.total_revenue / report.client_count if report.client_count > 0 else 0
        if report.total_revenue > 50000:
            status_emoji = "🚀"
            status_text = "Outstanding Week!"
        elif report.total_revenue > 20000:
            status_emoji = "✅"
            status_text = "Great Performance"
        elif report.total_revenue > 10000:
            status_emoji = "📊"
            status_text = "Good Progress"
        else:
            status_emoji = "📈"
            status_text = "Building Momentum"
        
        # Create Slack message with rich formatting
        slack_message = {
            "text": f"{status_emoji} EmailPilot Weekly Revenue Report - ${report.total_revenue:,.2f}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} Weekly Revenue Report",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{status_text}*\n{report.report_period}"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*💰 Total Revenue*\n${report.total_revenue:,.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*📧 Campaign Revenue*\n${report.total_campaign_revenue:,.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*🔄 Flow Revenue*\n${report.total_flow_revenue:,.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*📊 Active Clients*\n{report.clients_with_revenue} of {report.client_count}"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🏆 Top Performing Clients*"
                    }
                }
            ] + client_blocks + [
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Generated via Revenue API MCP Process | {report.generated_at}"
                        }
                    ]
                }
            ]
        }
        
        # Send to Slack
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=slack_message)
            if response.status_code == 200:
                logger.info("✅ MCP weekly report sent to Slack successfully")
            else:
                logger.error(f"❌ Failed to send to Slack: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"Error sending MCP weekly report to Slack: {e}")


# --- Weekly Insights and Company Summary (MCP + AI prompts) ---

def _select_ai_provider(ai: "AIModelsService") -> str:
    # Rough heuristic based on initialized clients
    for p in ("gemini", "claude", "openai"):
        try:
            # If initialized, it's in _api_clients
            if getattr(ai, "_api_clients", {}).get(p):
                return p
        except Exception:
            continue
    return "gemini"


async def _run_prompt_text(ai: "AIModelsService", text: str, prefer: Optional[str] = None) -> str:
    provider = prefer or _select_ai_provider(ai)
    try:
        if provider == "gemini":
            return await ai._execute_gemini(text, "gemini-1.5-pro-latest")
        if provider == "claude":
            return await ai._execute_claude(text, "claude-3-sonnet")
        return await ai._execute_openai(text, "gpt-4")
    except Exception:
        # Fallback chain
        for p in ("claude", "openai", "gemini"):
            if p == provider:
                continue
            try:
                if p == "gemini":
                    return await ai._execute_gemini(text, "gemini-1.5-pro-latest")
                if p == "claude":
                    return await ai._execute_claude(text, "claude-3-sonnet")
                return await ai._execute_openai(text, "gpt-4")
            except Exception:
                continue
        return "INSIGHTS:\n• Unable to generate insights.\n\nACTIONS:\n• Configure AI providers."


@router.post("/weekly/insights")
async def generate_weekly_insights(
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service),
    send_client_posts: Optional[bool] = Body(default=None),
    preview: bool = Body(default=False),
    client_slugs: Optional[List[str]] = Body(default=None, description="Limit to these client slugs/IDs"),
    limit_clients: Optional[int] = Body(default=None, description="Process at most this many clients"),
    metrics_only: bool = Body(default=False, description="Skip AI prompt generation; return metrics only"),
    concurrency: int = Body(default=5, description="Max concurrent client fetches"),
    per_client_timeout: float = Body(default=12.0, description="Timeout (seconds) per client metrics fetch"),
):
    """Generate weekly per-client insights and a company-wide summary using provided prompts.

    - Collects metrics for all clients (combines PerformanceMonitor for rich metrics + Klaviyo API MCP for revenue split)
    - Renders two prompts: per-client insights; company-wide insights
    - Sends results to Slack (rich blocks) and returns JSON
    """
    await ensure_klaviyo_api_available()
    api_base = get_base_url()

    ai = get_ai_models_service(db, secret_manager)
    slack = SlackAlertService(secret_manager)

    clients = list(db.collection("clients").stream())
    if not clients:
        raise HTTPException(status_code=404, detail="No clients found")

    # Apply admin default for per-client posts if not specified by request
    if send_client_posts is None:
        try:
            sref = db.collection("app_settings").document("reports")
            sdoc = sref.get()
            if sdoc.exists:
                sdata = sdoc.to_dict() or {}
                send_client_posts = bool(sdata.get("weekly_send_client_posts_default", False))
            else:
                send_client_posts = False
        except Exception:
            send_client_posts = False

    all_metrics: list[dict] = []
    total_revenue = 0.0
    total_orders = 0
    total_campaign_revenue = 0.0
    total_flow_revenue = 0.0
    status_counts = {"ahead": 0, "on_track": 0, "behind": 0, "at_risk": 0}

    # Collect per-client metrics
    # Concurrency-limited client fetch
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    async def fetch_one(name: str, slug: str, cid: str) -> Dict[str, Any]:
        async with sem:
            try:
                timeout = httpx.Timeout(per_client_timeout, connect=per_client_timeout/3)
                async with httpx.AsyncClient(timeout=timeout) as c:
                    r = await c.get(f"{api_base}/clients/{slug}/weekly/full")
                    if r.status_code == 404 and slug != cid:
                        r = await c.get(f"{api_base}/clients/{cid}/weekly/full")
                    full = r.json() if r.status_code == 200 else {}
                pm = {
                    "account_name": name,
                    "weekly_revenue": float(full.get("weekly_revenue", 0)),
                    "weekly_orders": int(full.get("weekly_orders", 0)),
                    "campaign_revenue": float(full.get("campaign_revenue", 0)),
                    "campaign_orders": int(full.get("campaign_orders", 0)),
                    "flow_revenue": float(full.get("flow_revenue", 0)),
                    "flow_orders": int(full.get("flow_orders", 0)),
                    "open_rate": float(full.get("open_rate", 0)),
                    "click_rate": float(full.get("click_rate", 0)),
                    "click_through_rate": float(full.get("click_through_rate", full.get("click_rate", 0) or 0)),
                    "conversion_rate": float(full.get("conversion_rate", 0)),
                    "avg_order_value": float(full.get("avg_order_value", 0)),
                    "revenue_per_recipient": float(full.get("revenue_per_recipient", 0)),
                    "week_over_week_change": full.get("week_over_week_change"),
                    "goal_progress_percent": None,
                    "on_track_status": "unknown",
                }
                return {
                    "account_name": pm["account_name"],
                    "weekly_revenue": pm["weekly_revenue"],
                    "weekly_orders": pm["weekly_orders"],
                    "campaign_revenue": pm["campaign_revenue"],
                    "campaign_orders": pm["campaign_orders"],
                    "flow_revenue": pm["flow_revenue"],
                    "flow_orders": pm["flow_orders"],
                    "open_rate": pm["open_rate"],
                    "click_rate": pm["click_rate"],
                    "click_through_rate": pm["click_through_rate"],
                    "conversion_rate": pm["conversion_rate"],
                    "avg_order_value": pm["avg_order_value"],
                    "revenue_per_recipient": pm["revenue_per_recipient"],
                    "wow_change": pm.get("week_over_week_change"),
                    "goal_progress": pm.get("goal_progress_percent"),
                    "on_track_status": pm.get("on_track_status", "unknown"),
                }
            except Exception as e:
                return {"account_name": name, "error": str(e), "weekly_revenue": 0.0, "weekly_orders": 0}

    tasks = []
    for doc in clients:
        if limit_clients is not None and len(tasks) >= limit_clients:
            break
        cid = doc.id
        data = doc.to_dict() or {}
        name = data.get("name", cid)
        slug = data.get("client_slug", cid)
        if client_slugs is not None and slug not in client_slugs and cid not in client_slugs:
            continue
        tasks.append(fetch_one(name, slug, cid))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=False)
        for metrics_data in results:
            # Aggregate totals
            try:
                total_revenue += float(metrics_data.get("weekly_revenue", 0) or 0)
                total_orders += int(metrics_data.get("weekly_orders", 0) or 0)
                total_campaign_revenue += float(metrics_data.get("campaign_revenue", 0) or 0)
                total_flow_revenue += float(metrics_data.get("flow_revenue", 0) or 0)
                status = metrics_data.get("on_track_status", "unknown")
                if status in status_counts:
                    status_counts[status] += 1
            except Exception:
                pass
            all_metrics.append(metrics_data)

    # Render prompts
    client_insights = []
    # Try to use admin-managed prompts if available
    # Load admin settings for prompt overrides
    settings_ref = db.collection("app_settings").document("reports")
    settings_doc = settings_ref.get()
    settings = settings_doc.to_dict() if settings_doc.exists else {}
    client_prompt_id_override = settings.get("weekly_client_prompt_id")
    company_prompt_id_override = settings.get("weekly_company_prompt_id")

    client_prompt_cfg = await ai.get_prompt(client_prompt_id_override) if client_prompt_id_override else await ai.get_prompt("weekly_client_insights")
    company_prompt_cfg = await ai.get_prompt(company_prompt_id_override) if company_prompt_id_override else await ai.get_prompt("weekly_company_summary")

    # Auto-seed prompts if missing
    def _ensure_prompt(doc_id: str, name: str, desc: str, template: str, provider: str = "gemini", model: str = "gemini-1.5-pro-latest", variables: list[str] = []):
        try:
            ref = db.collection("ai_prompts").document(doc_id)
            if not ref.get().exists:
                ref.set({
                    "name": name,
                    "description": desc,
                    "prompt_template": template,
                    "model_provider": provider,
                    "model_name": model,
                    "category": "analysis",
                    "variables": variables,
                    "active": True,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                })
        except Exception as se:
            logger.warning(f"Failed to seed prompt {doc_id}: {se}")

    if metrics_only:
        # Fast return without AI
        return {
            "success": True,
            "summary": {
                "clients": len(all_metrics),
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "total_campaign_revenue": total_campaign_revenue,
                "total_flow_revenue": total_flow_revenue,
                "status_counts": status_counts,
            },
            "client_metrics": all_metrics,
            "note": "metrics_only=true; AI prompt generation skipped"
        }

    if not client_prompt_cfg:
        client_template = (
            "You are a CRM expert analyzing weekly Klaviyo performance for {account_name}\n\n"
            "WEEKLY PERFORMANCE DATA:\n"
            "- Total Revenue: ${weekly_revenue}\n"
            "- Total Orders: {weekly_orders}\n"
            "- Campaign Revenue: ${campaign_revenue} ({campaign_orders} orders)\n"
            "- Flow Revenue: ${flow_revenue} ({flow_orders} orders)\n"
            "- Overall Open Rate: {open_rate}%\n"
            "- Overall Click Rate: {click_rate}%\n"
            "- Click Through Rate: {click_through_rate}%\n"
            "- Conversion Rate: {conversion_rate}%\n"
            "- Average Order Value: ${avg_order_value}\n"
            "- Revenue per Recipient: ${revenue_per_recipient}\n"
            "- Week over Week Change: {wow_change}\n"
            "- Monthly Goal Progress: {goal_progress}\n"
            "- Status: {on_track_status}\n\n"
            "Provide exactly 4 bullet point insights about performance and exactly 4 bullet point action items.\n\n"
            "Format your response as:\n"
            "INSIGHTS:\n"
            "• [insight 1]\n"
            "• [insight 2]\n"
            "• [insight 3]\n"
            "• [insight 4]\n\n"
            "ACTIONS:\n"
            "• [action 1]\n"
            "• [action 2]\n"
            "• [action 3]\n"
            "• [action 4]"
        )
        _ensure_prompt(
            "weekly_client_insights",
            "Weekly Client Insights",
            "Per-client weekly insights (4+4)",
            client_template,
            variables=[
                "account_name","weekly_revenue","weekly_orders","campaign_revenue","campaign_orders",
                "flow_revenue","flow_orders","open_rate","click_rate","click_through_rate","conversion_rate",
                "avg_order_value","revenue_per_recipient","wow_change","goal_progress","on_track_status"
            ],
        )
        client_prompt_cfg = await ai.get_prompt("weekly_client_insights")

    if not company_prompt_cfg:
        company_template = (
            "You are a CRM expert analyzing company-wide weekly Klaviyo performance across {client_count} client accounts.\n\n"
            "COMPANY-WIDE PERFORMANCE:\n"
            "- Total Weekly Revenue: ${total_revenue} across {client_count} clients\n"
            "- Total Weekly Orders: {total_orders}\n"
            "- Campaign Revenue: ${total_campaign_revenue} ({share_campaign}% of total)\n"
            "- Flow Revenue: ${total_flow_revenue} ({share_flow}% of total)\n"
            "- Account Status: {status_ahead} ahead, {status_on_track} on track, {status_behind} behind, {status_at_risk} at risk\n\n"
            "CLIENT BREAKDOWN:\n{client_breakdown}\n\n"
            "Provide exactly 4 company-wide insights and exactly 4 strategic action items.\n\n"
            "Format your response as:\n"
            "INSIGHTS:\n"
            "• [company insight 1]\n"
            "• [company insight 2]\n"
            "• [company insight 3]\n"
            "• [company insight 4]\n\n"
            "ACTIONS:\n"
            "• [strategic action 1]\n"
            "• [strategic action 2]\n"
            "• [strategic action 3]\n"
            "• [strategic action 4]"
        )
        _ensure_prompt(
            "weekly_company_summary",
            "Weekly Company Summary",
            "Company-wide weekly insights (4+4)",
            company_template,
            variables=[
                "client_count","total_revenue","total_orders","total_campaign_revenue","share_campaign",
                "total_flow_revenue","share_flow","status_ahead","status_on_track","status_behind","status_at_risk",
                "client_breakdown"
            ],
        )
        company_prompt_cfg = await ai.get_prompt("weekly_company_summary")

    for m in all_metrics:
        if m.get("error"):
            client_insights.append({"account_name": m.get("account_name"), "insights": "", "actions": "", "error": m["error"]})
            continue
        # Build variables (preformatted for readability)
        vars = {
            "account_name": m["account_name"],
            "weekly_revenue": f"{m['weekly_revenue']:,.2f}",
            "weekly_orders": f"{m['weekly_orders']:,}",
            "campaign_revenue": f"{m['campaign_revenue']:,.2f}",
            "campaign_orders": f"{m['campaign_orders']:,}",
            "flow_revenue": f"{m['flow_revenue']:,.2f}",
            "flow_orders": f"{m['flow_orders']:,}",
            "open_rate": f"{m['open_rate']:.1f}",
            "click_rate": f"{m['click_rate']:.1f}",
            "click_through_rate": f"{m['click_through_rate']:.1f}",
            "conversion_rate": f"{m['conversion_rate']:.2f}",
            "avg_order_value": f"{m['avg_order_value']:.2f}",
            "revenue_per_recipient": f"{m['revenue_per_recipient']:.3f}",
            "wow_change": m.get("wow_change", "N/A"),
            "goal_progress": m.get("goal_progress", "N/A"),
            "on_track_status": m.get("on_track_status", "unknown"),
        }
        if client_prompt_cfg:
            exec_res = await ai.execute_prompt(
                prompt_id=client_prompt_cfg["id"],
                variables=vars,
                override_provider=client_prompt_cfg.get("model_provider"),
                override_model=client_prompt_cfg.get("model_name"),
            )
            text = exec_res.get("response") if exec_res.get("success") else ""
            prompt_text = exec_res.get("rendered_prompt", "")
        else:
            prompt_text = (
                f"You are a CRM expert analyzing weekly Klaviyo performance for {m['account_name']}\n\n"
                f"WEEKLY PERFORMANCE DATA:\n"
                f"- Total Revenue: ${m['weekly_revenue']:,.2f}\n"
                f"- Total Orders: {m['weekly_orders']}\n"
                f"- Campaign Revenue: ${m['campaign_revenue']:,.2f} ({m['campaign_orders']} orders)\n"
                f"- Flow Revenue: ${m['flow_revenue']:,.2f} ({m['flow_orders']} orders)\n"
                f"- Overall Open Rate: {m['open_rate']:.1f}%\n"
                f"- Overall Click Rate: {m['click_rate']:.1f}%\n"
                f"- Click Through Rate: {m['click_through_rate']:.1f}%\n"
                f"- Conversion Rate: {m['conversion_rate']:.2f}%\n"
                f"- Average Order Value: ${m['avg_order_value']:.2f}\n"
                f"- Revenue per Recipient: ${m['revenue_per_recipient']:.3f}\n"
                f"- Week over Week Change: {m.get('wow_change','N/A')}\n"
                f"- Monthly Goal Progress: {m.get('goal_progress','N/A')}\n"
                f"- Status: {m.get('on_track_status','unknown')}\n\n"
                "Provide exactly 4 bullet point insights about performance and exactly 4 bullet point action items.\n\n"
                "Format your response as:\n"
                "INSIGHTS:\n"
                "• [insight 1]\n"
                "• [insight 2]\n"
                "• [insight 3]\n"
                "• [insight 4]\n\n"
                "ACTIONS:\n"
                "• [action 1]\n"
                "• [action 2]\n"
                "• [action 3]\n"
                "• [action 4]"
            )
            text = await _run_prompt_text(ai, prompt_text)
        # Simple accuracy/format check: 4 bullets in each section
        def _count_bullets(section: str) -> int:
            return sum(1 for line in section.splitlines() if line.strip().startswith("• "))
        insights_count = _count_bullets(text.split("ACTIONS:")[0]) if "ACTIONS:" in text else _count_bullets(text)
        actions_part = text.split("ACTIONS:")[-1] if "ACTIONS:" in text else ""
        actions_count = _count_bullets(actions_part)
        format_ok = ("INSIGHTS:" in text and "ACTIONS:" in text and insights_count >= 4 and actions_count >= 4)
        client_insights.append({
            "account_name": m["account_name"],
            "prompt": prompt_text,
            "response": text,
            "metrics": m,
            "insights_count": insights_count,
            "actions_count": actions_count,
            "format_ok": format_ok,
        })
        if send_client_posts and not preview:
            try:
                webhook = await slack._get_slack_webhook_url()
                if webhook:
                    blocks = [
                        {"type": "header", "text": {"type": "plain_text", "text": f"📊 Weekly Insights — {m['account_name']}"}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}},
                    ]
                    await slack._send_to_slack(webhook, {"text": f"Weekly insights — {m['account_name']}", "blocks": blocks})
            except Exception as e:
                logger.warning(f"Failed to post client insights for {m['account_name']}: {e}")

    # Company-wide summary prompt
    def _client_line(m: dict) -> str:
        wow = m.get("wow_change")
        if wow is None or wow == "N/A":
            return f"- {m['account_name']}: ${m['weekly_revenue']:,.0f} ({m.get('on_track_status','unknown')})"
        try:
            return f"- {m['account_name']}: ${m['weekly_revenue']:,.0f} ({m.get('on_track_status','unknown')}, {float(wow):+.1f}% WoW)"
        except Exception:
            return f"- {m['account_name']}: ${m['weekly_revenue']:,.0f} ({m.get('on_track_status','unknown')})"

    breakdown = "\n".join(_client_line(m) for m in all_metrics)
    share_campaign = (total_campaign_revenue / total_revenue * 100) if total_revenue > 0 else 0
    share_flow = (total_flow_revenue / total_revenue * 100) if total_revenue > 0 else 0
    company_prompt = (
        f"You are a CRM expert analyzing company-wide weekly Klaviyo performance across {len(all_metrics)} client accounts.\n\n"
        f"COMPANY-WIDE PERFORMANCE:\n"
        f"- Total Weekly Revenue: ${total_revenue:,.2f} across {len(all_metrics)} clients\n"
        f"- Total Weekly Orders: {total_orders}\n"
        f"- Campaign Revenue: ${total_campaign_revenue:,.2f} ({share_campaign:.0f}% of total)\n"
        f"- Flow Revenue: ${total_flow_revenue:,.2f} ({share_flow:.0f}% of total)\n"
        f"- Account Status: {status_counts.get('ahead',0)} ahead, {status_counts.get('on_track',0)} on track, {status_counts.get('behind',0)} behind, {status_counts.get('at_risk',0)} at risk\n\n"
        f"CLIENT BREAKDOWN:\n{breakdown}\n\n"
        "Provide exactly 4 company-wide insights and exactly 4 strategic action items.\n\n"
        "Format your response as:\n"
        "INSIGHTS:\n"
        "• [company insight 1]\n"
        "• [company insight 2]\n"
        "• [company insight 3]\n"
        "• [company insight 4]\n\n"
        "ACTIONS:\n"
        "• [strategic action 1]\n"
        "• [strategic action 2]\n"
        "• [strategic action 3]\n"
        "• [strategic action 4]"
    )
    if company_prompt_cfg:
        # Build variables similar to the template shown; pass precomputed breakdown
        comp_vars = {
            "client_count": len(all_metrics),
            "total_revenue": f"{total_revenue:,.2f}",
            "total_orders": f"{total_orders:,}",
            "total_campaign_revenue": f"{total_campaign_revenue:,.2f}",
            "total_flow_revenue": f"{total_flow_revenue:,.2f}",
            "share_campaign": f"{(total_campaign_revenue/total_revenue*100) if total_revenue>0 else 0:.0f}",
            "share_flow": f"{(total_flow_revenue/total_revenue*100) if total_revenue>0 else 0:.0f}",
            "status_ahead": status_counts.get("ahead",0),
            "status_on_track": status_counts.get("on_track",0),
            "status_behind": status_counts.get("behind",0),
            "status_at_risk": status_counts.get("at_risk",0),
            "client_breakdown": breakdown,
        }
        exec_res = await ai.execute_prompt(
            prompt_id=company_prompt_cfg["id"],
            variables=comp_vars,
            override_provider=company_prompt_cfg.get("model_provider"),
            override_model=company_prompt_cfg.get("model_name"),
        )
        company_response = exec_res.get("response") if exec_res.get("success") else ""
        company_prompt = exec_res.get("rendered_prompt", company_prompt)
    else:
        company_response = await _run_prompt_text(ai, company_prompt)

    # Send to Slack (summary + top clients)
    try:
        # Build a concise Slack message
        top_clients = sorted([m for m in all_metrics if not m.get("error")], key=lambda x: x["weekly_revenue"], reverse=True)[:5]
        fields = [
            {"type": "mrkdwn", "text": f"*Total Revenue*\n${total_revenue:,.2f}"},
            {"type": "mrkdwn", "text": f"*Orders*\n{total_orders:,}"},
            {"type": "mrkdwn", "text": f"*Campaign Rev*\n${total_campaign_revenue:,.2f}"},
            {"type": "mrkdwn", "text": f"*Flow Rev*\n${total_flow_revenue:,.2f}"},
        ]
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📈 Weekly Klaviyo Performance (Company)"}},
            {"type": "section", "fields": fields},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*🤖 AI Summary*\n{company_response}"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": "*🏆 Top Clients*"}},
        ]
        for m in top_clients:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"• *{m['account_name']}* — ${m['weekly_revenue']:,.0f}"}})

        webhook = await slack._get_slack_webhook_url()
        if webhook and not preview:
            await slack._send_to_slack(webhook, {"text": "Weekly Klaviyo Performance", "blocks": blocks})
    except Exception as e:
        logger.warning(f"Failed to send Slack summary: {e}")

    return {
        "success": True,
        "summary": {
            "clients": len(all_metrics),
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_campaign_revenue": total_campaign_revenue,
            "total_flow_revenue": total_flow_revenue,
            "status_counts": status_counts,
        },
        "company_prompt": company_prompt,
        "company_response": company_response,
        "client_insights": client_insights,
    }
