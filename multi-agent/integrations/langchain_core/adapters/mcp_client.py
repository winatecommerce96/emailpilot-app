"""
Enhanced MCP (Model Context Protocol) client adapter.

Provides integration with EmailPilot's MCP services including:
- Klaviyo Revenue API (port 9090)
- Performance API (port 9091)
- Multi-Agent System (port 8090)
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import LangChainConfig, get_config

logger = logging.getLogger(__name__)

# MCP Server Configurations
MCP_SERVERS = {
    "klaviyo_revenue": {
        "name": "Klaviyo Revenue API",
        "port": 9090,
        "base_url": "http://localhost:9090",
        "health_endpoint": "/health"
    },
    "performance_api": {
        "name": "Performance API",
        "port": 9091,
        "base_url": "http://localhost:9091",
        "health_endpoint": "/health"
    },
    "multi_agent": {
        "name": "Multi-Agent System",
        "port": 8090,
        "base_url": "http://localhost:8090",
        "health_endpoint": "/health"
    }
}


@dataclass
class MCPResponse:
    """Structured MCP response."""
    success: bool
    data: Optional[Any]
    error: Optional[str]
    endpoint: str
    status_code: Optional[int]
    duration_ms: int
    metadata: Dict[str, Any]


@dataclass
class MCPError(Exception):
    """MCP client error."""
    endpoint: str
    status_code: Optional[int]
    message: str
    details: Optional[Dict[str, Any]]


class MCPClient:
    """Typed client for MCP endpoints."""
    
    def __init__(self, config: Optional[LangChainConfig] = None):
        """
        Initialize MCP client.
        
        Args:
            config: Configuration instance
        """
        self.config = config or get_config()
        self.base_url = self.config.mcp_base_url
        self.klaviyo_url = self.config.klaviyo_mcp_url
        self.timeout = self.config.mcp_timeout_seconds
        
        # HTTP client with retry
        self.client = httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": "LangChain-Core/1.0",
                "Content-Type": "application/json"
            }
        )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Make HTTP request to MCP endpoint.
        
        Args:
            method: HTTP method
            endpoint: Endpoint path
            params: Query parameters
            body: Request body
        
        Returns:
            MCPResponse
        
        Raises:
            MCPError on failure
        """
        url = f"{self.base_url}/{endpoint}"
        start_time = datetime.utcnow()
        
        try:
            if method == "GET":
                response = self.client.get(url, params=params)
            elif method == "POST":
                response = self.client.post(url, json=body, params=params)
            elif method == "PUT":
                response = self.client.put(url, json=body, params=params)
            elif method == "DELETE":
                response = self.client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Calculate duration
            duration_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Check status
            if response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                except:
                    pass
                
                raise MCPError(
                    endpoint=endpoint,
                    status_code=response.status_code,
                    message=f"MCP request failed with status {response.status_code}",
                    details=error_data
                )
            
            # Parse response
            try:
                data = response.json()
            except:
                data = response.text
            
            return MCPResponse(
                success=True,
                data=data,
                error=None,
                endpoint=endpoint,
                status_code=response.status_code,
                duration_ms=duration_ms,
                metadata={
                    "method": method,
                    "url": url
                }
            )
        
        except httpx.HTTPError as e:
            duration_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            logger.error(f"MCP HTTP error: {e}")
            
            return MCPResponse(
                success=False,
                data=None,
                error=str(e),
                endpoint=endpoint,
                status_code=None,
                duration_ms=duration_ms,
                metadata={
                    "method": method,
                    "url": url,
                    "error_type": "http_error"
                }
            )
        
        except Exception as e:
            duration_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            logger.error(f"MCP request error: {e}")
            
            return MCPResponse(
                success=False,
                data=None,
                error=str(e),
                endpoint=endpoint,
                status_code=None,
                duration_ms=duration_ms,
                metadata={
                    "method": method,
                    "url": url,
                    "error_type": "unknown"
                }
            )
    
    def healthcheck(self) -> bool:
        """
        Check if MCP service is healthy.
        
        Returns:
            True if healthy
        """
        try:
            response = self._request("GET", "health")
            return response.success and response.status_code == 200
        except:
            return False
    
    # Klaviyo endpoints
    
    def klaviyo_fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> MCPResponse:
        """
        Fetch data from Klaviyo via MCP.
        
        Args:
            endpoint: Klaviyo endpoint
            params: Query parameters
        
        Returns:
            MCPResponse
        """
        return self._request(
            "GET",
            f"klaviyo/{endpoint}",
            params=params
        )
    
    def klaviyo_campaigns(
        self,
        brand_id: str,
        month: Optional[str] = None,
        limit: int = 10
    ) -> MCPResponse:
        """
        Get Klaviyo campaigns.
        
        Args:
            brand_id: Brand identifier
            month: Optional month filter
            limit: Result limit
        
        Returns:
            MCPResponse
        """
        params = {
            "brand_id": brand_id,
            "limit": limit
        }
        if month:
            params["month"] = month
        
        return self.klaviyo_fetch("campaigns", params)
    
    def klaviyo_metrics(
        self,
        campaign_id: str,
        metrics: List[str]
    ) -> MCPResponse:
        """
        Get Klaviyo campaign metrics.
        
        Args:
            campaign_id: Campaign ID
            metrics: List of metric names
        
        Returns:
            MCPResponse
        """
        return self.klaviyo_fetch(
            f"campaigns/{campaign_id}/metrics",
            params={"metrics": ",".join(metrics)}
        )
    
    # Enrichment endpoints
    
    def enrichment_status(
        self,
        job_id: str
    ) -> MCPResponse:
        """
        Check enrichment job status.
        
        Args:
            job_id: Job identifier
        
        Returns:
            MCPResponse
        """
        return self._request(
            "GET",
            f"enrichment/jobs/{job_id}"
        )
    
    def enrichment_start(
        self,
        data_type: str,
        params: Dict[str, Any]
    ) -> MCPResponse:
        """
        Start enrichment job.
        
        Args:
            data_type: Type of data to enrich
            params: Enrichment parameters
        
        Returns:
            MCPResponse with job_id
        """
        return self._request(
            "POST",
            "enrichment/jobs",
            body={
                "data_type": data_type,
                "params": params
            }
        )
    
    # Campaign insights
    
    def campaign_insights(
        self,
        brand_id: str,
        month: str,
        insight_types: Optional[List[str]] = None
    ) -> MCPResponse:
        """
        Get campaign insights.
        
        Args:
            brand_id: Brand identifier
            month: Month for insights
            insight_types: Types of insights to generate
        
        Returns:
            MCPResponse
        """
        body = {
            "brand_id": brand_id,
            "month": month
        }
        
        if insight_types:
            body["insight_types"] = insight_types
        
        return self._request(
            "POST",
            "campaigns/insights",
            body=body
        )
    
    # Calendar operations
    
    def calendar_events(
        self,
        month: Optional[str] = None,
        brand_id: Optional[str] = None
    ) -> MCPResponse:
        """
        Get calendar events.
        
        Args:
            month: Optional month filter
            brand_id: Optional brand filter
        
        Returns:
            MCPResponse
        """
        params = {}
        if month:
            params["month"] = month
        if brand_id:
            params["brand_id"] = brand_id
        
        return self._request(
            "GET",
            "calendar/events",
            params=params
        )
    
    # Batch operations
    
    def batch_request(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[MCPResponse]:
        """
        Execute batch of MCP requests.
        
        Args:
            requests: List of request specifications
        
        Returns:
            List of MCPResponse objects
        """
        responses = []
        
        for req in requests:
            try:
                response = self._request(
                    method=req.get("method", "GET"),
                    endpoint=req["endpoint"],
                    params=req.get("params"),
                    body=req.get("body")
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Batch request failed: {e}")
                responses.append(MCPResponse(
                    success=False,
                    data=None,
                    error=str(e),
                    endpoint=req["endpoint"],
                    status_code=None,
                    duration_ms=0,
                    metadata={"batch": True}
                ))
        
        return responses