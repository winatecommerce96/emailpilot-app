"""
Tool definitions for LangChain agents.

Provides read-only tools for interacting with external services
including Klaviyo stub, Firestore, calendar data, and web fetching.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from langchain.tools import Tool, StructuredTool
from langchain_core.pydantic_v1 import BaseModel, Field

logger = logging.getLogger(__name__)


# Tool input schemas using Pydantic v1 for LangChain compatibility
class KlaviyoStubInput(BaseModel):
    """Input for Klaviyo stub tool."""
    endpoint: str = Field(description="API endpoint path (e.g., /metrics, /campaigns)")
    method: str = Field(default="GET", description="HTTP method (GET or POST)")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")
    
    
class FirestoreReadInput(BaseModel):
    """Input for Firestore read tool."""
    collection: str = Field(description="Collection name to read from")
    document_id: Optional[str] = Field(default=None, description="Specific document ID to read")
    limit: int = Field(default=10, description="Maximum number of documents to return")


class CalendarReadInput(BaseModel):
    """Input for calendar read tool."""
    month: Optional[str] = Field(default=None, description="Month to filter (YYYY-MM format)")
    campaign_type: Optional[str] = Field(default=None, description="Campaign type to filter")


class WebFetchInput(BaseModel):
    """Input for web fetch tool."""
    url: str = Field(description="URL to fetch (must be in allowlist)")


def http_klaviyo_stub(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Make HTTP request to Klaviyo stub/proxy endpoint.
    
    Args:
        endpoint: API endpoint path
        method: HTTP method (GET or POST only)
        params: Query parameters
        config: LangChainConfig instance
    
    Returns:
        JSON response or error message
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    try:
        import httpx
        
        # Ensure read-only (no mutations)
        if method not in ["GET", "POST"]:
            return {"error": f"Method {method} not allowed. Only GET and POST are permitted."}
        
        base_url = config.readonly_klaviyo_base_url
        url = f"{base_url}{endpoint}"
        
        logger.info(f"Calling Klaviyo stub: {method} {url}")
        
        with httpx.Client(timeout=10.0) as client:
            if method == "GET":
                response = client.get(url, params=params)
            else:  # POST
                response = client.post(url, json=params)
        
        response.raise_for_status()
        return response.json()
        
    except httpx.TimeoutException:
        return {"error": "Request timed out"}
    except httpx.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error calling Klaviyo stub: {e}")
        return {"error": str(e)}


def firestore_ro(
    collection: str,
    document_id: Optional[str] = None,
    limit: int = 10,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Read-only access to Firestore collections.
    
    Args:
        collection: Collection name
        document_id: Specific document ID (optional)
        limit: Maximum number of documents
        config: LangChainConfig instance
    
    Returns:
        Document data or collection list
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    try:
        from ..deps import get_firestore_client
        
        client = get_firestore_client(config)
        if client is None:
            return {"error": "Firestore client not available"}
        
        # Enforce read-only by only allowing safe collections
        safe_collections = [
            "clients", "campaigns", "calendar_events", "goals",
            "performance_metrics", "ma_artifacts", "ma_runs"
        ]
        
        if collection not in safe_collections:
            return {"error": f"Collection '{collection}' not in allowlist"}
        
        if document_id:
            # Read specific document
            doc_ref = client.collection(collection).document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data["_id"] = doc.id
                return {"document": data}
            else:
                return {"error": f"Document {document_id} not found"}
        else:
            # List documents (with limit)
            query = client.collection(collection).limit(min(limit, 50))
            docs = query.stream()
            
            results = []
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    data["_id"] = doc.id
                    results.append(data)
            
            return {"documents": results, "count": len(results)}
            
    except Exception as e:
        logger.error(f"Firestore read error: {e}")
        return {"error": str(e)}


def calendar_ro(
    month: Optional[str] = None,
    campaign_type: Optional[str] = None,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Read calendar data from static JSON file.
    
    Args:
        month: Month filter (YYYY-MM format)
        campaign_type: Campaign type filter
        config: LangChainConfig instance
    
    Returns:
        Calendar events matching filters
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    try:
        # Look for calendar JSON in data directory
        calendar_file = config.seed_docs_path.parent / "calendar_sample.json"
        
        if not calendar_file.exists():
            # Create sample calendar data
            sample_data = {
                "events": [
                    {
                        "id": "evt_001",
                        "date": "2024-10-15",
                        "campaign_type": "email",
                        "name": "October Newsletter",
                        "status": "completed",
                        "metrics": {"sent": 10000, "opens": 3500, "clicks": 750}
                    },
                    {
                        "id": "evt_002",
                        "date": "2024-10-20",
                        "campaign_type": "sms",
                        "name": "Flash Sale Alert",
                        "status": "scheduled",
                        "metrics": {}
                    },
                    {
                        "id": "evt_003",
                        "date": "2024-11-01",
                        "campaign_type": "email",
                        "name": "November Welcome",
                        "status": "draft",
                        "metrics": {}
                    }
                ]
            }
            
            calendar_file.parent.mkdir(parents=True, exist_ok=True)
            calendar_file.write_text(json.dumps(sample_data, indent=2))
            logger.info(f"Created sample calendar at {calendar_file}")
        
        # Load calendar data
        data = json.loads(calendar_file.read_text())
        events = data.get("events", [])
        
        # Apply filters
        if month:
            events = [e for e in events if e.get("date", "").startswith(month)]
        
        if campaign_type:
            events = [e for e in events if e.get("campaign_type") == campaign_type]
        
        return {
            "events": events,
            "count": len(events),
            "filters_applied": {
                "month": month,
                "campaign_type": campaign_type
            }
        }
        
    except Exception as e:
        logger.error(f"Calendar read error: {e}")
        return {"error": str(e)}


def web_fetch(url: str, config: Optional[Any] = None) -> Dict[str, Any]:
    """
    Fetch content from allowed web URLs.
    
    Args:
        url: URL to fetch
        config: LangChainConfig instance
    
    Returns:
        Fetched content or error
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    try:
        import httpx
        from urllib.parse import urlparse
        
        # URL allowlist
        allowed_domains = [
            "docs.klaviyo.com",
            "help.klaviyo.com",
            "developers.klaviyo.com",
            "emailpilot.ai",
            "github.com/klaviyo"
        ]
        
        parsed = urlparse(url)
        if not any(domain in parsed.netloc for domain in allowed_domains):
            return {"error": f"Domain {parsed.netloc} not in allowlist"}
        
        logger.info(f"Fetching URL: {url}")
        
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            # Return text content (truncated if too long)
            content = response.text
            if len(content) > 5000:
                content = content[:5000] + "\n... (truncated)"
            
            return {
                "url": str(response.url),
                "status_code": response.status_code,
                "content": content,
                "content_type": response.headers.get("content-type", "unknown")
            }
            
    except httpx.TimeoutException:
        return {"error": "Request timed out"}
    except httpx.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        logger.error(f"Web fetch error: {e}")
        return {"error": str(e)}


