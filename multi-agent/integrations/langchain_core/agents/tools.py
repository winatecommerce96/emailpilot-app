"""
Tools for agents - both native SDK and MCP-backed.

Provides read-only tools for data access and safe operations.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import httpx

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from ..config import LangChainConfig, get_config
from ..deps import get_firestore_client, get_cache
# Will import Enhanced MCP adapter when it exists
try:
    from ..adapters.enhanced_mcp_adapter import get_enhanced_tools_for_agent, get_enhanced_mcp_adapter
    ENHANCED_MCP_AVAILABLE = True
except ImportError:
    ENHANCED_MCP_AVAILABLE = False
    logger.warning("Enhanced MCP adapter not available")


# Tool input schemas using Pydantic v1 for LangChain compatibility
class FirestoreInput(BaseModel):
    """Input for Firestore read-only tool."""
    collection: str = Field(description="Collection name")
    document_id: Optional[str] = Field(default=None, description="Document ID (optional)")
    max_fields: int = Field(default=10, description="Maximum fields to return")


class HTTPInput(BaseModel):
    """Input for HTTP GET tool."""
    url: str = Field(description="URL to fetch (must be allowlisted)")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Optional headers")


class CacheGetInput(BaseModel):
    """Input for cache get tool."""
    key: str = Field(description="Cache key")


class CacheSetInput(BaseModel):
    """Input for cache set tool."""
    key: str = Field(description="Cache key")
    value: Any = Field(description="Value to cache")
    ttl_seconds: int = Field(default=300, description="TTL in seconds")


class MCPToolInput(BaseModel):
    """Input for MCP tool calls."""
    endpoint: str = Field(description="MCP endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")
    body: Optional[Dict[str, Any]] = Field(default=None, description="Request body")


# Native tools
@tool("firestore_ro_get", args_schema=FirestoreInput, return_direct=False)
def firestore_ro_get(
    collection: str,
    document_id: Optional[str] = None,
    max_fields: int = 10
) -> Dict[str, Any]:
    """
    Read-only Firestore access.
    
    Retrieves documents or collections from Firestore.
    Limited to read operations only.
    """
    try:
        client = get_firestore_client()
        
        if not client:
            return {
                "error": "Firestore client not available",
                "data": None
            }
        
        if document_id:
            # Get specific document
            doc_ref = client.collection(collection).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                
                # Limit fields if too many
                if len(data) > max_fields:
                    data = dict(list(data.items())[:max_fields])
                    data["_truncated"] = True
                
                return {
                    "success": True,
                    "data": data,
                    "document_id": document_id,
                    "collection": collection
                }
            else:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found in {collection}",
                    "data": None
                }
        
        else:
            # List collection documents (limited)
            docs = client.collection(collection).limit(10).get()
            
            results = []
            for doc in docs:
                doc_data = doc.to_dict()
                
                # Limit fields per document
                if len(doc_data) > max_fields:
                    doc_data = dict(list(doc_data.items())[:max_fields])
                    doc_data["_truncated"] = True
                
                results.append({
                    "id": doc.id,
                    "data": doc_data
                })
            
            return {
                "success": True,
                "collection": collection,
                "count": len(results),
                "documents": results
            }
    
    except Exception as e:
        logger.error(f"Firestore read error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


@tool("http_get_json", args_schema=HTTPInput, return_direct=False)
def http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Fetch JSON data from allowlisted URLs.
    
    Only allows GET requests to pre-approved domains.
    """
    # URL allowlist
    ALLOWED_DOMAINS = [
        "api.klaviyo.com",
        "localhost",
        "127.0.0.1",
        "jsonplaceholder.typicode.com"  # For testing
    ]
    
    try:
        # Check if URL is allowed
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if not any(domain in parsed.netloc for domain in ALLOWED_DOMAINS):
            return {
                "success": False,
                "error": f"Domain {parsed.netloc} not in allowlist",
                "data": None
            }
        
        # Make request
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json(),
                "url": url
            }
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }
    except Exception as e:
        logger.error(f"HTTP tool error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


@tool("simple_cache_get", args_schema=CacheGetInput, return_direct=False)
def simple_cache_get(key: str) -> Any:
    """
    Get value from in-process cache.
    
    Returns cached value or None if not found.
    """
    cache = get_cache()
    
    if key in cache:
        entry = cache[key]
        
        # Check TTL
        if "expires_at" in entry:
            if datetime.utcnow().timestamp() > entry["expires_at"]:
                # Expired
                del cache[key]
                return None
        
        return entry.get("value")
    
    return None


@tool("simple_cache_set", args_schema=CacheSetInput, return_direct=False)
def simple_cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = 300
) -> bool:
    """
    Set value in in-process cache with TTL.
    
    Returns True if successful.
    """
    cache = get_cache()
    
    cache[key] = {
        "value": value,
        "expires_at": datetime.utcnow().timestamp() + ttl_seconds,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return True


def create_mcp_tool(
    name: str,
    description: str,
    endpoint: str,
    method: str = "GET",
    config: Optional[LangChainConfig] = None
) -> StructuredTool:
    """
    Create an MCP-backed tool.
    
    Args:
        name: Tool name
        description: Tool description
        endpoint: MCP endpoint
        method: HTTP method
        config: Configuration
    
    Returns:
        StructuredTool instance
    """
    if config is None:
        config = get_config()
    
    def mcp_caller(
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call MCP endpoint."""
        try:
            url = f"{config.mcp_base_url}/{endpoint}"
            
            with httpx.Client(timeout=config.mcp_timeout_seconds) as client:
                if method == "GET":
                    response = client.get(url, params=params)
                elif method == "POST":
                    response = client.post(url, json=body, params=params)
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported method: {method}"
                    }
                
                response.raise_for_status()
                
                return {
                    "success": True,
                    "data": response.json(),
                    "endpoint": endpoint
                }
        
        except httpx.HTTPError as e:
            logger.error(f"MCP call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
        except Exception as e:
            logger.error(f"MCP tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
    
    return StructuredTool.from_function(
        func=mcp_caller,
        name=name,
        description=description
    )


def get_native_tools() -> List[Any]:
    """
    Get list of native SDK tools.
    
    Returns:
        List of tool instances
    """
    return [
        firestore_ro_get,
        http_get_json,
        simple_cache_get,
        simple_cache_set
    ]


def get_mcp_tools(config: Optional[LangChainConfig] = None) -> List[Any]:
    """
    Get list of MCP-backed tools.
    
    Args:
        config: Configuration
    
    Returns:
        List of tool instances
    """
    if config is None:
        config = get_config()
    
    tools = []
    
    # Klaviyo fetch tool
    tools.append(create_mcp_tool(
        name="klaviyo_fetch",
        description="Fetch data from Klaviyo API via MCP (read-only)",
        endpoint="klaviyo/data",
        method="GET",
        config=config
    ))
    
    # Enrichment job status tool
    tools.append(create_mcp_tool(
        name="enrichment_job_status",
        description="Check status of enrichment job via MCP",
        endpoint="enrichment/status",
        method="GET",
        config=config
    ))
    
    # Campaign insights tool
    tools.append(create_mcp_tool(
        name="campaign_insights",
        description="Get campaign insights via MCP",
        endpoint="campaigns/insights",
        method="POST",
        config=config
    ))
    
    return tools


def get_all_tools(config: Optional[LangChainConfig] = None, agent_name: str = None, client_id: str = None) -> List[Any]:
    """
    Get all available tools (native + MCP + Enhanced MCP).
    
    Args:
        config: Configuration
        agent_name: Name of agent requesting tools
        client_id: Default client ID for Klaviyo
    
    Returns:
        List of all tool instances
    """
    native = get_native_tools()
    mcp = get_mcp_tools(config)
    
    # Add Enhanced MCP tools if available
    enhanced_tools = []
    if ENHANCED_MCP_AVAILABLE:
        try:
            if agent_name:
                enhanced_tools = get_enhanced_tools_for_agent(agent_name, client_id)
            else:
                adapter = get_enhanced_mcp_adapter()
                enhanced_tools = adapter.get_all_enhanced_tools(client_id)
        except Exception as e:
            logger.error(f"Failed to get Enhanced MCP tools: {e}")
    
    combined = native + mcp + enhanced_tools
    
    logger.info(f"Total tools available: {len(combined)} "
                f"(Native: {len(native)}, MCP: {len(mcp)}, "
                f"Enhanced MCP: {len(enhanced_tools)})")
    
    return combined


def get_enhanced_tools_only(agent_name: str = None, client_id: str = None) -> List[Any]:
    """
    Get only Enhanced MCP tools.
    
    Args:
        agent_name: Name of agent requesting tools
        client_id: Default client ID for Klaviyo
    
    Returns:
        List of Enhanced MCP tool instances
    """
    if not ENHANCED_MCP_AVAILABLE:
        logger.warning("Enhanced MCP not available")
        return []
    
    try:
        if agent_name:
            return get_enhanced_tools_for_agent(agent_name, client_id)
        else:
            adapter = get_enhanced_mcp_adapter()
            return adapter.get_all_enhanced_tools(client_id)
    except Exception as e:
        logger.error(f"Failed to get Enhanced MCP tools: {e}")
        return []