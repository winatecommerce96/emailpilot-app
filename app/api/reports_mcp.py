# app/api/reports_mcp.py
"""
MCP-based Reports API
Uses the Revenue API's MCP process for generating comprehensive weekly reports
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import asyncio
import httpx
import subprocess
import json
from datetime import datetime, timedelta
from dataclasses import dataclass

from google.cloud import firestore
from app.deps.firestore import get_db
from app.services.secrets import SecretManagerService
from app.deps.secrets import get_secret_manager_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/mcp", tags=["MCP Reports"])

@dataclass
class MCPWeeklyReport:
    """Data class for MCP-based weekly report"""
    total_revenue: float
    total_orders: int
    client_count: int
    clients_with_revenue: int
    top_clients: List[Dict[str, Any]]
    generated_at: str
    report_period: str

class MCPReportGenerator:
    """Generate reports using MCP process similar to weekly_performance_update.py"""
    
    def __init__(self):
        self.mcp_process = None
        
    async def start_klaviyo_mcp(self, api_key: str):
        """Start the Klaviyo MCP server for a specific client"""
        import os
        env = os.environ.copy()
        env["PRIVATE_API_KEY"] = api_key
        env["READ_ONLY"] = "true"
        
        self.mcp_process = subprocess.Popen(
            ["uvx", "klaviyo-mcp-server@latest"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Initialize MCP protocol
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "emailpilot-weekly-report",
                    "version": "1.0.0"
                }
            }
        }
        
        self.mcp_process.stdin.write(json.dumps(init_request) + "\n")
        self.mcp_process.stdin.flush()
        response = self.mcp_process.stdout.readline()
        
        # Send initialized notification
        initialized_request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        self.mcp_process.stdin.write(json.dumps(initialized_request) + "\n")
        self.mcp_process.stdin.flush()
        
    async def call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool and return the result"""
        if not self.mcp_process:
            raise RuntimeError("MCP process not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parameters or {}
            }
        }
        
        self.mcp_process.stdin.write(json.dumps(request) + "\n")
        self.mcp_process.stdin.flush()
        
        response_str = self.mcp_process.stdout.readline()
        response = json.loads(response_str)
        
        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")
        
        return response.get("result", {})
    
    async def get_client_revenue_mcp(self, api_key: str, client_name: str) -> Dict[str, Any]:
        """Get revenue data for a client using MCP process"""
        try:
            # Start MCP for this client
            await self.start_klaviyo_mcp(api_key)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Get campaign revenue
            campaign_result = await self.call_mcp_tool(
                "get_campaign_values_report",
                {
                    "conversion_metric_id": "$value",
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "statistics": ["revenue", "recipients", "conversions"]
                }
            )
            
            # Get flow revenue
            flow_result = await self.call_mcp_tool(
                "get_flow_values_report",
                {
                    "conversion_metric_id": "$value",
                    "from": start_date.strftime("%Y-%m-%d"),
                    "to": end_date.strftime("%Y-%m-%d"),
                    "statistics": ["revenue", "recipients", "conversions"]
                }
            )
            
            # Calculate totals
            campaign_revenue = float(campaign_result.get("total_revenue", 0))
            flow_revenue = float(flow_result.get("total_revenue", 0))
            total_revenue = campaign_revenue + flow_revenue
            
            campaign_orders = int(campaign_result.get("total_conversions", 0))
            flow_orders = int(flow_result.get("total_conversions", 0))
            total_orders = campaign_orders + flow_orders
            
            return {
                "client_name": client_name,
                "total_revenue": total_revenue,
                "campaign_revenue": campaign_revenue,
                "flow_revenue": flow_revenue,
                "total_orders": total_orders,
                "campaign_orders": campaign_orders,
                "flow_orders": flow_orders,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"MCP error for client {client_name}: {e}")
            return {
                "client_name": client_name,
                "total_revenue": 0,
                "campaign_revenue": 0,
                "flow_revenue": 0,
                "total_orders": 0,
                "campaign_orders": 0,
                "flow_orders": 0,
                "success": False,
                "error": str(e)
            }
        finally:
            # Stop MCP process
            if self.mcp_process:
                try:
                    self.mcp_process.terminate()
                except:
                    pass
                self.mcp_process = None

