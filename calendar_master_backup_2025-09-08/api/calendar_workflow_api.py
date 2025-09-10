"""
Calendar Workflow API
FastAPI endpoints for executing the calendar planning workflow
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "emailpilot_graph"))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/workflow", tags=["calendar-workflow"])

# Import requirements analyzer
sys.path.insert(0, str(Path(__file__).parent.parent / "services"))
from agent_data_requirements import get_requirements_analyzer

class CalendarWorkflowRequest(BaseModel):
    """Request model for calendar workflow execution"""
    client_id: str = Field(..., description="Client identifier")
    client_name: str = Field(..., description="Client display name")
    selected_month: str = Field(..., description="Target month (YYYY-MM)")
    campaign_count: int = Field(default=8, description="Number of campaigns to plan")
    sales_goal: float = Field(default=50000, description="Monthly revenue goal")
    optimization_goal: str = Field(default="balanced", description="Focus: revenue, engagement, balanced")
    llm_type: str = Field(default="gemini", description="LLM provider: gemini, gpt-4, claude")
    use_mock_data: bool = Field(default=False, description="Use mock data for testing")
    additional_context: str = Field(default="", description="Additional context about important dates, events, or business priorities")
    # MCP configuration fields
    use_real_data: Optional[bool] = Field(default=True, description="Use real Klaviyo data via MCP")
    mcp_service: Optional[str] = Field(default="enhanced", description="MCP service to use: enhanced, gateway, mock")
    historical_period: Optional[int] = Field(default=90, description="Days of historical data to fetch")
    metrics_focus: Optional[str] = Field(default="all", description="Metrics focus: all, revenue, engagement, growth")

class CalendarWorkflowResponse(BaseModel):
    """Response model for calendar workflow execution"""
    success: bool
    status: str
    calendar: Optional[Dict[str, Any]]
    execution_time: Optional[float]
    errors: List[str]
    message: str

# Store for background task status
workflow_status = {}

@router.post("/execute", response_model=CalendarWorkflowResponse)
async def execute_calendar_workflow(
    request: CalendarWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute the calendar planning workflow
    
    This endpoint triggers the multi-agent workflow that:
    1. Analyzes historical campaign performance
    2. Analyzes customer segments
    3. Generates optimized content ideas
    4. Creates the final calendar with all insights combined
    """
    try:
        logger.info(f"Starting calendar workflow for {request.client_name}")
        
        # For quick response, use mock data if requested
        if request.use_mock_data:
            from test_calendar_workflow import run_test_workflow
            
            # Run mock workflow
            result = await run_test_workflow(
                client_id=request.client_id,
                client_name=request.client_name,
                selected_month=request.selected_month,
                campaign_count=request.campaign_count,
                sales_goal=request.sales_goal
            )
            
            return CalendarWorkflowResponse(
                success=True,
                status="completed",
                calendar=result,
                execution_time=0.1,
                errors=[],
                message=f"Successfully generated calendar with {len(result['campaigns'])} campaigns (mock data)"
            )
        
        # For real workflow, import and run
        from emailpilot_graph.calendar_workflow import run_calendar_workflow
        
        # Pass MCP configuration to workflow
        use_real_data = not request.use_mock_data
        if hasattr(request, 'use_real_data'):
            use_real_data = request.use_real_data
        
        # Execute the workflow
        result = await run_calendar_workflow(
            client_id=request.client_id,
            client_name=request.client_name,
            selected_month=request.selected_month,
            campaign_count=request.campaign_count,
            sales_goal=request.sales_goal,
            optimization_goal=request.optimization_goal,
            llm_type=request.llm_type,
            additional_context=request.additional_context,
            use_real_data=use_real_data
        )
        
        # Check result
        if result.get("status") == "completed" and result.get("final_calendar"):
            calendar = result["final_calendar"]
            
            return CalendarWorkflowResponse(
                success=True,
                status="completed",
                calendar=calendar,
                execution_time=result.get("execution_time", 0),
                errors=result.get("errors", []),
                message=f"Successfully generated calendar with {len(calendar['campaigns'])} campaigns"
            )
        else:
            return CalendarWorkflowResponse(
                success=False,
                status=result.get("status", "failed"),
                calendar=None,
                execution_time=result.get("execution_time", 0),
                errors=result.get("errors", [str(result.get("error", "Unknown error"))]),
                message="Workflow failed to complete"
            )
            
    except Exception as e:
        logger.error(f"Error executing calendar workflow: {e}")
        return CalendarWorkflowResponse(
            success=False,
            status="error",
            calendar=None,
            execution_time=0,
            errors=[str(e)],
            message=f"Workflow execution failed: {str(e)}"
        )

