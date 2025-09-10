"""
MCP Registry API
FastAPI endpoints for managing the universal MCP server registry
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.services.mcp_registry import get_mcp_registry, MCPServerSpec, refresh_registry_health

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mcp/registry", tags=["mcp-registry"])

class RegisterServerRequest(BaseModel):
    """Request to register a new MCP server"""
    id: str = Field(..., description="Unique server identifier")
    name: str = Field(..., description="Human-readable server name")
    description: str = Field(..., description="Server description")
    url: str = Field(..., description="Server base URL")
    port: int = Field(..., description="Server port")
    type: str = Field(..., description="Server type (marketing, crm, analytics, etc.)")
    provider: str = Field(..., description="Service provider")
    version: str = Field(default="1.0.0", description="Server version")
    capabilities: List[str] = Field(default=[], description="List of capabilities")
    health_endpoint: str = Field(default="/health", description="Health check endpoint")
    tools_endpoint: str = Field(default="/tools", description="Tools listing endpoint")
    invoke_endpoint: str = Field(default="/invoke", description="Tool invocation endpoint")
    auth_required: bool = Field(default=True, description="Whether authentication is required")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

@router.get("/servers")
async def list_servers(
    type: Optional[str] = Query(None, description="Filter by server type"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    status: Optional[str] = Query(None, description="Filter by status"),
    online_only: bool = Query(False, description="Return only online servers")
):
    """
    List all registered MCP servers with optional filtering
    """
    try:
        registry = get_mcp_registry()
        servers = registry.get_all_servers()
        
        # Apply filters
        if type:
            servers = [s for s in servers if s.type == type]
        
        if capability:
            servers = [s for s in servers if capability in s.capabilities]
        
        if status:
            servers = [s for s in servers if s.status == status]
        
        if online_only:
            servers = [s for s in servers if s.status == "online"]
        
        return {
            "success": True,
            "count": len(servers),
            "servers": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "url": s.url,
                    "port": s.port,
                    "type": s.type,
                    "provider": s.provider,
                    "version": s.version,
                    "status": s.status,
                    "capabilities": s.capabilities,
                    "last_check": s.last_check,
                    "error_message": s.error_message,
                    "metadata": s.metadata
                }
                for s in servers
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    """
    Get detailed information about a specific MCP server
    """
    try:
        registry = get_mcp_registry()
        server = registry.get_server(server_id)
        
        if not server:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        return {
            "success": True,
            "server": {
                "id": server.id,
                "name": server.name,
                "description": server.description,
                "url": server.url,
                "port": server.port,
                "type": server.type,
                "provider": server.provider,
                "version": server.version,
                "status": server.status,
                "capabilities": server.capabilities,
                "health_endpoint": server.health_endpoint,
                "tools_endpoint": server.tools_endpoint,
                "invoke_endpoint": server.invoke_endpoint,
                "auth_required": server.auth_required,
                "last_check": server.last_check,
                "error_message": server.error_message,
                "metadata": server.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/servers/register")
async def register_server(request: RegisterServerRequest):
    """
    Register a new MCP server in the registry
    """
    try:
        registry = get_mcp_registry()
        
        server_spec = MCPServerSpec(
            id=request.id,
            name=request.name,
            description=request.description,
            url=request.url,
            port=request.port,
            type=request.type,
            provider=request.provider,
            version=request.version,
            status="unknown",
            capabilities=request.capabilities,
            health_endpoint=request.health_endpoint,
            tools_endpoint=request.tools_endpoint,
            invoke_endpoint=request.invoke_endpoint,
            auth_required=request.auth_required,
            metadata=request.metadata
        )
        
        success = await registry.register_server(server_spec)
        
        if success:
            return {
                "success": True,
                "message": f"Server {request.name} registered successfully",
                "server_id": request.id
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to register server")
            
    except Exception as e:
        logger.error(f"Error registering server: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/servers/discover")
async def discover_servers(
    port_start: int = Query(9090, description="Start of port range to scan"),
    port_end: int = Query(9100, description="End of port range to scan")
):
    """
    Auto-discover MCP servers running on local ports
    """
    try:
        registry = get_mcp_registry()
        discovered = await registry.discover_servers((port_start, port_end))
        
        return {
            "success": True,
            "discovered_count": len(discovered),
            "servers": [
                {
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "port": s.port,
                    "status": s.status,
                    "capabilities": s.capabilities
                }
                for s in discovered
            ],
            "message": f"Discovered {len(discovered)} servers in port range {port_start}-{port_end}"
        }
        
    except Exception as e:
        logger.error(f"Error discovering servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/health/check-all")
async def check_all_health():
    """
    Check health status of all registered servers
    """
    try:
        result = await refresh_registry_health()
        return {
            "success": True,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error checking server health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/health/check/{server_id}")
async def check_server_health(server_id: str):
    """
    Check health status of a specific server
    """
    try:
        registry = get_mcp_registry()
        server = registry.get_server(server_id)
        
        if not server:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        # Check health using private method (normally we'd make this public)
        health_ok = await registry._check_server_health(server_id)
        updated_server = registry.get_server(server_id)
        
        return {
            "success": True,
            "server_id": server_id,
            "health_ok": health_ok,
            "status": updated_server.status,
            "last_check": updated_server.last_check,
            "error_message": updated_server.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking health for server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_registry_stats():
    """
    Get registry statistics and overview
    """
    try:
        registry = get_mcp_registry()
        stats = registry.get_registry_stats()
        
        return {
            "success": True,
            **stats
        }
        
    except Exception as e:
        logger.error(f"Error getting registry stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_server_types():
    """
    Get available server types and their counts
    """
    try:
        registry = get_mcp_registry()
        servers = registry.get_all_servers()
        
        types = {}
        for server in servers:
            if server.type not in types:
                types[server.type] = {
                    "count": 0,
                    "online": 0,
                    "offline": 0,
                    "servers": []
                }
            
            types[server.type]["count"] += 1
            types[server.type]["servers"].append({
                "id": server.id,
                "name": server.name,
                "status": server.status
            })
            
            if server.status == "online":
                types[server.type]["online"] += 1
            elif server.status in ["offline", "error"]:
                types[server.type]["offline"] += 1
        
        return {
            "success": True,
            "types": types,
            "total_types": len(types)
        }
        
    except Exception as e:
        logger.error(f"Error getting server types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capabilities")
async def get_capabilities():
    """
    Get all available capabilities across servers
    """
    try:
        registry = get_mcp_registry()
        servers = registry.get_all_servers()
        
        capabilities = {}
        for server in servers:
            for capability in server.capabilities:
                if capability not in capabilities:
                    capabilities[capability] = {
                        "servers": [],
                        "total": 0,
                        "online": 0
                    }
                
                capabilities[capability]["servers"].append({
                    "id": server.id,
                    "name": server.name,
                    "status": server.status
                })
                capabilities[capability]["total"] += 1
                
                if server.status == "online":
                    capabilities[capability]["online"] += 1
        
        return {
            "success": True,
            "capabilities": capabilities,
            "total_capabilities": len(capabilities)
        }
        
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export")
async def export_registry():
    """
    Export registry configuration
    """
    try:
        registry = get_mcp_registry()
        export_data = await registry.export_registry()
        
        return {
            "success": True,
            "export": export_data
        }
        
    except Exception as e:
        logger.error(f"Error exporting registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def import_registry(registry_data: Dict[str, Any]):
    """
    Import registry configuration
    """
    try:
        registry = get_mcp_registry()
        success = await registry.import_registry(registry_data)
        
        if success:
            return {
                "success": True,
                "message": "Registry imported successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to import registry")
            
    except Exception as e:
        logger.error(f"Error importing registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))