"""
MCP Client Manager for multi-client support

Manages Node.js MCP server instances for different clients,
each with their own API key and isolated process.
"""

import os
import json
import time
import asyncio
import subprocess
import threading
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MCPClientInstance:
    """Represents an MCP server instance for a specific client."""
    client_id: str
    api_key: str
    process: subprocess.Popen
    port: int
    created_at: float
    last_used: float
    
    def is_alive(self) -> bool:
        """Check if the process is still running."""
        return self.process.poll() is None
        
    def update_last_used(self):
        """Update the last used timestamp."""
        self.last_used = time.time()


class MCPClientManager:
    """
    Manages multiple MCP server instances for different clients.
    Each client gets an isolated Node.js process with their own API key.
    """
    
    def __init__(
        self,
        mcp_server_path: str,
        base_port: int = 10000,
        max_clients: int = 10,
        idle_timeout: int = 3600  # 1 hour
    ):
        """
        Initialize the MCP Client Manager.
        
        Args:
            mcp_server_path: Path to the Klaviyo MCP Enhanced server
            base_port: Starting port for MCP server instances
            max_clients: Maximum number of concurrent client instances
            idle_timeout: Seconds before cleaning up idle instances
        """
        self.mcp_server_path = Path(mcp_server_path)
        self.base_port = base_port
        self.max_clients = max_clients
        self.idle_timeout = idle_timeout
        self.instances: Dict[str, MCPClientInstance] = {}
        self.port_counter = 0
        self.lock = threading.Lock()
        
        # Verify MCP server exists
        if not self.mcp_server_path.exists():
            raise ValueError(f"MCP server path does not exist: {mcp_server_path}")
            
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
    def get_or_create_client(self, client_id: str, api_key: str) -> MCPClientInstance:
        """
        Get existing client instance or create a new one.
        
        Args:
            client_id: Client identifier
            api_key: Klaviyo API key for this client
            
        Returns:
            MCPClientInstance with running server
            
        Raises:
            RuntimeError: If max clients reached or server fails to start
        """
        with self.lock:
            # Check if instance exists and is alive
            if client_id in self.instances:
                instance = self.instances[client_id]
                if instance.is_alive():
                    instance.update_last_used()
                    # Check if API key changed
                    if instance.api_key != api_key:
                        logger.info(f"API key changed for client {client_id}, restarting instance")
                        self._stop_instance(client_id)
                    else:
                        return instance
                else:
                    logger.warning(f"Instance for client {client_id} died, cleaning up")
                    self._cleanup_instance(client_id)
                    
            # Check max clients limit
            if len(self.instances) >= self.max_clients:
                # Try to clean up idle instances
                self._cleanup_idle_instances()
                if len(self.instances) >= self.max_clients:
                    raise RuntimeError(f"Maximum number of MCP clients ({self.max_clients}) reached")
                    
            # Create new instance
            return self._create_instance(client_id, api_key)
            
    def _create_instance(self, client_id: str, api_key: str) -> MCPClientInstance:
        """
        Create a new MCP server instance for a client.
        
        Args:
            client_id: Client identifier
            api_key: Klaviyo API key
            
        Returns:
            New MCPClientInstance
            
        Raises:
            RuntimeError: If server fails to start
        """
        port = self.base_port + self.port_counter
        self.port_counter = (self.port_counter + 1) % 1000  # Cycle through 1000 ports
        
        # Create environment with API key
        env = os.environ.copy()
        env["KLAVIYO_API_KEY"] = api_key
        env["MCP_SERVER_PORT"] = str(port)
        env["NODE_ENV"] = "production"
        
        # Start the Node.js MCP server
        logger.info(f"Starting MCP server for client {client_id} on port {port}")
        
        try:
            process = subprocess.Popen(
                ["npm", "start"],
                cwd=self.mcp_server_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise RuntimeError(f"MCP server failed to start: {stderr}")
                
            instance = MCPClientInstance(
                client_id=client_id,
                api_key=api_key,
                process=process,
                port=port,
                created_at=time.time(),
                last_used=time.time()
            )
            
            self.instances[client_id] = instance
            logger.info(f"MCP server started successfully for client {client_id}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to start MCP server for client {client_id}: {e}")
            raise RuntimeError(f"Failed to start MCP server: {e}")
            
    def _stop_instance(self, client_id: str):
        """
        Stop and remove an MCP server instance.
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.instances:
            instance = self.instances[client_id]
            if instance.is_alive():
                logger.info(f"Stopping MCP server for client {client_id}")
                instance.process.terminate()
                try:
                    instance.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing MCP server for client {client_id}")
                    instance.process.kill()
                    instance.process.wait()
            del self.instances[client_id]
            
    def _cleanup_instance(self, client_id: str):
        """
        Clean up a dead or idle instance.
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.instances:
            instance = self.instances[client_id]
            if instance.is_alive():
                instance.process.terminate()
                try:
                    instance.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    instance.process.kill()
            del self.instances[client_id]
            logger.info(f"Cleaned up MCP instance for client {client_id}")
            
    def _cleanup_idle_instances(self):
        """Clean up instances that have been idle too long."""
        current_time = time.time()
        clients_to_clean = []
        
        for client_id, instance in self.instances.items():
            if current_time - instance.last_used > self.idle_timeout:
                clients_to_clean.append(client_id)
                
        for client_id in clients_to_clean:
            logger.info(f"Cleaning up idle MCP instance for client {client_id}")
            self._cleanup_instance(client_id)
            
    def _cleanup_loop(self):
        """Background thread to clean up idle instances."""
        while True:
            time.sleep(60)  # Check every minute
            with self.lock:
                self._cleanup_idle_instances()
                
    def call_tool(self, client_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool for a specific client.
        
        Args:
            client_id: Client identifier
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            
        Returns:
            Tool response
            
        Raises:
            RuntimeError: If tool call fails
        """
        import httpx
        
        # Get client instance (assumes API key already resolved)
        if client_id not in self.instances:
            raise RuntimeError(f"No MCP instance for client {client_id}. Call get_or_create_client first.")
            
        instance = self.instances[client_id]
        instance.update_last_used()
        
        if not instance.is_alive():
            raise RuntimeError(f"MCP instance for client {client_id} is not running")
            
        # Make HTTP request to the MCP server
        url = f"http://localhost:{instance.port}/tools/{tool_name}"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=arguments)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name} for client {client_id}: {e}")
            raise RuntimeError(f"Tool call failed: {e}")
            
    async def call_tool_async(self, client_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async version of call_tool.
        
        Args:
            client_id: Client identifier
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            
        Returns:
            Tool response
        """
        import httpx
        
        if client_id not in self.instances:
            raise RuntimeError(f"No MCP instance for client {client_id}. Call get_or_create_client first.")
            
        instance = self.instances[client_id]
        instance.update_last_used()
        
        if not instance.is_alive():
            raise RuntimeError(f"MCP instance for client {client_id} is not running")
            
        url = f"http://localhost:{instance.port}/tools/{tool_name}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=arguments)
            response.raise_for_status()
            return response.json()
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all client instances.
        
        Returns:
            Status dictionary
        """
        with self.lock:
            status = {
                "total_instances": len(self.instances),
                "max_clients": self.max_clients,
                "idle_timeout": self.idle_timeout,
                "instances": []
            }
            
            for client_id, instance in self.instances.items():
                status["instances"].append({
                    "client_id": client_id,
                    "port": instance.port,
                    "is_alive": instance.is_alive(),
                    "created_at": instance.created_at,
                    "last_used": instance.last_used,
                    "idle_seconds": time.time() - instance.last_used
                })
                
            return status
            
    def shutdown(self):
        """Shutdown all client instances."""
        logger.info("Shutting down all MCP client instances")
        with self.lock:
            for client_id in list(self.instances.keys()):
                self._stop_instance(client_id)