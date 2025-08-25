# app/api/reports.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from dataclasses import dataclass

from google.cloud import firestore
from app.deps.firestore import get_db
from app.services.secrets import SecretManagerService
from app.deps.secrets import get_secret_manager_service
from app.services.slack_alerts import SlackAlertService
from app.services.performance_monitor import performance_monitor
from app.services.agent_service import get_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

@dataclass
class ClientRevenue:
    """Data class for client revenue information"""
    client_id: str
    client_name: str
    last_7_days_revenue: float
    has_api_key: bool
    error_message: Optional[str] = None

@dataclass
class WeeklyReportData:
    """Data class for weekly report compilation"""
    total_revenue: float
    client_count: int
    clients_with_revenue: int
    clients_without_api_keys: int
    client_details: List[ClientRevenue]
    generated_at: str

@router.get("/")
def list_reports():
    # Return something valid so the UI stops 404'ing; fill in later.
    return {
        "available": [
            {"id": "monthly", "name": "Monthly Summary"},
            {"id": "weekly", "name": "Weekly Snapshot"},
        ]
    }

@router.post("/weekly/generate")
async def generate_weekly_report(
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """
    Generate weekly revenue report for all clients with valid Klaviyo API keys.
    Calls the Revenue API service and compiles data into a Slack report.
    """
    try:
        logger.info("Starting weekly report generation...")
        
        # Get all clients from Firestore
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        
        if not clients:
            logger.warning("No clients found in Firestore")
            return JSONResponse(
                status_code=404,
                content={"error": "No clients found in database"}
            )
        
        logger.info(f"Found {len(clients)} clients in database")
        
        # Check Revenue API availability
        revenue_api_base = "http://localhost:9090"
        if not await _check_revenue_api_health(revenue_api_base):
            raise HTTPException(
                status_code=503,
                detail="Revenue API service is not available at localhost:9090"
            )
        
        # Process each client to get revenue data
        client_revenues = []
        total_revenue = 0.0
        clients_with_revenue = 0
        clients_without_api_keys = 0
        
        logger.info("Processing clients for revenue data...")
        
        for i, client_doc in enumerate(clients, 1):
            client_id = client_doc.id
            client_data = client_doc.to_dict() or {}
            client_name = client_data.get("name", client_data.get("client_name", f"Client {client_id}"))
            client_slug = client_data.get("client_slug")  # Get the slug if available
            
            logger.info(f"Processing client {i}/{len(clients)}: {client_name} (id: {client_id}, slug: {client_slug or 'none'})")
            
            try:
                # Get revenue for last 7 days (pass slug if available)
                revenue_result = await _get_client_revenue(
                    client_id, client_name, revenue_api_base, client_slug
                )
                
                client_revenues.append(revenue_result)
                
                if revenue_result.has_api_key and revenue_result.error_message is None:
                    total_revenue += revenue_result.last_7_days_revenue
                    clients_with_revenue += 1
                elif not revenue_result.has_api_key:
                    clients_without_api_keys += 1
                
                # Add delay between API calls to avoid rate limiting
                if i < len(clients):  # Don't delay after the last client
                    logger.debug("Waiting 1 second before next client...")
                    await asyncio.sleep(1.0)
                    
            except Exception as e:
                logger.error(f"Error processing client {client_id}: {e}")
                client_revenues.append(ClientRevenue(
                    client_id=client_id,
                    client_name=client_name,
                    last_7_days_revenue=0.0,
                    has_api_key=False,
                    error_message=str(e)
                ))
                clients_without_api_keys += 1
        
        # Compile report data
        report_data = WeeklyReportData(
            total_revenue=total_revenue,
            client_count=len(clients),
            clients_with_revenue=clients_with_revenue,
            clients_without_api_keys=clients_without_api_keys,
            client_details=client_revenues,
            generated_at=datetime.now().isoformat()
        )
        
        logger.info(f"Weekly report compiled: ${total_revenue:,.2f} total revenue from {clients_with_revenue} clients")
        
        # Send to Slack in background
        background_tasks.add_task(_send_weekly_report_to_slack, report_data, secret_manager)
        
        # Return success response
        return {
            "success": True,
            "message": "Weekly report generated successfully",
            "summary": {
                "total_revenue": total_revenue,
                "client_count": len(clients),
                "clients_with_revenue": clients_with_revenue,
                "clients_without_api_keys": clients_without_api_keys,
                "generated_at": report_data.generated_at
            },
            "client_details": [
                {
                    "client_id": cr.client_id,
                    "client_name": cr.client_name,
                    "revenue": cr.last_7_days_revenue,
                    "has_api_key": cr.has_api_key,
                    "error": cr.error_message
                }
                for cr in client_revenues
            ]
        }
        
    except Exception as e:
        logger.error(f"Weekly report generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate weekly report: {str(e)}"
        )

async def _check_revenue_api_health(revenue_api_base: str) -> bool:
    """Check if Revenue API service is available"""
    try:
        logger.debug(f"Checking Revenue API health at {revenue_api_base}...")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{revenue_api_base}/healthz")
            if response.status_code == 200:
                logger.debug("Revenue API is healthy and responding")
                return True
            else:
                logger.warning(f"Revenue API returned status {response.status_code}")
                return False
    except Exception as e:
        logger.warning(f"Revenue API health check failed: {e}")
        return False

async def _get_client_revenue(client_id: str, client_name: str, revenue_api_base: str, client_slug: Optional[str] = None) -> ClientRevenue:
    """Get last 7 days revenue for a specific client from Revenue API"""
    try:
        # Calculate date range for last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Format dates for API
        start_time = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_time = end_date.strftime("%Y-%m-%dT23:59:59Z")
        
        params = {
            "start": start_time,
            "end": end_time,
            "recompute": "true"
        }
        
        # Use slug if available, otherwise use client_id
        if client_slug:
            url = f"{revenue_api_base}/clients/{client_slug}/revenue/last7"
        else:
            url = f"{revenue_api_base}/clients/{client_id}/revenue/last7"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            # If using slug failed with 404, try with document ID instead
            if response.status_code == 404 and client_slug and client_slug != client_id:
                logger.debug(f"Slug {client_slug} not found, trying with document ID {client_id}")
                url = f"{revenue_api_base}/clients/{client_id}/revenue/last7"
                response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                total_revenue = float(data.get("total", 0))
                
                logger.debug(f"Revenue for {client_name}: ${total_revenue:.2f}")
                
                return ClientRevenue(
                    client_id=client_id,
                    client_name=client_name,
                    last_7_days_revenue=total_revenue,
                    has_api_key=True
                )
                
            elif response.status_code == 400 and "Unable to resolve Klaviyo API key" in response.text:
                # Client has no API key configured
                logger.info(f"Client {client_name} has no Klaviyo API key configured - skipping")
                return ClientRevenue(
                    client_id=client_id,
                    client_name=client_name,
                    last_7_days_revenue=0.0,
                    has_api_key=False,
                    error_message="No Klaviyo API key configured"
                )
                
            elif response.status_code == 404:
                # Client not found in Revenue API
                logger.warning(f"Client {client_name} not found in Revenue API (tried {client_slug or client_id})")
                return ClientRevenue(
                    client_id=client_id,
                    client_name=client_name,
                    last_7_days_revenue=0.0,
                    has_api_key=False,
                    error_message="Client not found"
                )
                
            else:
                logger.warning(f"Revenue API returned {response.status_code} for {client_name}: {response.text}")
                return ClientRevenue(
                    client_id=client_id,
                    client_name=client_name,
                    last_7_days_revenue=0.0,
                    has_api_key=False,
                    error_message=f"API error: {response.status_code}"
                )
                
    except Exception as e:
        logger.error(f"Failed to get revenue for client {client_name}: {e}")
        return ClientRevenue(
            client_id=client_id,
            client_name=client_name,
            last_7_days_revenue=0.0,
            has_api_key=False,
            error_message=str(e)
        )

async def _send_weekly_report_to_slack(report_data: WeeklyReportData, secret_manager: SecretManagerService):
    """Send the weekly report to Slack using SlackAlertService"""
    try:
        logger.info("Sending weekly report to Slack...")
        
        slack_service = SlackAlertService(secret_manager)
        
        # Create formatted message for weekly report
        message = _format_weekly_report_for_slack(report_data)
        
        # Send the report
        success = await slack_service.send_weekly_report(message)
        
        if success:
            logger.info("Weekly report sent to Slack successfully")
        else:
            logger.error("Failed to send weekly report to Slack")
            
    except Exception as e:
        logger.error(f"Error sending weekly report to Slack: {e}")

def _format_weekly_report_for_slack(report_data: WeeklyReportData) -> Dict[str, Any]:
    """Format the weekly report data into a rich Slack message"""
    
    # Calculate percentage with revenue
    revenue_percentage = (report_data.clients_with_revenue / report_data.client_count * 100) if report_data.client_count > 0 else 0
    
    # Format client details
    client_details_text = ""
    for client in sorted(report_data.client_details, key=lambda x: x.last_7_days_revenue, reverse=True):
        if client.has_api_key and client.error_message is None:
            status_emoji = "💰" if client.last_7_days_revenue > 0 else "⚪"
            client_details_text += f"{status_emoji} *{client.client_name}*: ${client.last_7_days_revenue:,.2f}\n"
        elif not client.has_api_key:
            client_details_text += f"🔑 *{client.client_name}*: No API key configured\n"
        else:
            client_details_text += f"❌ *{client.client_name}*: {client.error_message}\n"
    
    # Determine overall status emoji
    if revenue_percentage >= 80:
        status_emoji = "🚀"
        status_text = "Excellent"
    elif revenue_percentage >= 60:
        status_emoji = "✅"
        status_text = "Good"
    elif revenue_percentage >= 40:
        status_emoji = "⚠️"
        status_text = "Needs Attention"
    else:
        status_emoji = "🚨"
        status_text = "Critical"
    
    return {
        "text": f"{status_emoji} EmailPilot Weekly Revenue Report",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} EmailPilot Weekly Revenue Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Period:* Last 7 days ending {datetime.now().strftime('%Y-%m-%d')}\n*Status:* {status_text} - {report_data.clients_with_revenue}/{report_data.client_count} clients reporting revenue ({revenue_percentage:.0f}%)"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Revenue:*\n${report_data.total_revenue:,.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Reporting Clients:*\n{report_data.clients_with_revenue} of {report_data.client_count}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Missing API Keys:*\n{report_data.clients_without_api_keys} clients"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Average per Client:*\n${report_data.total_revenue / report_data.clients_with_revenue:,.2f}" if report_data.clients_with_revenue > 0 else "*Average per Client:*\n$0.00"
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
                    "text": f"*📊 Client Revenue Breakdown*\n{client_details_text}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Report generated at {report_data.generated_at} | Data source: Revenue API (localhost:9090)"
                    }
                ]
            }
        ]
    }


