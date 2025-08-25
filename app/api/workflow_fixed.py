"""
Fixed Workflow API endpoints for LangGraph visual editor
Supports both singular (legacy) and plural (editor) routes
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import subprocess
import sys
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Add workflow tools to path
sys.path.append(str(Path(__file__).parent.parent.parent / "workflow" / "tools"))

try:
    from inspect_agents import AgentInspector
except ImportError:
    AgentInspector = None

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Storage paths
WORKFLOW_DIR = Path(__file__).parent.parent.parent / "workflow"
SCHEMAS_DIR = WORKFLOW_DIR / "schemas"
SCHEMAS_DIR.mkdir(exist_ok=True)


# ============================================================================
# PLURAL ENDPOINTS (for editor compatibility)
# ============================================================================

@router.get("/schemas")
async def list_schemas() -> List[Dict[str, Any]]:
    """List all saved workflow schemas (plural endpoint for editor)"""
    schemas = []
    
    # Always include default
    schemas.append({
        "id": "default",
        "name": "emailpilot_calendar",
        "version": "2.0.0",
        "description": "Email/SMS calendar builder with validation and human approval gate"
    })
    
    # Add saved schemas
    for schema_file in SCHEMAS_DIR.glob("*.json"):
        try:
            with open(schema_file) as f:
                schema = json.load(f)
                schemas.append({
                    "id": schema_file.stem,
                    "name": schema.get("name", schema_file.stem),
                    "description": schema.get("metadata", {}).get("description", ""),
                    "version": schema.get("metadata", {}).get("version", "1.0.0")
                })
        except Exception as e:
            print(f"Error reading schema {schema_file}: {e}")
    
    return schemas


@router.get("/schemas/{schema_id}")
async def get_schema(schema_id: str) -> Dict[str, Any]:
    """Get a specific workflow schema (plural endpoint for editor)"""
    schema_file = None
    
    if schema_id == "default":
        schema_file = WORKFLOW_DIR / "workflow.json"
    else:
        schema_file = SCHEMAS_DIR / f"{schema_id}.json"
    
    if not schema_file or not schema_file.exists():
        raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
    
    try:
        with open(schema_file) as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading schema: {e}")


@router.post("/schemas/{schema_id}")
async def save_schema(
    schema_id: str,
    schema: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """Save/update a workflow schema (plural endpoint for editor)"""
    try:
        # Determine save location
        if schema_id == "default":
            schema_file = WORKFLOW_DIR / "workflow.json"
        else:
            schema_file = SCHEMAS_DIR / f"{schema_id}.json"
        
        # Add metadata
        if "metadata" not in schema:
            schema["metadata"] = {}
        schema["metadata"]["saved_at"] = datetime.now().isoformat()
        schema["metadata"]["schema_id"] = schema_id
        
        # Save schema
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)
        
        return {
            "ok": True,
            "success": True,
            "schema_id": schema_id,
            "path": str(schema_file.relative_to(Path(__file__).parent.parent.parent))
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save schema: {e}")


@router.post("/schemas/{schema_id}/compile")
async def compile_schema(schema_id: str) -> Dict[str, Any]:
    """Compile a workflow schema to LangGraph runtime code"""
    try:
        # Ensure schema exists
        if schema_id == "default":
            schema_file = WORKFLOW_DIR / "workflow.json"
        else:
            schema_file = SCHEMAS_DIR / f"{schema_id}.json"
            # Copy to workflow.json for codegen
            if schema_file.exists():
                import shutil
                shutil.copy(schema_file, WORKFLOW_DIR / "workflow.json")
        
        # Run codegen
        result = subprocess.run(
            [sys.executable, str(WORKFLOW_DIR / "tools" / "codegen.py")],
            capture_output=True,
            text=True,
            cwd=str(WORKFLOW_DIR)
        )
        
        if result.returncode != 0:
            raise ValueError(f"Codegen failed: {result.stderr}")
        
        # Read generated code
        runtime_file = WORKFLOW_DIR / "runtime" / "graph_compiled.py"
        compiled_code = None
        
        if runtime_file.exists():
            with open(runtime_file) as f:
                compiled_code = f.read()
        
        return {
            "success": True,
            "schema_id": schema_id,
            "output": result.stdout,
            "compiled_code": compiled_code
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {e}")


@router.post("/schemas/{schema_id}/run")
async def run_workflow(
    schema_id: str,
    inputs: Dict[str, Any] = Body({})
) -> Dict[str, Any]:
    """Run a compiled workflow (stub for now)"""
    try:
        # First compile
        compile_result = await compile_schema(schema_id)
        
        if not compile_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to compile workflow")
        
        # Create run instance
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Store run state (in production, use database)
        if not hasattr(run_workflow, '_runs'):
            run_workflow._runs = {}
        
        run_workflow._runs[run_id] = {
            "run_id": run_id,
            "schema_id": schema_id,
            "status": "running",
            "inputs": inputs,
            "current_node": "ingest",
            "pending_approval": False,
            "created_at": datetime.now().isoformat(),
            "message": "Workflow execution started"
        }
        
        return run_workflow._runs[run_id]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")


# ============================================================================
# AGENT MANAGEMENT
# ============================================================================

@router.post("/agents/{agent_id}")
async def save_agent(
    agent_id: str,
    agent_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Save or update an agent (stub for UI)
    In production, this would write to the actual agent files
    """
    try:
        # Store in memory for now (in production, write to files)
        if not hasattr(save_agent, '_agents'):
            save_agent._agents = {}
        
        save_agent._agents[agent_id] = agent_data
        
        return {
            "success": True,
            "agent_id": agent_id,
            "message": "Agent saved successfully (in memory)"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save agent: {e}")


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    """
    Get a specific agent's details
    """
    if hasattr(save_agent, '_agents') and agent_id in save_agent._agents:
        return save_agent._agents[agent_id]
    
    # Try to find in available nodes
    try:
        inspector = AgentInspector()
        catalog = inspector.export_to_workflow_schema()
        
        for node in catalog.get('available_nodes', []):
            if node['id'] == agent_id:
                return node
        
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {e}")


# ============================================================================
# AGENT DISCOVERY
# ============================================================================

@router.get("/agents")
async def discover_agents(
    format: str = Query(None, description="Output format: catalog or workflow")
) -> Dict[str, Any]:
    """Discover all available agents and tools in the codebase"""
    try:
        if not AgentInspector:
            # Return mock data if inspector not available
            return {
                "available_nodes": [
                    {
                        "id": "calendar-planner",
                        "type": "agent",
                        "impl": "agents.calendar_planner",
                        "description": "Calendar planning agent"
                    },
                    {
                        "id": "klaviyo-fetch",
                        "type": "tool",
                        "impl": "tools.klaviyo_fetch",
                        "description": "Fetch Klaviyo data"
                    }
                ],
                "metadata": {
                    "total_agents": 1,
                    "total_tools": 1
                }
            }
        
        inspector = AgentInspector()
        
        if format == "workflow":
            return inspector.export_to_workflow_schema()
        else:
            return inspector.generate_catalog()
            
    except Exception as e:
        # Return empty but valid response on error
        print(f"Agent discovery error: {e}")
        return {
            "available_nodes": [],
            "metadata": {
                "total_agents": 0,
                "total_tools": 0,
                "error": str(e)
            }
        }


# ============================================================================
# VALIDATION & EXPORT
# ============================================================================

@router.post("/schemas/{schema_id}/validate")
async def validate_schema(schema_id: str) -> Dict[str, Any]:
    """Validate a workflow schema"""
    try:
        schema = await get_schema(schema_id)
        
        errors = []
        warnings = []
        
        # Basic validation
        required = ["name", "state", "nodes", "edges", "checkpointer"]
        for field in required:
            if field not in schema:
                errors.append(f"Missing required field: {field}")
        
        # Validate node references
        if "nodes" in schema and "edges" in schema:
            node_ids = {node["id"] for node in schema["nodes"]}
            
            for edge in schema["edges"]:
                if edge.get("from") not in node_ids:
                    errors.append(f"Edge references unknown source: {edge.get('from')}")
                if edge.get("to") not in node_ids:
                    errors.append(f"Edge references unknown target: {edge.get('to')}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "schema_id": schema_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "schema_id": schema_id
        }


@router.get("/export/{schema_id}/mermaid")
async def export_mermaid(schema_id: str) -> str:
    """Export workflow as Mermaid diagram"""
    schema = await get_schema(schema_id)
    
    mermaid = ["graph TD"]
    
    # Add nodes
    for node in schema.get("nodes", []):
        node_id = node["id"]
        node_type = node.get("type", "unknown")
        
        if node_type == "agent":
            mermaid.append(f'    {node_id}["{node_id}<br/>🤖 Agent"]')
        elif node_type == "human_gate":
            mermaid.append(f'    {node_id}{{"🧑 {node_id}"}}"')
        elif node_type == "tool":
            mermaid.append(f'    {node_id}[["🔧 {node_id}"]]')
        else:
            mermaid.append(f'    {node_id}["{node_id}"]')
    
    # Add edges
    for edge in schema.get("edges", []):
        from_node = edge["from"]
        to_node = edge["to"]
        
        if "condition" in edge:
            condition = edge["condition"].replace('"', "'")
            # Simplify condition for display
            if "valid" in condition and "False" in condition:
                label = "invalid"
            elif "valid" in condition:
                label = "valid"
            else:
                label = condition[:20] + "..." if len(condition) > 20 else condition
            mermaid.append(f'    {from_node} -->|"{label}"| {to_node}')
        else:
            mermaid.append(f'    {from_node} --> {to_node}')
    
    return "\n".join(mermaid)


# ============================================================================
# LEGACY SINGULAR ENDPOINTS (backward compatibility)
# ============================================================================

@router.get("/schema")
async def get_schema_singular(name: str = Query("workflow")) -> Dict[str, Any]:
    """Get workflow schema (singular - legacy)"""
    return await get_schema("default" if name == "workflow" else name)


@router.post("/schema")
async def save_schema_singular(
    schema: Dict[str, Any] = Body(...),
    validate: bool = Query(True)
) -> Dict[str, Any]:
    """Save workflow schema (singular - legacy)"""
    schema_id = schema.get("name", "default")
    result = await save_schema(schema_id, schema)
    return result


# ============================================================================
# HUMAN GATE VISIBILITY APIs
# ============================================================================

@router.get("/runs")
async def list_runs() -> List[Dict[str, Any]]:
    """
    List all workflow runs
    """
    if not hasattr(run_workflow, '_runs'):
        return []
    
    return list(run_workflow._runs.values())


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str) -> Dict[str, Any]:
    """
    Get status of a specific run
    """
    if not hasattr(run_workflow, '_runs') or run_id not in run_workflow._runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    
    return run_workflow._runs[run_id]