@router.post("/weekly/generate")
async def generate_weekly_report_mcp(
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
):
    """
    Generate weekly report using MCP process for all clients.
    This endpoint uses the same approach as weekly_performance_update.py
    but integrated into the EmailPilot API.
    """
    try:
        logger.info("Starting MCP-based weekly report generation...")
        
        # Get all clients from Firestore
        clients_ref = db.collection("clients")
        clients = list(clients_ref.stream())
        
        if not clients:
            logger.warning("No clients found in Firestore")
            return JSONResponse(
                status_code=404,
                content={"error": "No clients found in database"}
            )
        
        logger.info(f"Found {len(clients)} clients to process with MCP")
        
        # Process each client with MCP
        generator = MCPReportGenerator()
        client_results = []
        total_revenue = 0.0
        total_orders = 0
        clients_with_revenue = 0
        
        for client_doc in clients:
            client_id = client_doc.id
            client_data = client_doc.to_dict() or {}
            client_name = client_data.get("name", client_data.get("client_name", f"Client {client_id}"))
            
            # Check if client has API key
            has_key = client_data.get("has_klaviyo_key", False)
            if not has_key:
                logger.info(f"Skipping {client_name} - no Klaviyo API key")
                continue
                
            # Get API key from Secret Manager
            secret_name = client_data.get("klaviyo_api_key_secret")
            if not secret_name:
                logger.warning(f"Client {client_name} missing secret reference")
                continue
                
            try:
                api_key = secret_manager.get_secret(secret_name)
                if not api_key:
                    logger.warning(f"Could not retrieve API key for {client_name}")
                    continue
                    
                logger.info(f"Processing {client_name} with MCP...")
                
                # Get revenue data using MCP
                result = await generator.get_client_revenue_mcp(api_key, client_name)
                
                if result["success"]:
                    client_results.append(result)
                    total_revenue += result["total_revenue"]
                    total_orders += result["total_orders"]
                    if result["total_revenue"] > 0:
                        clients_with_revenue += 1
                    
                    logger.info(f"✅ {client_name}: ${result['total_revenue']:,.2f} ({result['total_orders']} orders)")
                else:
                    logger.error(f"❌ {client_name}: {result.get('error', 'Unknown error')}")
                    
                # Add delay between clients to avoid overwhelming the system
                await asyncio.sleep(2.0)
                
            except Exception as e:
                logger.error(f"Error processing client {client_name}: {e}")
                continue
        
        # Sort clients by revenue
        client_results.sort(key=lambda x: x["total_revenue"], reverse=True)
        top_clients = client_results[:5]  # Top 5 clients
        
        # Create report summary
        report = MCPWeeklyReport(
            total_revenue=total_revenue,
            total_orders=total_orders,
            client_count=len(client_results),
            clients_with_revenue=clients_with_revenue,
            top_clients=top_clients,
            generated_at=datetime.now().isoformat(),
            report_period=f"Last 7 days ending {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        logger.info(f"MCP Weekly report compiled: ${total_revenue:,.2f} from {clients_with_revenue} clients")
        
        # Send to Slack in background
        background_tasks.add_task(_send_mcp_report_to_slack, report, client_results, secret_manager)
        
        # Return success response
        return {
            "success": True,
            "message": "MCP-based weekly report generated successfully",
            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "client_count": len(client_results),
                "clients_with_revenue": clients_with_revenue,
                "top_clients": top_clients,
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

async def _send_mcp_report_to_slack(report: MCPWeeklyReport, client_results: List[Dict], secret_manager: SecretManagerService):
    """Send the MCP-generated weekly report to Slack"""
    try:
        logger.info("Sending MCP weekly report to Slack...")
        
        # Get Slack webhook URL from Secret Manager
        try:
            webhook_url = secret_manager.get_secret("slack-webhook-url")
        except:
            # Fallback to environment variable
            import os
            webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            
        if not webhook_url:
            logger.warning("No Slack webhook URL configured")
            return
        
        # Format the message
        client_details = ""
        for client in client_results:
            if client["total_revenue"] > 0:
                emoji = "💰" if client["total_revenue"] > 1000 else "💵"
                client_details += f"{emoji} *{client['client_name']}*: ${client['total_revenue']:,.2f} ({client['total_orders']} orders)\n"
                client_details += f"   • Campaigns: ${client['campaign_revenue']:,.2f} ({client['campaign_orders']} orders)\n"
                client_details += f"   • Flows: ${client['flow_revenue']:,.2f} ({client['flow_orders']} orders)\n\n"
        
        # Determine performance status
        avg_revenue = report.total_revenue / report.client_count if report.client_count > 0 else 0
        if avg_revenue > 5000:
            status_emoji = "🚀"
            status_text = "Excellent Performance"
        elif avg_revenue > 2000:
            status_emoji = "✅"
            status_text = "Good Performance"
        elif avg_revenue > 500:
            status_emoji = "📊"
            status_text = "Moderate Performance"
        else:
            status_emoji = "⚠️"
            status_text = "Needs Attention"
        
        # Create Slack message
        slack_message = {
            "text": f"{status_emoji} EmailPilot Weekly Revenue Report (MCP-Generated)",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} Weekly Revenue Report - MCP Process"
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
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Revenue:*\n${report.total_revenue:,.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Orders:*\n{report.total_orders:,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Active Clients:*\n{report.clients_with_revenue} of {report.client_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg per Client:*\n${avg_revenue:,.2f}"
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
                        "text": f"*📈 Top Performing Clients*\n\n{client_details[:1500]}"  # Limit to avoid Slack message size limits
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
                            "text": f"Generated via MCP Process at {report.generated_at} | EmailPilot Revenue Analytics"
                        }
                    ]
                }
            ]
        }
        
        # Send to Slack
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=slack_message)
            if response.status_code == 200:
                logger.info("MCP weekly report sent to Slack successfully")
            else:
                logger.error(f"Failed to send to Slack: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"Error sending MCP weekly report to Slack: {e}")