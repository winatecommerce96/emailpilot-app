"""
Schema API endpoints for workflow management
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.tools.codegen import SchemaValidator, ValidationError

router = APIRouter(prefix="/api/workflow")

# Schema storage directory
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
SCHEMAS_DIR.mkdir(exist_ok=True)


@router.get("/schema")
async def get_schema(name: str = "workflow") -> Dict[str, Any]:
    """Get workflow schema by name"""
    try:
        # First try schemas directory
        schema_file = SCHEMAS_DIR / f"{name}.json"
        
        if not schema_file.exists():
            # Try main workflow.json
            schema_file = Path(__file__).parent.parent / "workflow.json"
        
        if not schema_file.exists():
            raise HTTPException(status_code=404, detail=f"Schema '{name}' not found")
        
        with open(schema_file) as f:
            schema = json.load(f)
        
        return {
            "success": True,
            "schema": schema,
            "path": str(schema_file.relative_to(Path(__file__).parent.parent.parent))
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schema")
async def save_schema(
    schema: Dict[str, Any] = Body(...),
    validate: bool = True
) -> Dict[str, Any]:
    """Save or update workflow schema"""
    try:
        # Validate if requested
        if validate:
            validator = SchemaValidator(schema)
            try:
                validator.validate()
            except ValidationError as e:
                return {
                    "success": False,
                    "errors": e.errors,
                    "warnings": e.warnings
                }
        
        # Get schema name
        name = schema.get("name", "unnamed")
        
        # Save to schemas directory
        schema_file = SCHEMAS_DIR / f"{name}.json"
        
        # Add metadata
        if "metadata" not in schema:
            schema["metadata"] = {}
        schema["metadata"]["saved_at"] = datetime.now().isoformat()
        
        # Write schema
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)
        
        return {
            "success": True,
            "path": str(schema_file.relative_to(Path(__file__).parent.parent.parent)),
            "warnings": validator.warnings if validate else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/schema/validate")
async def validate_schema(schema: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Validate a workflow schema without saving"""
    try:
        validator = SchemaValidator(schema)
        validator.validate()
        
        return {
            "valid": True,
            "errors": [],
            "warnings": validator.warnings
        }
        
    except ValidationError as e:
        return {
            "valid": False,
            "errors": e.errors,
            "warnings": e.warnings
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": []
        }


@router.get("/schemas")
async def list_schemas() -> List[Dict[str, Any]]:
    """List all saved schemas"""
    schemas = []
    
    # Check schemas directory
    for schema_file in SCHEMAS_DIR.glob("*.json"):
        try:
            with open(schema_file) as f:
                schema = json.load(f)
            
            schemas.append({
                "name": schema.get("name", schema_file.stem),
                "version": schema.get("metadata", {}).get("version", "1.0.0"),
                "description": schema.get("metadata", {}).get("description", ""),
                "saved_at": schema.get("metadata", {}).get("saved_at"),
                "path": schema_file.stem
            })
        except Exception as e:
            print(f"Error loading schema {schema_file}: {e}")
    
    # Add main workflow.json
    main_schema = Path(__file__).parent.parent / "workflow.json"
    if main_schema.exists():
        try:
            with open(main_schema) as f:
                schema = json.load(f)
            
            schemas.append({
                "name": schema.get("name", "workflow"),
                "version": schema.get("metadata", {}).get("version", "1.0.0"),
                "description": schema.get("metadata", {}).get("description", ""),
                "saved_at": schema.get("metadata", {}).get("saved_at"),
                "path": "workflow",
                "is_main": True
            })
        except Exception:
            pass
    
    return schemas


@router.post("/schema/generate")
async def generate_code(name: str = "workflow") -> Dict[str, Any]:
    """Generate code from schema"""
    try:
        import subprocess
        
        # Run codegen
        result = subprocess.run(
            [sys.executable, "tools/codegen.py"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        
        if result.returncode != 0:
            raise ValueError(f"Codegen failed: {result.stderr}")
        
        return {
            "success": True,
            "output": result.stdout,
            "errors": result.stderr if result.stderr else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/export/mermaid")
async def export_mermaid(name: str = "workflow") -> str:
    """Export schema as Mermaid diagram"""
    try:
        # Load schema
        result = await get_schema(name)
        schema = result["schema"]
        
        mermaid = ["graph TD"]
        
        # Add nodes with styling
        for node in schema.get("nodes", []):
            node_id = node["id"]
            node_type = node.get("type", "unknown")
            
            if node_type == "agent":
                mermaid.append(f'    {node_id}["{node_id}<br/>🤖 Agent"]:::agent')
            elif node_type == "human_gate":
                mermaid.append(f'    {node_id}{{"🧑 {node_id}"}}:::human')
            elif node_type == "python_fn":
                mermaid.append(f'    {node_id}["{node_id}"]:::function')
            else:
                mermaid.append(f'    {node_id}["{node_id}"]')
        
        # Add edges
        for edge in schema.get("edges", []):
            from_node = edge["from"]
            to_node = edge["to"]
            
            if "condition" in edge:
                # Simplify condition for display
                condition = edge["condition"]
                if "get('valid'" in condition and "False" in condition:
                    label = "invalid"
                elif "get('valid'" in condition:
                    label = "valid"
                else:
                    label = condition[:20] + "..." if len(condition) > 20 else condition
                
                mermaid.append(f'    {from_node} -->|{label}| {to_node}')
            else:
                mermaid.append(f'    {from_node} --> {to_node}')
        
        # Add styling
        mermaid.extend([
            "",
            "    classDef agent fill:#e0f2fe,stroke:#0284c7,stroke-width:2px",
            "    classDef human fill:#fce7f3,stroke:#ec4899,stroke-width:2px",
            "    classDef function fill:#e9d5ff,stroke:#9333ea,stroke-width:2px"
        ])
        
        diagram = "\n".join(mermaid)
        
        # Return as markdown
        return f"""# Workflow: {schema.get('name', 'Unnamed')}

{schema.get('metadata', {}).get('description', '')}

```mermaid
{diagram}
```

## Nodes
{chr(10).join(f"- **{node['id']}** ({node['type']}): {node.get('impl', 'N/A')}" for node in schema.get('nodes', []))}

## State
{chr(10).join(f"- `{key}`: {type_str}" for key, type_str in schema.get('state', {}).items())}
"""
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))