def get_agent_tools(config: Optional[Any] = None) -> List[Tool]:
    """
    Get all available tools for the agent.
    
    Args:
        config: LangChainConfig instance
    
    Returns:
        List of Tool instances
    """
    if config is None:
        from ..config import get_config
        config = get_config()
    
    tools = []
    
    # Klaviyo stub tool
    tools.append(StructuredTool.from_function(
        func=lambda endpoint, method="GET", params=None: http_klaviyo_stub(
            endpoint, method, params, config
        ),
        name="klaviyo_api",
        description="Query Klaviyo API stub for campaign and metric data",
        args_schema=KlaviyoStubInput
    ))
    
    # Firestore read-only tool
    tools.append(StructuredTool.from_function(
        func=lambda collection, document_id=None, limit=10: firestore_ro(
            collection, document_id, limit, config
        ),
        name="firestore_read",
        description="Read data from Firestore collections (read-only)",
        args_schema=FirestoreReadInput
    ))
    
    # Calendar read-only tool
    tools.append(StructuredTool.from_function(
        func=lambda month=None, campaign_type=None: calendar_ro(
            month, campaign_type, config
        ),
        name="calendar_read",
        description="Read calendar events and campaign schedules",
        args_schema=CalendarReadInput
    ))
    
    # Web fetch tool
    tools.append(StructuredTool.from_function(
        func=lambda url: web_fetch(url, config),
        name="web_fetch",
        description="Fetch content from allowed web URLs (Klaviyo docs, etc.)",
        args_schema=WebFetchInput
    ))
    
    logger.info(f"Loaded {len(tools)} tools for agent")
    return tools