"""
Workflow API endpoints for LangGraph visual editor
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import subprocess
import sys
import uuid
from datetime import datetime

# Add workflow tools to path
sys.path.append(str(Path(__file__).parent.parent.parent / "workflow" / "tools"))

from inspect_agents import AgentInspector

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Storage for workflow schemas
WORKFLOW_DIR = Path(__file__).parent.parent.parent / "workflow"
SCHEMAS_DIR = WORKFLOW_DIR / "schemas"
SCHEMAS_DIR.mkdir(exist_ok=True)


@router.get("/agents")
async def discover_agents(
    format: str = Query("workflow", description="Output format: catalog or workflow")
) -> Dict[str, Any]:
    """
    Discover all available agents and tools in the codebase
    """
    try:
        inspector = AgentInspector()
        
        if format == "workflow":
            return inspector.export_to_workflow_schema()
        else:
            return inspector.generate_catalog()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent discovery failed: {e}")


@router.get("/schemas")
async def list_schemas() -> List[Dict[str, Any]]:
    """
    List all saved workflow schemas
    """
    schemas = []
    
    for schema_file in SCHEMAS_DIR.glob("*.json"):
        try:
            with open(schema_file) as f:
                schema = json.load(f)
                schemas.append({
                    "id": schema_file.stem,
                    "name": schema.get("name", schema_file.stem),
                    "description": schema.get("metadata", {}).get("description", ""),
                    "version": schema.get("metadata", {}).get("version", "0.0.0"),
                    "created": datetime.fromtimestamp(schema_file.stat().st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(schema_file.stat().st_mtime).isoformat()
                })
        except Exception as e:
            print(f"Error reading schema {schema_file}: {e}")
    
    return schemas


@router.get("/schemas/{schema_id}")
async def get_schema(schema_id: str) -> Dict[str, Any]:
    """
    Get a specific workflow schema
    """
    schema_file = SCHEMAS_DIR / f"{schema_id}.json"
    
    if not schema_file.exists():
        # Try the main workflow.json
        if schema_id == "default":
            schema_file = WORKFLOW_DIR / "workflow.json"
        else:
            raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
    
    try:
        with open(schema_file) as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading schema: {e}")


@router.post("/schemas")
async def save_schema(
    schema: Dict[str, Any] = Body(...),
    schema_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a workflow schema
    """
    if not schema_id:
        schema_id = schema.get("name", str(uuid.uuid4()))
    
    # Clean the ID to be filesystem-safe
    schema_id = "".join(c for c in schema_id if c.isalnum() or c in "-_")
    
    schema_file = SCHEMAS_DIR / f"{schema_id}.json"
    
    try:
        # Validate schema has required fields
        required = ["name", "state", "nodes", "edges", "checkpointer"]
        for field in required:
            if field not in schema:
                raise ValueError(f"Missing required field: {field}")
        
        # Add metadata if not present
        if "metadata" not in schema:
            schema["metadata"] = {}
        
        schema["metadata"]["saved_at"] = datetime.now().isoformat()
        schema["metadata"]["schema_id"] = schema_id
        
        # Save schema
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)
        
        return {
            "success": True,
            "schema_id": schema_id,
            "path": str(schema_file.relative_to(Path(__file__).parent.parent.parent))
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save schema: {e}")


@router.post("/schemas/{schema_id}/compile")
async def compile_schema(schema_id: str) -> Dict[str, Any]:
    """
    Compile a workflow schema to LangGraph runtime code
    """
    # Get the schema
    schema_file = SCHEMAS_DIR / f"{schema_id}.json"
    
    if not schema_file.exists():
        if schema_id == "default":
            schema_file = WORKFLOW_DIR / "workflow.json"
        else:
            raise HTTPException(status_code=404, detail=f"Schema {schema_id} not found")
    
    try:
        # Run codegen
        result = subprocess.run(
            [sys.executable, str(WORKFLOW_DIR / "tools" / "codegen.py")],
            capture_output=True,
            text=True,
            cwd=str(WORKFLOW_DIR)
        )
        
        if result.returncode != 0:
            raise ValueError(f"Codegen failed: {result.stderr}")
        
        # Read the generated code
        runtime_file = WORKFLOW_DIR / "runtime" / "graph_compiled.py"
        
        if runtime_file.exists():
            with open(runtime_file) as f:
                compiled_code = f.read()
        else:
            compiled_code = None
        
        return {
            "success": True,
            "schema_id": schema_id,
            "output": result.stdout,
            "compiled_code": compiled_code,
            "runtime_path": str(runtime_file.relative_to(Path(__file__).parent.parent.parent)) if runtime_file.exists() else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {e}")


@router.post("/schemas/{schema_id}/run")
async def run_workflow(
    schema_id: str,
    inputs: Dict[str, Any] = Body({})
) -> Dict[str, Any]:
    """
    Run a compiled workflow
    """
    # First compile the schema
    compile_result = await compile_schema(schema_id)
    
    if not compile_result["success"]:
        raise HTTPException(status_code=500, detail="Failed to compile workflow")
    
    try:
        # Import the compiled graph
        import importlib.util
        runtime_path = WORKFLOW_DIR / "runtime" / "graph_compiled.py"
        
        spec = importlib.util.spec_from_file_location("graph_compiled", runtime_path)
        if not spec or not spec.loader:
            raise ValueError("Could not load compiled graph")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the compile function
        if not hasattr(module, 'compile_graph'):
            raise ValueError("Compiled graph missing compile_graph function")
        
        # Compile and run the graph
        app = module.compile_graph()
        
        # Create initial state
        initial_state = {
            "inputs": inputs,
            **inputs  # Also spread inputs at top level
        }
        
        # Run the graph
        result = app.invoke(initial_state)
        
        return {
            "success": True,
            "schema_id": schema_id,
            "result": result,
            "execution_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}")


@router.post("/schemas/{schema_id}/validate")
async def validate_schema(schema_id: str) -> Dict[str, Any]:
    """
    Validate a workflow schema
    """
    try:
        schema = await get_schema(schema_id)
        
        errors = []
        warnings = []
        
        # Check required fields
        required = ["name", "state", "nodes", "edges", "checkpointer"]
        for field in required:
            if field not in schema:
                errors.append(f"Missing required field: {field}")
        
        # Validate node references in edges
        if "nodes" in schema and "edges" in schema:
            node_ids = {node["id"] for node in schema["nodes"]}
            
            for edge in schema["edges"]:
                if edge.get("from") not in node_ids:
                    errors.append(f"Edge references unknown source node: {edge.get('from')}")
                if edge.get("to") not in node_ids:
                    errors.append(f"Edge references unknown target node: {edge.get('to')}")
        
        # Check for entry point
        if schema.get("nodes") and len(schema["nodes"]) > 0:
            first_node_id = schema["nodes"][0]["id"]
            has_entry = any(
                edge.get("from") == first_node_id 
                for edge in schema.get("edges", [])
            )
            if not has_entry and len(schema["nodes"]) > 1:
                warnings.append(f"First node '{first_node_id}' has no outgoing edges")
        
        # Check for orphaned nodes
        if "nodes" in schema and "edges" in schema:
            connected_nodes = set()
            for edge in schema["edges"]:
                connected_nodes.add(edge.get("from"))
                connected_nodes.add(edge.get("to"))
            
            for node in schema["nodes"]:
                if node["id"] not in connected_nodes and len(schema["nodes"]) > 1:
                    warnings.append(f"Node '{node['id']}' is not connected to any edges")
        
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
    """
    Export workflow as Mermaid diagram
    """
    schema = await get_schema(schema_id)
    
    mermaid = ["graph TD"]
    
    # Add nodes
    for node in schema.get("nodes", []):
        node_id = node["id"]
        node_type = node.get("type", "unknown")
        label = node.get("description", node_id)
        
        if node_type == "agent":
            mermaid.append(f'    {node_id}["{label}<br/>🤖 Agent"]')
        elif node_type == "human_gate":
            mermaid.append(f'    {node_id}{{"🧑 {label}"}}"')
        elif node_type == "tool":
            mermaid.append(f'    {node_id}[["🔧 {label}"]]')
        else:
            mermaid.append(f'    {node_id}["{label}"]')
    
    # Add edges
    for edge in schema.get("edges", []):
        from_node = edge["from"]
        to_node = edge["to"]
        
        if "condition" in edge:
            condition = edge["condition"].replace('"', "'")
            mermaid.append(f'    {from_node} -->|"{condition}"| {to_node}')
        else:
            mermaid.append(f'    {from_node} --> {to_node}')
    
    return "\n".join(mermaid)