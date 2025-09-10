"""
MCP Server Manager
Handles health checks and auto-starting of MCP services
"""

import asyncio
import subprocess
import logging
import httpx
from typing import Dict, Any, Optional
from pathlib import Path
import time
import os

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages MCP server lifecycle - health checks and auto-starting"""
    
    def __init__(self):
        self.servers = {
            "enhanced": {
                "name": "Klaviyo MCP Enhanced",
                "health_url": "http://localhost:9095/health",
                "port": 9095,
                "start_cmd": ["npm", "start"],
                "working_dir": Path(__file__).parent.parent.parent / "services" / "klaviyo_mcp_enhanced",
                "process": None,
                "startup_time": 5  # seconds to wait after starting
            },
            "fallback": {
                "name": "Klaviyo API Service", 
                "health_url": "http://localhost:9090/healthz",
                "port": 9090,
                "start_cmd": ["uvicorn", "main:app", "--port", "9090", "--host", "localhost"],
                "working_dir": Path(__file__).parent.parent.parent / "services" / "klaviyo_api",
                "process": None,
                "startup_time": 3
            }
        }
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def check_health(self, server_key: str) -> bool:
        """Check if a server is healthy"""
        server = self.servers.get(server_key)
        if not server:
            return False
            
        try:
            response = await self.client.get(server["health_url"])
            return response.status_code == 200
        except (httpx.RequestError, httpx.TimeoutException):
            return False
    
    async def is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use"""
        try:
            # Use lsof to check port usage
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0  # Port is in use if lsof returns 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def start_server(self, server_key: str) -> bool:
        """Start an MCP server if not already running"""
        server = self.servers.get(server_key)
        if not server:
            logger.error(f"Unknown server: {server_key}")
            return False
        
        # Check if already healthy
        if await self.check_health(server_key):
            logger.info(f"✅ {server['name']} is already running and healthy")
            return True
        
        # Check if port is in use but not healthy
        if await self.is_port_in_use(server["port"]):
            logger.warning(f"⚠️ Port {server['port']} is in use but {server['name']} is not healthy. Attempting to kill existing process...")
            try:
                # Kill existing process on port
                subprocess.run(
                    ["pkill", "-f", f"port.*{server['port']}"],
                    capture_output=True,
                    timeout=2
                )
                await asyncio.sleep(1)  # Wait for process to die
            except Exception as e:
                logger.error(f"Failed to kill existing process: {e}")
        
        # Start the server
        logger.info(f"🚀 Starting {server['name']} on port {server['port']}...")
        
        working_dir = server["working_dir"]
        if not working_dir.exists():
            logger.error(f"Working directory does not exist: {working_dir}")
            return False
        
        try:
            # Check if it's a Node.js project and npm install is needed
            if server_key == "enhanced":
                package_json = working_dir / "package.json"
                node_modules = working_dir / "node_modules"
                
                if package_json.exists() and not node_modules.exists():
                    logger.info(f"📦 Installing npm dependencies for {server['name']}...")
                    install_result = subprocess.run(
                        ["npm", "install"],
                        cwd=working_dir,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    if install_result.returncode != 0:
                        logger.error(f"npm install failed: {install_result.stderr}")
                        return False
            
            # Start the server process
            env = os.environ.copy()
            if server_key == "fallback":
                # Ensure Python environment for Klaviyo API
                env["PYTHONPATH"] = str(working_dir)
            
            server["process"] = subprocess.Popen(
                server["start_cmd"],
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info(f"⏳ Waiting {server['startup_time']} seconds for {server['name']} to start...")
            await asyncio.sleep(server["startup_time"])
            
            # Check if server is healthy
            max_retries = 10
            for i in range(max_retries):
                if await self.check_health(server_key):
                    logger.info(f"✅ {server['name']} started successfully!")
                    return True
                await asyncio.sleep(1)
            
            logger.error(f"❌ {server['name']} failed to become healthy after starting")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start {server['name']}: {e}")
            return False
    
    async def ensure_servers_running(self) -> Dict[str, bool]:
        """Ensure all MCP servers are running, start them if not"""
        results = {}
        
        for server_key in self.servers:
            results[server_key] = await self.start_server(server_key)
        
        return results
    
    async def stop_server(self, server_key: str) -> bool:
        """Stop an MCP server"""
        server = self.servers.get(server_key)
        if not server or not server["process"]:
            return False
        
        try:
            server["process"].terminate()
            server["process"].wait(timeout=5)
            server["process"] = None
            logger.info(f"🛑 Stopped {server['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop {server['name']}: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers"""
        status = {}
        
        for server_key, server_info in self.servers.items():
            is_healthy = await self.check_health(server_key)
            port_in_use = await self.is_port_in_use(server_info["port"])
            
            status[server_key] = {
                "name": server_info["name"],
                "port": server_info["port"],
                "healthy": is_healthy,
                "port_in_use": port_in_use,
                "process_running": server_info["process"] is not None
            }
        
        return status
    
    async def __aenter__(self):
        """Context manager entry - ensure servers are running"""
        await self.ensure_servers_running()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        await self.client.aclose()


# Singleton instance
_manager_instance: Optional[MCPServerManager] = None


def get_mcp_manager() -> MCPServerManager:
    """Get singleton MCP server manager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MCPServerManager()
    return _manager_instance


async def ensure_mcp_servers_ready() -> bool:
    """Convenience function to ensure MCP servers are ready"""
    manager = get_mcp_manager()
    results = await manager.ensure_servers_running()
    return all(results.values())