@router.get("/runs/{run_id}/pending-approvals")
async def get_pending_approvals(run_id: str) -> Dict[str, Any]:
    """
    Get pending human approvals for a run
    """
    if not hasattr(run_workflow, '_runs') or run_id not in run_workflow._runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    
    run_state = run_workflow._runs[run_id]
    
    if run_state.get('pending_approval'):
        return {
            "run_id": run_id,
            "pending": True,
            "node": run_state.get('current_node', 'unknown'),
            "data_preview": run_state.get('preview_data', {}),
            "awaiting_since": run_state.get('approval_requested_at', datetime.now().isoformat())
        }
    else:
        return {
            "run_id": run_id,
            "pending": False
        }


@router.post("/runs/{run_id}/approve")
async def approve_human_gate(run_id: str, approval: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Approve or reject a human gate
    
    Args:
        run_id: The workflow run ID
        approval: Dict with 'approved' (bool) and optional 'notes' (str)
    """
    if not hasattr(run_workflow, '_runs') or run_id not in run_workflow._runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    
    run_state = run_workflow._runs[run_id]
    
    if not run_state.get('pending_approval'):
        raise HTTPException(status_code=400, detail="No pending approval for this run")
    
    # Update run state
    run_state['pending_approval'] = False
    run_state['last_approval'] = {
        "approved": approval.get('approved', False),
        "notes": approval.get('notes', ''),
        "timestamp": datetime.now().isoformat()
    }
    
    if approval.get('approved'):
        run_state['status'] = 'resumed'
        run_state['current_node'] = 'publish'  # Move to next node
    else:
        run_state['status'] = 'rejected'
    
    return {
        "run_id": run_id,
        "status": run_state['status'],
        "approval": run_state['last_approval']
    }


@router.post("/runs/{run_id}/simulate-human-gate")
async def simulate_human_gate(run_id: str) -> Dict[str, Any]:
    """
    Simulate arriving at a human gate (for testing)
    """
    if not hasattr(run_workflow, '_runs'):
        run_workflow._runs = {}
    
    # Create or update run
    if run_id not in run_workflow._runs:
        run_workflow._runs[run_id] = {
            "run_id": run_id,
            "schema_id": "default",
            "status": "running",
            "created_at": datetime.now().isoformat()
        }
    
    run_state = run_workflow._runs[run_id]
    run_state['pending_approval'] = True
    run_state['current_node'] = 'review'
    run_state['approval_requested_at'] = datetime.now().isoformat()
    run_state['preview_data'] = {
        "candidates": [
            {"type": "email", "name": "Summer Sale", "date": "2025-06-01"},
            {"type": "sms", "name": "Flash Sale", "date": "2025-06-15"}
        ],
        "total_campaigns": 25,
        "projected_revenue": 150000
    }
    
    return {
        "run_id": run_id,
        "status": "awaiting_approval",
        "message": "Human gate simulation activated"
    }


@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: str) -> Dict[str, Any]:
    """
    Pause a running workflow
    """
    if not hasattr(run_workflow, '_runs') or run_id not in run_workflow._runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    
    run_state = run_workflow._runs[run_id]
    
    if run_state['status'] not in ['running', 'resumed']:
        raise HTTPException(status_code=400, detail=f"Cannot pause run in status '{run_state['status']}'")
    
    run_state['status'] = 'paused'
    run_state['paused_at'] = datetime.now().isoformat()
    
    return {
        "run_id": run_id,
        "status": "paused",
        "message": "Workflow paused successfully"
    }


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: str) -> Dict[str, Any]:
    """
    Resume a paused workflow
    """
    if not hasattr(run_workflow, '_runs') or run_id not in run_workflow._runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    
    run_state = run_workflow._runs[run_id]
    
    if run_state['status'] != 'paused':
        raise HTTPException(status_code=400, detail=f"Cannot resume run in status '{run_state['status']}'")
    
    run_state['status'] = 'resumed'
    run_state['resumed_at'] = datetime.now().isoformat()
    
    return {
        "run_id": run_id,
        "status": "resumed",
        "message": "Workflow resumed successfully"
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> Dict[str, Any]:
    """
    Cancel a workflow run
    """
    if not hasattr(run_workflow, '_runs') or run_id not in run_workflow._runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    
    run_state = run_workflow._runs[run_id]
    
    if run_state['status'] in ['completed', 'failed', 'cancelled']:
        raise HTTPException(status_code=400, detail=f"Cannot cancel run in status '{run_state['status']}'")
    
    run_state['status'] = 'cancelled'
    run_state['cancelled_at'] = datetime.now().isoformat()
    
    return {
        "run_id": run_id,
        "status": "cancelled",
        "message": "Workflow cancelled successfully"
    }