@router.post("/monthly/generate")
async def generate_monthly_reports(
    background_tasks: BackgroundTasks,
    client_id: Optional[str] = None,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service),
):
    """Generate monthly reports using Performance Monitor + AI agent prompting.

    - For each client (or the specified client), compile monthly metrics via PerformanceMonitor.
    - Then invoke the agent orchestrator to produce a narrative summary and actions.
    - Returns an aggregated summary with optional AI narrative.
    """
    try:
        logger.info("Starting monthly report generation%s...", f" for {client_id}" if client_id else " for all clients")

        # Build client list
        client_docs = []
        if client_id:
            doc = db.collection("clients").document(client_id).get()
            if not doc.exists:
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
            client_docs = [doc]
        else:
            client_docs = list(db.collection("clients").stream())

        if not client_docs:
            return JSONResponse(status_code=404, content={"error": "No clients found"})

        results: List[Dict[str, Any]] = []
        total_revenue = 0.0
        total_orders = 0
        processed_clients = 0

        # Generate per-client monthly metrics (also posts Slack via PerformanceMonitor if configured)
        for i, doc in enumerate(client_docs, 1):
            cid = doc.id
            data = doc.to_dict() or {}
            name = data.get("name", cid)
            try:
                report = await performance_monitor.generate_monthly_report(cid)
                results.append({
                    "client_id": cid,
                    "client_name": name,
                    "status": "success",
                    "metrics": {
                        "total_revenue": report.get("total_revenue", 0),
                        "total_orders": report.get("total_orders", 0),
                        "goal_achievement_percent": report.get("goal_achievement_percent"),
                    }
                })
                total_revenue += float(report.get("total_revenue", 0) or 0)
                total_orders += int(report.get("total_orders", 0) or 0)
                processed_clients += 1
            except Exception as e:
                logger.error(f"Monthly metrics failed for {name}: {e}")
                results.append({
                    "client_id": cid,
                    "client_name": name,
                    "status": "failed",
                    "error": str(e),
                })

        # AI Agent orchestration for an executive summary across clients
        ai_summary = None
        try:
            agent_service = get_agent_service()
            ai_payload = {
                "report_type": "monthly",
                "objective": "Create an executive summary of monthly email performance across clients with 3 insights and 3 actions.",
                "aggregated": {
                    "total_revenue": total_revenue,
                    "total_orders": total_orders,
                    "clients_processed": processed_clients,
                },
                "per_client": results,
            }
            agent_resp = await agent_service.invoke_agent(ai_payload)
            if isinstance(agent_resp, dict) and agent_resp.get("status") == "success":
                ai_summary = agent_resp.get("result")
        except Exception as e:
            logger.warning(f"AI agent monthly summary failed: {e}")

        return {
            "success": True,
            "message": "Monthly report generation completed",
            "summary": {
                "clients_processed": processed_clients,
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "generated_at": datetime.now().isoformat(),
            },
            "client_details": results,
            "ai_summary": ai_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Monthly report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
