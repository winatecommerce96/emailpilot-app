"""
Enhanced MCP Service with multi-model support.

This module provides two primary entry points:
- MCPServiceManager: manages provider-backed MCP execution for tools.
- MCPService: a lightweight compatibility shim used by existing APIs
  that only need to "check connection" semantics.

Notes:
- The project primarily uses Firestore; avoid SQLAlchemy here.
- Secrets are fetched from Google Secret Manager using a stable
  naming convention: mcp-{client_id}-{provider}-key.
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional
from types import SimpleNamespace
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

# Import AI Orchestrator as primary interface
try:
    from app.core.ai_orchestrator import get_ai_orchestrator, ai_complete
    AI_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    AI_ORCHESTRATOR_AVAILABLE = False
    logger.warning("AI Orchestrator not available, using direct SDK imports")

# Fallback to direct SDK imports if orchestrator not available
if not AI_ORCHESTRATOR_AVAILABLE:
    import openai
    import google.generativeai as genai
    from anthropic import Anthropic
else:
    # Create dummy imports for type hints
    openai = None
    genai = None
    Anthropic = None
from fastapi import Depends
import httpx

from app.deps import get_secret_manager_service, get_db
from app.services.secret_manager import SecretManagerService

logger = logging.getLogger(__name__)


class MCPServiceManager:
    """Manages MCP connections for multiple AI providers"""
    
    def __init__(self, secret_manager: SecretManagerService):
        self.secret_manager = secret_manager
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
                    "gpt-4o": {
                        "name": "gpt-4o",
                        "display_name": "GPT-4o (Latest)",
                        "max_tokens": 16384,
                        "context_window": 128000,
                        "input_cost_per_1k": 0.0025,
                        "output_cost_per_1k": 0.01
                    },
                    "gpt-4o-mini": {
                        "name": "gpt-4o-mini",
                        "display_name": "GPT-4o Mini",
                        "max_tokens": 16384,
                        "context_window": 128000,
                        "input_cost_per_1k": 0.00015,
                        "output_cost_per_1k": 0.0006
                    },
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
                    "gemini-2.0-flash-exp": {
                        "name": "gemini-2.0-flash-exp",
                        "display_name": "Gemini 2.0 Flash (Experimental)",
                        "max_tokens": 8192,
                        "context_window": 1048576,
                        "input_cost_per_1k": 0.0,
                        "output_cost_per_1k": 0.0
                    },
                    "gemini-1.5-pro": {
                        "name": "gemini-1.5-pro-002",
                        "display_name": "Gemini 1.5 Pro (Latest)",
                        "max_tokens": 8192,
                        "context_window": 2097152,
                        "input_cost_per_1k": 0.00125,
                        "output_cost_per_1k": 0.005
                    },
                    "gemini-1.5-flash": {
                        "name": "gemini-1.5-flash-002",
                        "display_name": "Gemini 1.5 Flash",
                        "max_tokens": 8192,
                        "context_window": 1048576,
                        "input_cost_per_1k": 0.000075,
                        "output_cost_per_1k": 0.0003
                    },
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
    
    async def get_mcp_instance(self, client_id: str, db = Depends(get_db), provider: str = None) -> 'MCPInstance':
        """Get or create an MCP instance for a client (Firestore-backed)."""
        cache_key = f"{client_id}:{provider or 'default'}"
        
        if cache_key not in self.mcp_instances:
            # Load client meta from Firestore
            client_doc = db.collection("clients").document(client_id).get()
            if not client_doc.exists:
                raise ValueError(f"Client {client_id} not found")

            client_data = client_doc.to_dict() or {}

            # Optional per-client MCP config
            mcp_doc = db.collection("mcp_clients").document(client_id).get()
            mcp_data = mcp_doc.to_dict() if mcp_doc.exists else {}

            # Minimal client config used by this service
            client = SimpleNamespace(
                id=client_id,
                name=client_data.get("name", client_id),
                read_only=bool(mcp_data.get("read_only", True)),
                default_model_provider=mcp_data.get("default_model_provider", "claude"),
            )

            # Load API keys from Secret Manager (best-effort)
            api_keys = self._load_api_keys(client_id)

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
        db = Depends(get_db),
        provider: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """Execute an MCP tool using specified provider"""
        start_time = time.time()
        
        try:
            # Get MCP instance
            instance = await self.get_mcp_instance(client_id, db, provider)
            
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
        """Track usage metrics in Firestore (best-effort; non-blocking)."""
        try:
            db = get_db()

            # Calculate rough cost
            model_config = self.model_configs.get(provider, {}).get("models", {}).get(model, {})
            input_cost = (request_tokens / 1000) * model_config.get("input_cost_per_1k", 0)
            output_cost = (response_tokens / 1000) * model_config.get("output_cost_per_1k", 0)
            total_cost = input_cost + output_cost

            usage_doc = {
                "client_id": client_id,
                "model_provider": provider,
                "model_name": model,
                "tool_name": tool_name,
                "request_tokens": request_tokens,
                "response_tokens": response_tokens,
                "total_tokens": request_tokens + response_tokens,
                "latency_ms": latency_ms,
                "estimated_cost": total_cost,
                "request_id": f"{client_id}:{provider}:{tool_name}:{datetime.now().isoformat()}",
                "status": status,
                "error_message": error_message,
                "completed_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat(),
            }

            db.collection("clients").document(client_id).collection("mcp_usage").add(usage_doc)
        except Exception as e:
            # Do not raise; logging only
            logging.getLogger(__name__).warning(f"Failed to track MCP usage: {e}")
    
    async def test_connection(self, client_id: str, provider: str, db = Depends(get_db)) -> Dict[str, Any]:
        """Test MCP connection for a specific provider"""
        try:
            instance = await self.get_mcp_instance(client_id, db, provider)
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
        client_config,
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
        # Try to use AI Orchestrator first
        if AI_ORCHESTRATOR_AVAILABLE:
            self.orchestrator = get_ai_orchestrator()
            self.use_orchestrator = True
            logger.info(f"Using AI Orchestrator for provider {self.provider}")
        else:
            self.orchestrator = None
            self.use_orchestrator = False
            
            # Fallback to direct SDK initialization
            if self.provider == "claude":
                # Use existing MCP server process
                self.mcp_process = None
                api_key = self.api_keys.get("klaviyo")  # Klaviyo key for MCP server
                if api_key and Anthropic:
                    self.anthropic_client = Anthropic(api_key=api_key)
                else:
                    self.anthropic_client = None
                
            elif self.provider == "openai":
                api_key = self.api_keys.get("openai")
                if not api_key:
                    raise ValueError("OpenAI API key not configured")
                if openai:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                
            elif self.provider == "gemini":
                api_key = self.api_keys.get("gemini")
                if not api_key:
                    raise ValueError("Gemini API key not configured")
                if genai:
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
        
        # Use orchestrator if available
        if self.use_orchestrator:
            return await self._execute_with_orchestrator(tool_name, parameters, model)
        
        # Fallback to direct provider execution
        if self.provider == "claude":
            return await self._execute_claude_mcp(tool_name, parameters, model)
        elif self.provider == "openai":
            return await self._execute_openai_tool(tool_name, parameters, model)
        elif self.provider == "gemini":
            return await self._execute_gemini_tool(tool_name, parameters, model)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def _execute_with_orchestrator(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        model: str
    ) -> Dict[str, Any]:
        """Execute tool using AI Orchestrator"""
        # Build prompt for tool execution
        prompt = f"""Execute the following Klaviyo MCP tool:

