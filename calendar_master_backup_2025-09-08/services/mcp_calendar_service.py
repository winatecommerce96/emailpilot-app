"""
MCP Calendar Service - Robust MCP integration for calendar automation
Implements failover, retry logic, and standardized data fetching
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPConnectionResult:
    """Result of MCP connection attempt"""
    success: bool
    mcp_name: str
    auth_context: Dict[str, Any]
    error: Optional[str] = None
    response_time_ms: Optional[float] = None

@dataclass
class MCPDataResult:
    """Result of MCP data fetch"""
    success: bool
    data: List[Dict[str, Any]]
    source_mcp: str
    normalization_map: Dict[str, str]
    error: Optional[str] = None
    fetch_time_ms: Optional[float] = None

class MCPCalendarService:
    """Enhanced MCP service for calendar automation with robust failover"""
    
    def __init__(self, secret_manager_service):
        self.secret_manager = secret_manager_service
        self.mcp_configs = {
            "klaviyo_mcp": {
                "base_url": "http://localhost:8090",
                "priority": 1,
                "endpoints": {
                    "campaigns": "/campaigns",
                    "metrics": "/metrics",
                    "health": "/health"
                },
                "timeout": 30,
                "retry_count": 3
            },
            "openapi_mcp": {
                "base_url": "http://localhost:8091/mcp/openapi",
                "priority": 2,
                "endpoints": {
                    "campaigns": "/klaviyo/campaigns",
                    "metrics": "/klaviyo/metrics",
                    "health": "/health"
                },
                "timeout": 45,
                "retry_count": 2
            },
            "firestore_mcp": {
                "base_url": "http://localhost:8092/mcp/firestore",
                "priority": 3,
                "endpoints": {
                    "campaigns": "/proxy/klaviyo/campaigns",
                    "metrics": "/proxy/klaviyo/metrics",
                    "health": "/health"
                },
                "timeout": 60,
                "retry_count": 1
            }
        }
        
        # Field normalization mappings for different MCPs
        self.field_mappings = {
            "klaviyo_mcp": {
                "campaign_id": "id",
                "campaign_name": "name",
                "send_datetime": "send_time",
                "sends": "sent_count",
                "delivered": "delivered_count",
                "open_rate": "open_rate",
                "click_rate": "click_rate",
                "placed_order_count": "conversions",
                "placed_order_revenue": "revenue",
                "revenue_per_recipient": "rpr",
                "unsubscribes": "unsubscribe_count",
                "spam_complaints": "spam_count",
                "channel": "type"
            },
            "openapi_mcp": {
                "campaign_id": "campaign_id",
                "campaign_name": "subject",
                "send_datetime": "send_timestamp",
                "sends": "recipients_count",
                "delivered": "delivered_count",
                "open_rate": "unique_open_rate",
                "click_rate": "unique_click_rate",
                "placed_order_count": "placed_order_count",
                "placed_order_revenue": "placed_order_value",
                "revenue_per_recipient": "revenue_per_recipient",
                "unsubscribes": "unsubscribes",
                "spam_complaints": "spam_complaints",
                "channel": "channel"
            },
            "firestore_mcp": {
                "campaign_id": "id",
                "campaign_name": "name",
                "send_datetime": "sent_at",
                "sends": "total_sent",
                "delivered": "total_delivered",
                "open_rate": "open_rate_pct",
                "click_rate": "click_rate_pct",
                "placed_order_count": "orders",
                "placed_order_revenue": "total_revenue",
                "revenue_per_recipient": "avg_revenue",
                "unsubscribes": "unsubs",
                "spam_complaints": "complaints",
                "channel": "message_type"
            }
        }
    
    async def select_mcp_with_failover(self, klaviyo_account_id: str) -> MCPConnectionResult:
        """
        Select best available MCP with exponential backoff failover
        Tests each MCP in priority order until one succeeds
        """
        # Sort MCPs by priority
        sorted_mcps = sorted(
            self.mcp_configs.items(),
            key=lambda x: x[1]["priority"]
        )
        
        connection_attempts = []
        
        for mcp_name, config in sorted_mcps:
            logger.info(f"Attempting connection to {mcp_name}")
            
            try:
                result = await self._test_mcp_connection(mcp_name, config, klaviyo_account_id)
                connection_attempts.append(result)
                
                if result.success:
                    logger.info(f"Successfully connected to {mcp_name}")
                    return result
                
                # Exponential backoff before trying next MCP
                backoff_delay = 0.5 * (2 ** (config["priority"] - 1))
                logger.warning(f"MCP {mcp_name} failed, waiting {backoff_delay}s before next attempt")
                await asyncio.sleep(backoff_delay)
                
            except Exception as e:
                logger.error(f"Unexpected error testing {mcp_name}: {e}")
                connection_attempts.append(MCPConnectionResult(
                    success=False,
                    mcp_name=mcp_name,
                    auth_context={},
                    error=str(e)
                ))
                continue
        
        # All MCPs failed
        errors = [attempt.error for attempt in connection_attempts if attempt.error]
        combined_error = "; ".join(errors)
        
        return MCPConnectionResult(
            success=False,
            mcp_name="none",
            auth_context={},
            error=f"All MCP services failed: {combined_error}"
        )
    
    async def _test_mcp_connection(self, mcp_name: str, config: Dict[str, Any], 
                                  klaviyo_account_id: str) -> MCPConnectionResult:
        """Test individual MCP connection with retries"""
        start_time = datetime.utcnow()
        
        # Get authentication context
        auth_context = await self._get_auth_context(mcp_name, klaviyo_account_id)
        
        # Test health endpoint
        health_url = f"{config['base_url']}{config['endpoints']['health']}"
        
        for attempt in range(config["retry_count"]):
            try:
                async with httpx.AsyncClient(timeout=config["timeout"]) as client:
                    headers = await self._build_auth_headers(mcp_name, auth_context)
                    
                    response = await client.get(health_url, headers=headers)
                    
                    if response.status_code == 200:
                        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        return MCPConnectionResult(
                            success=True,
                            mcp_name=mcp_name,
                            auth_context=auth_context,
                            response_time_ms=response_time
                        )
                    elif response.status_code == 429:
                        # Rate limited, implement jitter and retry
                        jitter = 0.1 * attempt
                        await asyncio.sleep(1 + jitter)
                        continue
                    else:
                        logger.warning(f"{mcp_name} health check failed: {response.status_code}")
                        
            except httpx.TimeoutException:
                logger.warning(f"{mcp_name} health check timed out (attempt {attempt + 1})")
                if attempt < config["retry_count"] - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
            except Exception as e:
                logger.warning(f"{mcp_name} health check error: {e}")
                break
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return MCPConnectionResult(
            success=False,
            mcp_name=mcp_name,
            auth_context=auth_context,
            error=f"Connection failed after {config['retry_count']} attempts",
            response_time_ms=response_time
        )
    
    async def fetch_campaign_data(self, mcp_name: str, auth_context: Dict[str, Any],
                                 time_window: Dict[str, Any], klaviyo_account_id: str) -> MCPDataResult:
        """
        Fetch campaign data from selected MCP for specific time window
        Implements robust pagination and rate limit handling
        """
        start_time = datetime.utcnow()
        
        try:
            config = self.mcp_configs[mcp_name]
            
            # Build request parameters
            params = await self._build_time_window_params(time_window, klaviyo_account_id)
            
            # Fetch data with pagination
            all_data = []
            page = 1
            has_more = True
            
            while has_more and page <= 10:  # Safety limit
                page_data = await self._fetch_page(
                    mcp_name, config, auth_context, params, page
                )
                
                if page_data:
                    all_data.extend(page_data)
                    page += 1
                    
                    # Check for pagination indicators
                    has_more = len(page_data) >= 50  # Assume 50 is page size
                else:
                    has_more = False
                
                # Rate limiting courtesy pause
                if page > 1:
                    await asyncio.sleep(0.2)
            
            # Normalize data
            normalized_data, normalization_map = await self._normalize_data(mcp_name, all_data)
            
            fetch_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return MCPDataResult(
                success=True,
                data=normalized_data,
                source_mcp=mcp_name,
                normalization_map=normalization_map,
                fetch_time_ms=fetch_time
            )
            
        except Exception as e:
            logger.error(f"Data fetch from {mcp_name} failed: {e}")
            fetch_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return MCPDataResult(
                success=False,
                data=[],
                source_mcp=mcp_name,
                normalization_map={},
                error=str(e),
                fetch_time_ms=fetch_time
            )
    
    async def _fetch_page(self, mcp_name: str, config: Dict[str, Any], 
                         auth_context: Dict[str, Any], params: Dict[str, Any], 
                         page: int) -> List[Dict[str, Any]]:
        """Fetch single page of data from MCP"""
        campaigns_url = f"{config['base_url']}{config['endpoints']['campaigns']}"
        
        # Add pagination parameters
        page_params = {**params, "page": page, "limit": 50}
        
        headers = await self._build_auth_headers(mcp_name, auth_context)
        
        for attempt in range(config["retry_count"]):
            try:
                async with httpx.AsyncClient(timeout=config["timeout"]) as client:
                    response = await client.get(campaigns_url, params=page_params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different response structures
                        if isinstance(data, dict):
                            return data.get("campaigns", data.get("data", []))
                        elif isinstance(data, list):
                            return data
                        else:
                            logger.warning(f"Unexpected response format from {mcp_name}")
                            return []
                    
                    elif response.status_code == 202:
                        # Processing request, wait and retry
                        logger.info(f"{mcp_name} returned 202, waiting for processing")
                        await asyncio.sleep(2)
                        continue
                    
                    elif response.status_code == 429:
                        # Rate limited, implement exponential backoff with jitter
                        retry_after = int(response.headers.get("Retry-After", 5))
                        jitter = 0.1 * attempt
                        await asyncio.sleep(retry_after + jitter)
                        continue
                        
                    else:
                        logger.warning(f"{mcp_name} returned {response.status_code}: {response.text}")
                        return []
                        
            except httpx.TimeoutException:
                logger.warning(f"{mcp_name} request timed out (attempt {attempt + 1})")
                if attempt < config["retry_count"] - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    
            except Exception as e:
                logger.error(f"{mcp_name} request error: {e}")
                break
        
        return []
    
    async def _build_time_window_params(self, time_window: Dict[str, Any], 
                                       klaviyo_account_id: str) -> Dict[str, Any]:
        """Build query parameters for time window"""
        params = {
            "klaviyo_account_id": klaviyo_account_id
        }
        
        if "year" in time_window and "month" in time_window:
            # Monthly window
            year = time_window["year"]
            month = time_window["month"]
            
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            params.update({
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            })
            
        elif "days_back" in time_window:
            # Rolling window
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_window["days_back"])
            
            params.update({
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            })
        
        return params
    
    async def _normalize_data(self, mcp_name: str, raw_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Normalize field names using MCP-specific mappings"""
        field_mapping = self.field_mappings.get(mcp_name, {})
        normalized_data = []
        normalization_map = {}
        
        for record in raw_data:
            normalized_record = {}
            
            # Map known fields
            for standard_field, source_field in field_mapping.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Type conversions
                    if standard_field in ["open_rate", "click_rate"] and isinstance(value, (int, float)):
                        # Convert to decimal if needed
                        if value > 1:
                            value = value / 100.0
                    
                    normalized_record[standard_field] = value
                    normalization_map[standard_field] = source_field
                else:
                    # Set defaults for missing required fields
                    defaults = {
                        "sends": 0,
                        "delivered": 0,
                        "open_rate": 0.0,
                        "click_rate": 0.0,
                        "placed_order_count": 0,
                        "placed_order_revenue": 0.0,
                        "revenue_per_recipient": 0.0,
                        "unsubscribes": 0,
                        "spam_complaints": 0,
                        "channel": "email"
                    }
                    
                    if standard_field in defaults:
                        normalized_record[standard_field] = defaults[standard_field]
            
            # Calculate derived fields
            if normalized_record.get("sends", 0) > 0 and normalized_record.get("placed_order_revenue", 0) > 0:
                normalized_record["revenue_per_recipient"] = (
                    normalized_record["placed_order_revenue"] / normalized_record["sends"]
                )
            
            # Copy unmapped fields as-is
            for field, value in record.items():
                if field not in field_mapping.values():
                    normalized_record[field] = value
            
            normalized_data.append(normalized_record)
        
        return normalized_data, normalization_map
    
    async def _get_auth_context(self, mcp_name: str, klaviyo_account_id: str) -> Dict[str, Any]:
        """Get authentication context for MCP"""
        try:
            # Get Klaviyo API key from Secret Manager
            klaviyo_key = await self.secret_manager.get_klaviyo_key_for_account(klaviyo_account_id)
            
            return {
                "klaviyo_account_id": klaviyo_account_id,
                "klaviyo_api_key": klaviyo_key,
                "authenticated": True
            }
            
        except Exception as e:
            logger.warning(f"Failed to get auth context for {mcp_name}: {e}")
            return {
                "klaviyo_account_id": klaviyo_account_id,
                "authenticated": False,
                "error": str(e)
            }
    
    async def _build_auth_headers(self, mcp_name: str, auth_context: Dict[str, Any]) -> Dict[str, str]:
        """Build authentication headers for MCP request"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EmailPilot-Calendar-Automation/1.0"
        }
        
        if auth_context.get("authenticated") and auth_context.get("klaviyo_api_key"):
            headers["Authorization"] = f"Klaviyo-API-Key {auth_context['klaviyo_api_key']}"
            headers["X-Klaviyo-Account-ID"] = auth_context["klaviyo_account_id"]
        
        # MCP-specific headers
        if mcp_name == "openapi_mcp":
            headers["X-MCP-Type"] = "openapi"
        elif mcp_name == "firestore_mcp":
            headers["X-MCP-Type"] = "firestore-proxy"
        
        return headers

    async def introspect_firestore_schema(self, db) -> Dict[str, Any]:
        """Introspect existing Firestore schema for compatibility"""
        schema_info = {
            "calendar_import_logs": {"exists": False, "sample_fields": {}},
            "calendar_events": {"exists": False, "sample_fields": {}},
            "version": "unknown"
        }
        
        try:
            # Check calendar_import_logs
            logs_ref = db.collection('calendar_import_logs').limit(1)
            logs_docs = list(logs_ref.stream())
            
            if logs_docs:
                schema_info["calendar_import_logs"]["exists"] = True
                sample_doc = logs_docs[0].to_dict()
                schema_info["calendar_import_logs"]["sample_fields"] = {
                    k: type(v).__name__ for k, v in sample_doc.items()
                }
            
            # Check calendar_events
            events_ref = db.collection('calendar_events').limit(1)
            events_docs = list(events_ref.stream())
            
            if events_docs:
                schema_info["calendar_events"]["exists"] = True
                sample_doc = events_docs[0].to_dict()
                schema_info["calendar_events"]["sample_fields"] = {
                    k: type(v).__name__ for k, v in sample_doc.items()
                }
            
            logger.info(f"Firestore schema introspection complete: {schema_info}")
            
        except Exception as e:
            logger.error(f"Schema introspection failed: {e}")
        
        return schema_info