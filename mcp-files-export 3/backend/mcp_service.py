"""
Enhanced MCP Service with multi-model support
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import openai
import google.generativeai as genai
from anthropic import Anthropic
import logging
from app.services.secret_manager import get_secret_manager
from app.models.mcp_client import MCPClient, MCPUsage, MCPModelConfig
from app.core.database import get_db
from sqlalchemy.orm import Session
import time

logger = logging.getLogger(__name__)


class MCPServiceManager:
    """Manages MCP connections for multiple AI providers"""
    
    def __init__(self):
        self.secret_manager = get_secret_manager()
        self.mcp_instances = {}  # client_id -> MCPInstance
        self.model_configs = self._load_model_configs()
    
    def _load_model_configs(self) -> Dict[str, Dict]:
        """Load model configurations"""
        return {
            "claude": {
                "models": {
                    "claude-3-opus": {
                        "name": "claude-3-opus-20240229",
                        "display_name": "Claude 3 Opus",
                        "max_tokens": 4096,
                        "context_window": 200000,
                        "input_cost_per_1k": 0.015,
                        "output_cost_per_1k": 0.075
                    },
                    "claude-3-sonnet": {
                        "name": "claude-3-sonnet-20240229",
                        "display_name": "Claude 3 Sonnet",
                        "max_tokens": 4096,
                        "context_window": 200000,
                        "input_cost_per_1k": 0.003,
                        "output_cost_per_1k": 0.015
                    }
                }
            },
            "openai": {
                "models": {
                    "gpt-4-turbo": {
                        "name": "gpt-4-turbo-preview",
                        "display_name": "GPT-4 Turbo",
                        "max_tokens": 4096,
                        "context_window": 128000,
                        "input_cost_per_1k": 0.01,
                        "output_cost_per_1k": 0.03
                    },
                    "gpt-4": {
                        "name": "gpt-4",
                        "display_name": "GPT-4",
                        "max_tokens": 8192,
                        "context_window": 8192,
                        "input_cost_per_1k": 0.03,
                        "output_cost_per_1k": 0.06
                    },
                    "gpt-3.5-turbo": {
                        "name": "gpt-3.5-turbo",
                        "display_name": "GPT-3.5 Turbo",
                        "max_tokens": 4096,
                        "context_window": 16385,
                        "input_cost_per_1k": 0.0005,
                        "output_cost_per_1k": 0.0015
                    }
                }
            },
            "gemini": {
                "models": {
                    "gemini-pro": {
                        "name": "gemini-pro",
                        "display_name": "Gemini Pro",
                        "max_tokens": 8192,
                        "context_window": 32760,
                        "input_cost_per_1k": 0.00025,
                        "output_cost_per_1k": 0.0005
                    },
                    "gemini-pro-vision": {
                        "name": "gemini-pro-vision",
                        "display_name": "Gemini Pro Vision",
                        "max_tokens": 4096,
                        "context_window": 16384,
                        "input_cost_per_1k": 0.00025,
                        "output_cost_per_1k": 0.0005
                    }
                }
            }
        }
    
    async def get_mcp_instance(self, client_id: str, provider: str = None) -> 'MCPInstance':
        """Get or create an MCP instance for a client"""
        cache_key = f"{client_id}:{provider or 'default'}"
        
        if cache_key not in self.mcp_instances:
            # Load client configuration
            db = next(get_db())
            client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
            if not client:
                raise ValueError(f"Client {client_id} not found")
            
            # Get API keys from Secret Manager
            api_keys = self.secret_manager.get_api_keys(client_id)
            
            # Determine provider
            provider = provider or client.default_model_provider
            
            # Create instance based on provider
            instance = MCPInstance(
                client_id=client_id,
                client_config=client,
                provider=provider,
                api_keys=api_keys,
                model_configs=self.model_configs.get(provider, {})
            )
            
            self.mcp_instances[cache_key] = instance
        
        return self.mcp_instances[cache_key]
    
    async def execute_tool(
        self,
        client_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        provider: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """Execute an MCP tool using specified provider"""
        start_time = time.time()
        
        try:
            # Get MCP instance
            instance = await self.get_mcp_instance(client_id, provider)
            
            # Execute tool based on provider
            result = await instance.execute_tool(tool_name, parameters, model)
            
            # Track usage
            latency_ms = int((time.time() - start_time) * 1000)
            await self._track_usage(
                client_id=client_id,
                provider=provider or instance.provider,
                model=model or instance.default_model,
                tool_name=tool_name,
                request_tokens=result.get("request_tokens", 0),
                response_tokens=result.get("response_tokens", 0),
                latency_ms=latency_ms,
                status="success"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            
            # Track failed usage
            latency_ms = int((time.time() - start_time) * 1000)
            await self._track_usage(
                client_id=client_id,
                provider=provider or "unknown",
                model=model or "unknown",
                tool_name=tool_name,
                request_tokens=0,
                response_tokens=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e)
            )
            
            raise
    
    async def _track_usage(
        self,
        client_id: str,
        provider: str,
        model: str,
        tool_name: str,
        request_tokens: int,
        response_tokens: int,
        latency_ms: int,
        status: str,
        error_message: str = None
    ):
        """Track usage metrics"""
        db = next(get_db())
        
        # Calculate cost
        model_config = self.model_configs.get(provider, {}).get("models", {}).get(model, {})
        input_cost = (request_tokens / 1000) * model_config.get("input_cost_per_1k", 0)
        output_cost = (response_tokens / 1000) * model_config.get("output_cost_per_1k", 0)
        total_cost = input_cost + output_cost
        
        # Create usage record
        usage = MCPUsage(
            client_id=client_id,
            model_provider=provider,
            model_name=model,
            tool_name=tool_name,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            total_tokens=request_tokens + response_tokens,
            latency_ms=latency_ms,
            estimated_cost=total_cost,
            request_id=f"{client_id}:{provider}:{tool_name}:{datetime.now().isoformat()}",
            status=status,
            error_message=error_message,
            completed_at=datetime.now()
        )
        
        db.add(usage)
        
        # Update client stats
        client = db.query(MCPClient).filter(MCPClient.id == client_id).first()
        if client:
            client.total_requests += 1
            client.total_tokens_used += request_tokens + response_tokens
            client.last_used_at = datetime.now()
        
        db.commit()
    
    async def test_connection(self, client_id: str, provider: str) -> Dict[str, Any]:
        """Test MCP connection for a specific provider"""
        try:
            instance = await self.get_mcp_instance(client_id, provider)
            result = await instance.test_connection()
            return {
                "success": True,
                "provider": provider,
                "available_tools": result.get("tools", []),
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider,
                "error": str(e),
                "message": "Connection failed"
            }


class MCPInstance:
    """Individual MCP instance for a specific client and provider"""
    
    def __init__(
        self,
        client_id: str,
        client_config: MCPClient,
        provider: str,
        api_keys: Dict[str, str],
        model_configs: Dict[str, Any]
    ):
        self.client_id = client_id
        self.client_config = client_config
        self.provider = provider
        self.api_keys = api_keys
        self.model_configs = model_configs
        self.default_model = self._get_default_model()
        
        # Initialize provider-specific clients
        self._init_provider_client()
    
    def _get_default_model(self) -> str:
        """Get default model for the provider"""
        models = self.model_configs.get("models", {})
        if models:
            return list(models.keys())[0]
        return "default"
    
    def _init_provider_client(self):
        """Initialize provider-specific API client"""
        if self.provider == "claude":
            # Use existing MCP server process
            self.mcp_process = None
            api_key = self.api_keys.get("klaviyo")  # Klaviyo key for MCP server
            if api_key:
                self.anthropic_client = Anthropic(api_key=api_key)
            else:
                self.anthropic_client = None
            
        elif self.provider == "openai":
            api_key = self.api_keys.get("openai")
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            self.openai_client = openai.OpenAI(api_key=api_key)
            
        elif self.provider == "gemini":
            api_key = self.api_keys.get("gemini")
            if not api_key:
                raise ValueError("Gemini API key not configured")
            genai.configure(api_key=api_key)
            self.gemini_client = genai
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        model: str = None
    ) -> Dict[str, Any]:
        """Execute MCP tool using the configured provider"""
        model = model or self.default_model
        
        if self.provider == "claude":
            return await self._execute_claude_mcp(tool_name, parameters, model)
        elif self.provider == "openai":
            return await self._execute_openai_tool(tool_name, parameters, model)
        elif self.provider == "gemini":
            return await self._execute_gemini_tool(tool_name, parameters, model)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def _execute_claude_mcp(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """Execute tool using Claude MCP server"""
        # Start MCP server process if not running
        if not self.mcp_process:
            self.mcp_process = await self._start_mcp_process()
        
        # Send request to MCP server
        request = {
            "jsonrpc": "2.0",
            "method": f"tools/{tool_name}",
            "params": parameters,
            "id": f"{self.client_id}:{tool_name}:{datetime.now().isoformat()}"
        }
        
        # Execute via subprocess or HTTP depending on configuration
        response = await self._send_mcp_request(request)
        
        return {
            "result": response.get("result"),
            "request_tokens": 0,  # TODO: Calculate from actual usage
            "response_tokens": 0  # TODO: Calculate from actual usage
        }
    
    async def _execute_openai_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """Execute tool using OpenAI function calling"""
        model_name = self.model_configs["models"][model]["name"]
        
        # Map MCP tool to OpenAI function
        functions = [{
            "name": tool_name,
            "description": f"Execute {tool_name} with Klaviyo data",
            "parameters": {
                "type": "object",
                "properties": parameters
            }
        }]
        
        # Create chat completion with function calling
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an MCP tool executor for Klaviyo data."},
                {"role": "user", "content": f"Execute {tool_name} with parameters: {json.dumps(parameters)}"}
            ],
            functions=functions,
            function_call={"name": tool_name}
        )
        
        # Extract function call result
        function_call = response.choices[0].message.get("function_call", {})
        
        # Execute actual Klaviyo API call
        result = await self._execute_klaviyo_tool(tool_name, json.loads(function_call.get("arguments", "{}")))
        
        return {
            "result": result,
            "request_tokens": response.usage.prompt_tokens,
            "response_tokens": response.usage.completion_tokens
        }
    
    async def _execute_gemini_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """Execute tool using Gemini function calling"""
        model_name = self.model_configs["models"][model]["name"]
        
        # Initialize Gemini model
        gemini_model = genai.GenerativeModel(model_name)
        
        # Create tool definition
        tools = [
            {
                "function_declarations": [{
                    "name": tool_name,
                    "description": f"Execute {tool_name} with Klaviyo data",
                    "parameters": {
                        "type": "object",
                        "properties": parameters
                    }
                }]
            }
        ]
        
        # Generate with function calling
        response = await asyncio.to_thread(
            gemini_model.generate_content,
            f"Execute {tool_name} with parameters: {json.dumps(parameters)}",
            tools=tools
        )
        
        # Execute actual Klaviyo API call
        result = await self._execute_klaviyo_tool(tool_name, parameters)
        
        return {
            "result": result,
            "request_tokens": 0,  # Gemini doesn't provide token counts directly
            "response_tokens": 0
        }
    
    async def _execute_klaviyo_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute actual Klaviyo API operation"""
        klaviyo_key = self.api_keys.get("klaviyo")
        if not klaviyo_key:
            raise ValueError("Klaviyo API key not configured")
        
        # Map tool names to Klaviyo API endpoints
        tool_mappings = {
            "get_campaigns": "/api/campaigns",
            "get_flows": "/api/flows",
            "get_segments": "/api/segments",
            "get_metrics": "/api/metrics",
            "get_lists": "/api/lists",
            "get_profiles": "/api/profiles",
            "get_templates": "/api/templates"
        }
        
        endpoint = tool_mappings.get(tool_name)
        if not endpoint:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Make Klaviyo API request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://a.klaviyo.com{endpoint}",
                headers={
                    "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
                    "Accept": "application/json"
                },
                params=parameters
            )
            response.raise_for_status()
            return response.json()
    
    async def _start_mcp_process(self) -> subprocess.Popen:
        """Start MCP server process"""
        klaviyo_key = self.api_keys.get("klaviyo")
        if not klaviyo_key:
            raise ValueError("Klaviyo API key not configured")
        
        # Start MCP server using uvx
        env = os.environ.copy()
        env["PRIVATE_API_KEY"] = klaviyo_key
        env["READ_ONLY"] = "true" if self.client_config.read_only else "false"
        
        process = subprocess.Popen(
            ["uvx", "klaviyo-mcp-server@latest"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        return process
    
    async def _send_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to MCP server and get response"""
        if not self.mcp_process:
            raise ValueError("MCP process not started")
        
        # Send request
        request_str = json.dumps(request) + "\n"
        self.mcp_process.stdin.write(request_str)
        self.mcp_process.stdin.flush()
        
        # Read response
        response_line = self.mcp_process.stdout.readline()
        if not response_line:
            raise ValueError("No response from MCP server")
        
        return json.loads(response_line)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the provider"""
        if self.provider == "claude":
            # Test MCP server
            process = await self._start_mcp_process()
            request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": "test"
            }
            response = await self._send_mcp_request(request)
            process.terminate()
            return {"tools": response.get("result", [])}
            
        elif self.provider == "openai":
            # Test OpenAI API
            response = await asyncio.to_thread(
                self.openai_client.models.list
            )
            return {"models": [m.id for m in response.data]}
            
        elif self.provider == "gemini":
            # Test Gemini API
            models = await asyncio.to_thread(
                genai.list_models
            )
            return {"models": [m.name for m in models]}
        
        return {}


# Singleton instance
_mcp_service = None

def get_mcp_service() -> MCPServiceManager:
    """Get singleton instance of MCPServiceManager"""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MCPServiceManager()
    return _mcp_service