Tool: {tool_name}
Parameters: {json.dumps(parameters, indent=2)}

Provide a structured response with the tool execution result."""
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # Use orchestrator for completion
            response = await ai_complete(
                messages=messages,
                provider=self.provider,
                model=model,
                temperature=0.3,  # Lower temperature for tool execution
                max_tokens=2000
            )
            
            # Parse response and execute actual tool
            result = await self._execute_klaviyo_tool(tool_name, parameters)
            
            return {
                "result": result,
                "ai_response": response,
                "request_tokens": 0,  # Orchestrator handles token tracking
                "response_tokens": 0
            }
        except Exception as e:
            logger.error(f"Orchestrator execution failed: {e}")
            # Fall back to direct execution if orchestrator fails
            if self.provider == "claude":
                return await self._execute_claude_mcp(tool_name, parameters, model)
            elif self.provider == "openai":
                return await self._execute_openai_tool(tool_name, parameters, model)
            elif self.provider == "gemini":
                return await self._execute_gemini_tool(tool_name, parameters, model)
            else:
                raise
    
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
        result = await self._execute_klaviyo_tool(tool_name, json.loads(function_call.get("arguments", "{{}}")))
        
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


    def _load_api_keys(self, client_id: str) -> Dict[str, Optional[str]]:
        """Load provider API keys from Secret Manager by convention.

        Secret IDs:
          - mcp-{client_id}-klaviyo-key
          - mcp-{client_id}-openai-key
          - mcp-{client_id}-gemini-key
        """
        keys: Dict[str, Optional[str]] = {"klaviyo": None, "openai": None, "gemini": None}
        try:
            keys["klaviyo"] = self.secret_manager.get_secret(f"mcp-{client_id}-klaviyo-key")
        except Exception:
            pass
        try:
            keys["openai"] = self.secret_manager.get_secret(f"mcp-{client_id}-openai-key")
        except Exception:
            pass
        try:
            keys["gemini"] = self.secret_manager.get_secret(f"mcp-{client_id}-gemini-key")
        except Exception:
            pass
        return keys


class MCPService:
    """Compatibility shim used by existing APIs.

    Currently supports a single method used by calendar_planning_ai:
    - check_client_connection(client_id) -> dict
    """

    def __init__(self, db=None):
        self.db = db or get_db()
        # Lazily initialize the manager with a real SecretManager
        self._manager: Optional[MCPServiceManager] = None

    def _get_manager(self) -> MCPServiceManager:
        if self._manager is None:
            secret_manager = get_secret_manager_service()
            self._manager = get_mcp_service(secret_manager)
        return self._manager

    async def check_client_connection(self, client_id: str) -> Dict[str, Any]:
        try:
            # Determine preferred provider from Firestore config
            provider = "claude"
            mcp_doc = self.db.collection("mcp_clients").document(client_id).get()
            if mcp_doc.exists:
                provider = (mcp_doc.to_dict() or {}).get("default_model_provider", "claude")

            mgr = self._get_manager()
            result = await mgr.test_connection(client_id, provider, db=self.db)
            return {"connected": bool(result.get("success")), **result}
        except Exception as e:
            logging.getLogger(__name__).error(f"MCP connection check failed for {client_id}: {e}")
            return {"connected": False, "success": False, "error": str(e)}


# Singleton instance
_mcp_service = None

def get_mcp_service(secret_manager: SecretManagerService = Depends(get_secret_manager_service)) -> MCPServiceManager:
    """Get singleton instance of MCPServiceManager"""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MCPServiceManager(secret_manager=secret_manager)
    return _mcp_service