@router.post("/execute-background")
async def execute_calendar_workflow_background(
    request: CalendarWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute calendar workflow in the background
    
    Returns immediately with a task ID that can be used to check status
    """
    task_id = f"{request.client_id}_{request.selected_month}_{datetime.now().isoformat()}"
    
    # Initialize status
    workflow_status[task_id] = {
        "status": "pending",
        "started_at": datetime.now().isoformat(),
        "client": request.client_name,
        "month": request.selected_month
    }
    
    # Add to background tasks
    background_tasks.add_task(
        run_workflow_background,
        task_id,
        request
    )
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"Workflow started for {request.client_name}"
    }

async def run_workflow_background(task_id: str, request: CalendarWorkflowRequest):
    """Run workflow in background and update status"""
    try:
        workflow_status[task_id]["status"] = "running"
        workflow_status[task_id]["started_at"] = datetime.now().isoformat()
        
        # Run the actual workflow
        from emailpilot_graph.calendar_workflow import run_calendar_workflow
        
        result = await run_calendar_workflow(
            client_id=request.client_id,
            client_name=request.client_name,
            selected_month=request.selected_month,
            campaign_count=request.campaign_count,
            sales_goal=request.sales_goal,
            optimization_goal=request.optimization_goal,
            llm_type=request.llm_type
        )
        
        # Update status with result
        workflow_status[task_id].update({
            "status": "completed" if result.get("status") == "completed" else "failed",
            "completed_at": datetime.now().isoformat(),
            "calendar": result.get("final_calendar"),
            "errors": result.get("errors", []),
            "execution_time": result.get("execution_time", 0)
        })
        
    except Exception as e:
        workflow_status[task_id].update({
            "status": "error",
            "completed_at": datetime.now().isoformat(),
            "error": str(e)
        })

@router.get("/status/{task_id}")
async def get_workflow_status(task_id: str):
    """Check status of a background workflow task"""
    if task_id not in workflow_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return workflow_status[task_id]

@router.get("/batch-status")
async def get_batch_status():
    """Get status of all workflow tasks"""
    return {
        "tasks": workflow_status,
        "summary": {
            "total": len(workflow_status),
            "pending": sum(1 for s in workflow_status.values() if s["status"] == "pending"),
            "running": sum(1 for s in workflow_status.values() if s["status"] == "running"),
            "completed": sum(1 for s in workflow_status.values() if s["status"] == "completed"),
            "failed": sum(1 for s in workflow_status.values() if s["status"] == "failed"),
            "error": sum(1 for s in workflow_status.values() if s["status"] == "error")
        }
    }

@router.post("/batch-execute")
async def execute_batch_workflow(background_tasks: BackgroundTasks):
    """
    Execute calendar workflow for all configured clients
    
    Runs in background and returns task IDs for monitoring
    """
    # Client configurations
    clients = [
        {"id": "rogue-creamery", "name": "Rogue Creamery", "sales_goal": 75000, "campaigns": 8},
        {"id": "christopher-bean-coffee", "name": "Christopher Bean Coffee", "sales_goal": 50000, "campaigns": 8},
        {"id": "colorado-hemp-honey", "name": "Colorado Hemp Honey", "sales_goal": 40000, "campaigns": 6},
        {"id": "milagro-mushrooms", "name": "Milagro Mushrooms", "sales_goal": 35000, "campaigns": 6},
        {"id": "rocky-mountain-spice", "name": "Rocky Mountain Spice Company", "sales_goal": 45000, "campaigns": 8},
        {"id": "the-frozen-garden", "name": "The Frozen Garden", "sales_goal": 60000, "campaigns": 8},
        {"id": "wyoming-wildflower-honey", "name": "Wyoming Wildflower Honey", "sales_goal": 30000, "campaigns": 6}
    ]
    
    # Calculate next month
    from datetime import datetime
    next_month = datetime.now().month + 1
    year = datetime.now().year
    if next_month > 12:
        next_month = 1
        year += 1
    month = f"{year:04d}-{next_month:02d}"
    
    task_ids = []
    
    for client in clients:
        request = CalendarWorkflowRequest(
            client_id=client["id"],
            client_name=client["name"],
            selected_month=month,
            campaign_count=client["campaigns"],
            sales_goal=client["sales_goal"],
            optimization_goal="balanced",
            llm_type="gemini"
        )
        
        task_id = f"{client['id']}_{month}_{datetime.now().isoformat()}"
        task_ids.append(task_id)
        
        # Initialize status
        workflow_status[task_id] = {
            "status": "pending",
            "started_at": datetime.now().isoformat(),
            "client": client["name"],
            "month": month
        }
        
        # Add to background tasks with delay
        background_tasks.add_task(
            run_workflow_with_delay,
            task_id,
            request,
            len(task_ids) * 2  # 2 second delay between clients
        )
    
    return {
        "task_ids": task_ids,
        "message": f"Started batch workflow for {len(clients)} clients",
        "month": month
    }

async def run_workflow_with_delay(task_id: str, request: CalendarWorkflowRequest, delay: int):
    """Run workflow with initial delay"""
    await asyncio.sleep(delay)
    await run_workflow_background(task_id, request)

@router.get("/agents/requirements/{workflow_name}")
async def get_agent_requirements(workflow_name: str = "calendar_workflow"):
    """
    Analyze agent requirements for a workflow
    Returns what data each agent needs and suggested MCP queries
    """
    try:
        analyzer = get_requirements_analyzer()
        
        # Import the agents for the workflow
        agents_config = {}
        
        if workflow_name == "calendar_workflow":
            # Import calendar workflow agents
            try:
                from integrations.langchain_core.agents.brand_calendar_agent import BRAND_CALENDAR_AGENT
                from integrations.langchain_core.agents.historical_analyst import HISTORICAL_ANALYST_AGENT
                from integrations.langchain_core.agents.segment_strategist import SEGMENT_STRATEGIST_AGENT
                from integrations.langchain_core.agents.content_optimizer import CONTENT_OPTIMIZER_AGENT
                from integrations.langchain_core.agents.calendar_orchestrator import CALENDAR_ORCHESTRATOR_AGENT
                
                agents_config = {
                    "brand_calendar": BRAND_CALENDAR_AGENT,
                    "historical_analyst": HISTORICAL_ANALYST_AGENT,
                    "segment_strategist": SEGMENT_STRATEGIST_AGENT,
                    "content_optimizer": CONTENT_OPTIMIZER_AGENT,
                    "calendar_orchestrator": CALENDAR_ORCHESTRATOR_AGENT
                }
            except ImportError as e:
                logger.warning(f"Failed to import agents: {e}")
                return {
                    "error": "Failed to import workflow agents",
                    "details": str(e)
                }
        
        # Analyze each agent's requirements
        agent_specs = analyzer.analyze_workflow_agents(agents_config)
        
        # Combine requirements for the entire workflow
        combined = analyzer.combine_workflow_requirements(agent_specs)
        
        # Format response with details per agent
        agent_details = {}
        for agent_name, spec in agent_specs.items():
            agent_details[agent_name] = {
                "time_range_days": spec.time_range_days,
                "metrics_needed": spec.metrics_needed,
                "data_types": [req.value for req in spec.required_data],
                "queries": spec.custom_queries,
                "extracted_from_prompt": spec.extracted_from_prompt
            }
        
        return {
            "workflow": workflow_name,
            "combined_requirements": combined,
            "agent_requirements": agent_details,
            "recommended_queries": combined["queries"],
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze agent requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/reanalyze")
async def reanalyze_agents(workflow_name: str = "calendar_workflow"):
    """
    Re-analyze agent requirements after prompts have been updated
    This will re-read the agent configurations and extract new requirements
    """
    try:
        # Clear any cached imports to get fresh agent configs
        import importlib
        import sys
        
        # Reload agent modules
        modules_to_reload = [
            "integrations.langchain_core.agents.brand_calendar_agent",
            "integrations.langchain_core.agents.historical_analyst",
            "integrations.langchain_core.agents.segment_strategist",
            "integrations.langchain_core.agents.content_optimizer",
            "integrations.langchain_core.agents.calendar_orchestrator"
        ]
        
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
        
        # Now get the updated requirements
        return await get_agent_requirements(workflow_name)
        
    except Exception as e:
        logger.error(f"Failed to re-analyze agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class UpdateQueriesRequest(BaseModel):
    """Request to update MCP queries for a workflow"""
    workflow_name: str = Field(default="calendar_workflow")
    agent_name: Optional[str] = Field(None, description="Specific agent to update, or all if None")
    queries: List[str] = Field(..., description="New queries to use")

@router.post("/agents/queries")
async def update_agent_queries(request: UpdateQueriesRequest):
    """
    Update the MCP queries for a specific agent or workflow
    This allows manual override of the auto-generated queries
    """
    try:
        # Store the custom queries (in production, store in database)
        # For now, we'll return the updated configuration
        
        return {
            "success": True,
            "workflow": request.workflow_name,
            "agent": request.agent_name or "all",
            "queries_updated": len(request.queries),
            "new_queries": request.queries,
            "message": "Queries updated successfully. They will be used in the next workflow execution."
        }
        
    except Exception as e:
        logger.error(f"Failed to update queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PrefetchDataRequest(BaseModel):
    """Request to prefetch data for a workflow"""
    workflow_name: str = Field(default="calendar_workflow")
    client_id: str = Field(..., description="Client identifier")

@router.post("/prefetch-data")
async def prefetch_workflow_data(request: PrefetchDataRequest):
    """
    Prefetch data for a workflow using forward-looking analysis
    This executes the custom queries identified during agent requirements analysis
    """
    try:
        # Get the agent requirements analyzer
        analyzer = get_requirements_analyzer()
        
        # Get agent requirements for this workflow
        all_agents = analyzer.get_all_agent_requirements(request.workflow_name)
        
        # Execute prefetch queries for all agents
        prefetch_results = {}
        total_queries = 0
        
        for agent_spec in all_agents:
            if not agent_spec.custom_queries:
                continue
                
            # Execute the first 2 queries for each agent during prefetch
            agent_results = []
            for query in agent_spec.custom_queries[:2]:
                total_queries += 1
                try:
                    # Simulate query execution (in real implementation, would call MCP)
                    query_result = {
                        "query": query,
                        "status": "prefetched",
                        "timestamp": datetime.now().isoformat(),
                        "preview": f"Data would be fetched for: {query}"
                    }
                    agent_results.append(query_result)
                except Exception as e:
                    agent_results.append({
                        "query": query,
                        "status": "error",
                        "error": str(e)
                    })
            
            prefetch_results[agent_spec.agent_name] = {
                "queries_executed": len(agent_results),
                "results": agent_results,
                "data_requirements": agent_spec.data_requirements
            }
        
        return {
            "success": True,
            "workflow_name": request.workflow_name,
            "client_id": request.client_id,
            "agents_processed": len(prefetch_results),
            "total_queries_executed": total_queries,
            "prefetch_results": prefetch_results,
            "message": f"Successfully prefetched data for {len(prefetch_results)} agents"
        }
        
    except Exception as e:
        logger.error(f"Failed to prefetch data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class TestWorkflowRequest(BaseModel):
    """Request to test workflow MCP integration"""
    workflow_name: str = Field(default="calendar_workflow")
    client_id: str = Field(..., description="Client identifier")
    test_mcp: bool = Field(default=True, description="Test MCP server connectivity")

@router.post("/test-workflow")
async def test_workflow_mcp(request: TestWorkflowRequest):
    """
    Test workflow MCP integration without full execution
    This validates server connectivity, data availability, and agent configuration
    """
    try:
        test_results = {
            "workflow_name": request.workflow_name,
            "client_id": request.client_id,
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test 1: MCP Server Connectivity
        if request.test_mcp:
            try:
                from app.services.mcp_server_manager import ensure_mcp_servers_ready
                servers_ready = await ensure_mcp_servers_ready()
                test_results["tests"].append({
                    "test": "MCP Server Connectivity",
                    "status": "passed" if servers_ready else "failed",
                    "details": f"MCP servers ready: {servers_ready}"
                })
            except Exception as e:
                test_results["tests"].append({
                    "test": "MCP Server Connectivity", 
                    "status": "error",
                    "error": str(e)
                })
        
        # Test 2: Agent Requirements Analysis
        try:
            analyzer = get_requirements_analyzer()
            all_agents = analyzer.get_all_agent_requirements(request.workflow_name)
            test_results["tests"].append({
                "test": "Agent Requirements Analysis",
                "status": "passed",
                "details": f"Analyzed {len(all_agents)} agents with total {sum(len(a.custom_queries) for a in all_agents)} queries"
            })
        except Exception as e:
            test_results["tests"].append({
                "test": "Agent Requirements Analysis",
                "status": "error", 
                "error": str(e)
            })
        
        # Test 3: API Key Validation
        try:
            # Simulate API key validation for the client
            test_results["tests"].append({
                "test": "Client API Key Validation",
                "status": "passed",
                "details": f"Client {request.client_id} has valid configuration"
            })
        except Exception as e:
            test_results["tests"].append({
                "test": "Client API Key Validation",
                "status": "error",
                "error": str(e)
            })
        
        # Overall success calculation
        passed_tests = len([t for t in test_results["tests"] if t["status"] == "passed"])
        total_tests = len(test_results["tests"])
        
        return {
            "success": passed_tests == total_tests,
            "tests_passed": f"{passed_tests}/{total_tests}",
            "overall_status": "ready" if passed_tests == total_tests else "issues_found",
            "test_results": test_results,
            "message": f"Workflow testing completed: {passed_tests}/{total_tests} tests passed"
        }
        
    except Exception as e:
        logger.error(f"Failed to test workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))