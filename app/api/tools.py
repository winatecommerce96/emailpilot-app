"""
Tools API Router - Integration of external Klaviyo audit and management tools
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import subprocess
import os
import json
import logging
from datetime import datetime
from pathlib import Path

from app.services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Base directory for external tools
TOOLS_BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to klaviyo-audit-automation

class ToolsService:
    """Service for managing external Klaviyo tools"""
    
    def __init__(self):
        self.tools_dir = TOOLS_BASE_DIR
        
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available external tools"""
        tools = [
            {
                "id": "add_client",
                "name": "Add New Client",
                "description": "Interactive tool to add a new Klaviyo client with API key setup and goals configuration",
                "category": "Client Management",
                "script": "add_new_client.py",
                "icon": "user-plus",
                "color": "blue"
            },
            {
                "id": "enhanced_audit",
                "name": "Enhanced Klaviyo Audit",
                "description": "Comprehensive audit of campaigns, flows, segments, and metrics for a specific client",
                "category": "Auditing",
                "script": "enhanced_klaviyo_audit.py",
                "icon": "search",
                "color": "green"
            },
            {
                "id": "run_all_audits",
                "name": "Run All Client Audits",
                "description": "Execute audits for all configured clients automatically",
                "category": "Auditing",
                "script": "run_all_audits.sh",
                "icon": "play",
                "color": "purple"
            },
            {
                "id": "value_assessment",
                "name": "Value Assessment Audit",
                "description": "Analyze actual metric values and generate critical alerts for zero metrics",
                "category": "Monitoring",
                "script": "run_value_assessments.sh",
                "icon": "chart-bar",
                "color": "orange"
            },
            {
                "id": "monthly_report",
                "name": "Monthly Revenue Report",
                "description": "Generate comprehensive monthly revenue and performance reports",
                "category": "Reporting",
                "script": "run_monthly_report.sh",
                "icon": "document-text",
                "color": "indigo"
            },
            {
                "id": "debug_api_key",
                "name": "Debug API Key",
                "description": "Test and validate Klaviyo API key connectivity for a client",
                "category": "Debugging",
                "script": "debug_api_key.py",
                "icon": "key",
                "color": "yellow"
            },
            {
                "id": "cloud_sync",
                "name": "Cloud Sync Tool",
                "description": "Synchronize local client data with cloud services",
                "category": "Data Management",
                "script": "cloud_sync.py",
                "icon": "cloud-upload",
                "color": "cyan"
            }
        ]
        
        # Filter to only include tools that actually exist
        available_tools = []
        for tool in tools:
            script_path = self.tools_dir / tool["script"]
            if script_path.exists():
                available_tools.append(tool)
                
        return available_tools
    
    def run_tool(self, tool_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        tools = {tool["id"]: tool for tool in self.get_available_tools()}
        
        if tool_id not in tools:
            raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
        
        tool = tools[tool_id]
        script_path = self.tools_dir / tool["script"]
        
        try:
            # Change to tools directory for execution
            cwd = str(self.tools_dir)
            
            if script_path.suffix == ".py":
                # Python script
                cmd = ["python3", tool["script"]]
                if params:
                    # Add parameters as environment variables
                    env = os.environ.copy()
                    for key, value in params.items():
                        env[f"TOOL_{key.upper()}"] = str(value)
                else:
                    env = None
                    
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    env=env
                )
            else:
                # Shell script
                cmd = ["bash", tool["script"]]
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout for shell scripts
                )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode,
                "execution_time": datetime.now().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Tool execution timed out",
                "return_code": -1,
                "execution_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error running tool {tool_id}: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "execution_time": datetime.now().isoformat()
            }

# Initialize service
tools_service = ToolsService()

@router.get("/")
async def get_tools(
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """Get list of available external tools"""
    try:
        tools = tools_service.get_available_tools()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "tools": tools,
                "total_count": len(tools)
            }
        )
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tools")

@router.post("/run/{tool_id}")
async def run_tool(
    tool_id: str,
    background_tasks: BackgroundTasks,
    params: Dict[str, Any] = None,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """Execute a specific tool"""
    try:
        logger.info(f"Running tool {tool_id} for user {current_user.get('email')}")
        
        # For long-running tools, we might want to run them in background
        if tool_id in ["run_all_audits", "monthly_report"]:
            # Run in background for long operations
            background_tasks.add_task(tools_service.run_tool, tool_id, params or {})
            return JSONResponse(
                status_code=202,
                content={
                    "success": True,
                    "message": f"Tool {tool_id} started in background",
                    "background": True
                }
            )
        else:
            # Run synchronously for quick tools
            result = tools_service.run_tool(tool_id, params or {})
            return JSONResponse(
                status_code=200 if result["success"] else 400,
                content=result
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running tool {tool_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run tool: {str(e)}")

@router.get("/logs/{tool_id}")
async def get_tool_logs(
    tool_id: str,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """Get execution logs for a specific tool"""
    try:
        # Check if logs directory exists
        logs_dir = TOOLS_BASE_DIR / "logs"
        log_file = logs_dir / f"{tool_id}.log"
        
        if not log_file.exists():
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No logs found for this tool"
                }
            )
        
        # Read recent logs (last 1000 lines)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "logs": "".join(recent_lines),
                "total_lines": len(lines),
                "showing_lines": len(recent_lines)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting logs for {tool_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tool logs")

@router.get("/status")
async def get_tools_status(
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """Get status of tools system"""
    try:
        tools = tools_service.get_available_tools()
        
        # Check if tools directory is accessible
        tools_accessible = TOOLS_BASE_DIR.exists() and TOOLS_BASE_DIR.is_dir()
        
        # Count tools by category
        categories = {}
        for tool in tools:
            category = tool["category"]
            categories[category] = categories.get(category, 0) + 1
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "tools_directory": str(TOOLS_BASE_DIR),
                "tools_accessible": tools_accessible,
                "total_tools": len(tools),
                "categories": categories,
                "last_check": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting tools status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tools status")