"""
Universal MCP Server Registry
Manages discovery, registration, and health monitoring of MCP servers
"""

import asyncio
import httpx
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

@dataclass
class MCPServerSpec:
    """Specification for an MCP server"""
    id: str
    name: str
    description: str
    url: str
    port: int
    type: str  # e.g., "marketing", "crm", "analytics", "finance"
    provider: str  # e.g., "klaviyo", "salesforce", "google"
    version: str
    status: str  # "online", "offline", "error", "unknown"
    capabilities: List[str]  # List of tool categories
    health_endpoint: str
    tools_endpoint: str
    invoke_endpoint: str
    auth_required: bool
    last_check: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MCPServerRegistry:
    """Universal registry for MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerSpec] = {}
        self.client = httpx.AsyncClient(timeout=5.0)
        self._initialize_default_servers()
    
    def _initialize_default_servers(self):
        """Initialize with known MCP servers"""
        default_servers = [
            MCPServerSpec(
                id="klaviyo_enhanced",
                name="Klaviyo Enhanced MCP",
                description="Enhanced Node.js wrapper for Klaviyo API with 20+ operations",
                url="http://localhost:9095",
                port=9095,
                type="marketing",
                provider="klaviyo",
                version="1.0.0",
                status="unknown",
                capabilities=["campaigns", "metrics", "segments", "profiles", "flows", "templates"],
                health_endpoint="/health",
                tools_endpoint="/mcp/tools", 
                invoke_endpoint="/mcp/invoke",
                auth_required=True,
                metadata={
                    "startup_cmd": ["npm", "start"],
                    "working_dir": "services/klaviyo_mcp_enhanced",
                    "startup_time": 5
                }
            ),
            MCPServerSpec(
                id="klaviyo_python",
                name="Python Klaviyo MCP",
                description="Python FastAPI implementation for Klaviyo operations",
                url="http://localhost:9090",
                port=9090,
                type="marketing",
                provider="klaviyo",
                version="1.0.0",
                status="unknown",
                capabilities=["campaigns", "metrics", "segments"],
                health_endpoint="/healthz",
                tools_endpoint="/tools",
                invoke_endpoint="/tools/invoke",
                auth_required=True,
                metadata={
                    "startup_cmd": ["uvicorn", "main:app", "--port", "9090", "--host", "localhost"],
                    "working_dir": "services/klaviyo_api",
                    "startup_time": 3
                }
            ),
            MCPServerSpec(
                id="salesforce_mcp",
                name="Salesforce MCP Server",
                description="CRM operations and lead management (Coming Soon)",
                url="http://localhost:9096",
                port=9096,
                type="crm",
                provider="salesforce",
                version="0.1.0",
                status="planned",
                capabilities=["leads", "contacts", "opportunities", "accounts"],
                health_endpoint="/health",
                tools_endpoint="/tools",
                invoke_endpoint="/invoke",
                auth_required=True,
                metadata={
                    "planned_release": "Q2 2025",
                    "dependencies": ["salesforce-api", "oauth2"]
                }
            ),
            MCPServerSpec(
                id="analytics_mcp",
                name="Analytics MCP Server", 
                description="Google Analytics 4 and Adobe Analytics integration (Coming Soon)",
                url="http://localhost:9097",
                port=9097,
                type="analytics",
                provider="google",
                version="0.1.0",
                status="planned",
                capabilities=["metrics", "reports", "audiences", "conversions"],
                health_endpoint="/health",
                tools_endpoint="/tools",
                invoke_endpoint="/invoke",
                auth_required=True,
                metadata={
                    "planned_release": "Q1 2025",
                    "supported_platforms": ["GA4", "Adobe Analytics", "Mixpanel"]
                }
            ),
            MCPServerSpec(
                id="mcp_gateway",
                name="MCP Smart Gateway",
                description="Intelligent routing to best available MCP server",
                url="http://localhost:8000/api/mcp/gateway",
                port=8000,
                type="gateway",
                provider="emailpilot",
                version="1.0.0",
                status="unknown",
                capabilities=["routing", "load_balancing", "failover"],
                health_endpoint="/health",
                tools_endpoint="/tools",
                invoke_endpoint="/invoke",
                auth_required=False,
                metadata={
                    "router_type": "smart",
                    "fallback_enabled": True
                }
            )
        ]
        
        for server in default_servers:
            self.servers[server.id] = server
    
    async def register_server(self, server_spec: MCPServerSpec) -> bool:
        """Register a new MCP server"""
        try:
            # Validate server spec
            if not server_spec.id or not server_spec.url:
                raise ValueError("Server ID and URL are required")
            
            # Check if server is already registered
            if server_spec.id in self.servers:
                logger.warning(f"Server {server_spec.id} already registered, updating...")
            
            # Store server
            self.servers[server_spec.id] = server_spec
            
            # Perform initial health check
            await self._check_server_health(server_spec.id)
            
            logger.info(f"Successfully registered MCP server: {server_spec.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register server {server_spec.id}: {e}")
            return False
    
    async def discover_servers(self, port_range: tuple = (9090, 9100)) -> List[MCPServerSpec]:
        """Auto-discover MCP servers on common ports"""
        discovered = []
        
        for port in range(port_range[0], port_range[1] + 1):
            try:
                url = f"http://localhost:{port}"
                response = await self.client.get(f"{url}/health", timeout=1.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Try to get server info
                    server_id = f"discovered_{port}"
                    server_name = data.get("name", f"MCP Server (Port {port})")
                    
                    discovered_server = MCPServerSpec(
                        id=server_id,
                        name=server_name,
                        description=f"Auto-discovered server on port {port}",
                        url=url,
                        port=port,
                        type="unknown",
                        provider="unknown",
                        version=data.get("version", "unknown"),
                        status="online",
                        capabilities=data.get("capabilities", []),
                        health_endpoint="/health",
                        tools_endpoint="/tools",
                        invoke_endpoint="/invoke",
                        auth_required=True,
                        last_check=datetime.now().isoformat()
                    )
                    
                    discovered.append(discovered_server)
                    
                    # Auto-register if not already known
                    if server_id not in self.servers:
                        self.servers[server_id] = discovered_server
                        logger.info(f"Auto-registered discovered server: {server_name}")
                        
            except Exception:
                # Silently skip ports with no server
                continue
        
        return discovered
    
    async def _check_server_health(self, server_id: str) -> bool:
        """Check health of a specific server"""
        if server_id not in self.servers:
            return False
        
        server = self.servers[server_id]
        
        # Skip health check for planned servers
        if server.status == "planned":
            return False
        
        try:
            response = await self.client.get(f"{server.url}{server.health_endpoint}")
            
            if response.status_code == 200:
                server.status = "online"
                server.error_message = None
                server.last_check = datetime.now().isoformat()
                return True
            else:
                server.status = "error"
                server.error_message = f"HTTP {response.status_code}"
                server.last_check = datetime.now().isoformat()
                return False
                
        except Exception as e:
            server.status = "offline"
            server.error_message = str(e)
            server.last_check = datetime.now().isoformat()
            return False
    
    async def check_all_servers_health(self) -> Dict[str, bool]:
        """Check health of all registered servers"""
        results = {}
        
        tasks = []
        for server_id in self.servers:
            tasks.append(self._check_server_health(server_id))
        
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, server_id in enumerate(self.servers):
            if isinstance(health_results[i], Exception):
                results[server_id] = False
                self.servers[server_id].status = "error"
                self.servers[server_id].error_message = str(health_results[i])
            else:
                results[server_id] = health_results[i]
        
        return results
    
    def get_servers_by_type(self, server_type: str) -> List[MCPServerSpec]:
        """Get servers by type (marketing, crm, analytics, etc.)"""
        return [server for server in self.servers.values() if server.type == server_type]
    
    def get_servers_by_capability(self, capability: str) -> List[MCPServerSpec]:
        """Get servers that support a specific capability"""
        return [
            server for server in self.servers.values() 
            if capability in server.capabilities
        ]
    
    def get_online_servers(self) -> List[MCPServerSpec]:
        """Get all currently online servers"""
        return [server for server in self.servers.values() if server.status == "online"]
    
    def get_server(self, server_id: str) -> Optional[MCPServerSpec]:
        """Get a specific server by ID"""
        return self.servers.get(server_id)
    
    def get_all_servers(self) -> List[MCPServerSpec]:
        """Get all registered servers"""
        return list(self.servers.values())
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total = len(self.servers)
        online = len([s for s in self.servers.values() if s.status == "online"])
        offline = len([s for s in self.servers.values() if s.status == "offline"])
        planned = len([s for s in self.servers.values() if s.status == "planned"])
        error = len([s for s in self.servers.values() if s.status == "error"])
        
        types = {}
        for server in self.servers.values():
            types[server.type] = types.get(server.type, 0) + 1
        
        return {
            "total_servers": total,
            "online": online,
            "offline": offline,
            "planned": planned,
            "error": error,
            "types": types,
            "last_updated": datetime.now().isoformat()
        }
    
    async def export_registry(self) -> Dict[str, Any]:
        """Export registry configuration"""
        return {
            "version": "1.0.0",
            "exported_at": datetime.now().isoformat(),
            "servers": [asdict(server) for server in self.servers.values()]
        }
    
    async def import_registry(self, registry_data: Dict[str, Any]) -> bool:
        """Import registry configuration"""
        try:
            if "servers" not in registry_data:
                raise ValueError("Invalid registry format")
            
            imported_count = 0
            for server_data in registry_data["servers"]:
                server_spec = MCPServerSpec(**server_data)
                await self.register_server(server_spec)
                imported_count += 1
            
            logger.info(f"Imported {imported_count} servers to registry")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import registry: {e}")
            return False
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.client.aclose()

# Singleton instance
_registry_instance: Optional[MCPServerRegistry] = None

def get_mcp_registry() -> MCPServerRegistry:
    """Get singleton MCP registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MCPServerRegistry()
    return _registry_instance

async def refresh_registry_health() -> Dict[str, Any]:
    """Convenience function to refresh all server health checks"""
    registry = get_mcp_registry()
    health_results = await registry.check_all_servers_health()
    stats = registry.get_registry_stats()
    
    return {
        "health_check_results": health_results,
        "registry_stats": stats,
        "refresh_time": datetime.now().isoformat()
    }