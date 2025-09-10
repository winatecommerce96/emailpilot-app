"""
Goals MCP Service - Fetches historical metrics from Klaviyo via Enhanced MCP Server
Supports multiple metric types for comprehensive goal tracking
"""

import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.services.client_key_resolver import ClientKeyResolver
from google.cloud import firestore

logger = logging.getLogger(__name__)

# MCP server configuration
ENHANCED_MCP_URL = "http://localhost:9095"
NL_MCP_URL = "http://localhost:8000/api/mcp/nl"

class GoalsMCPService:
    """
    Service for fetching historical metrics from Klaviyo via Enhanced MCP Server
    Supports revenue, open rate, click rate, bounce rate, and other metrics
    """
    
    def __init__(self, key_resolver: ClientKeyResolver, db: firestore.Client):
        self.key_resolver = key_resolver
        self.db = db
        self.enhanced_mcp_url = ENHANCED_MCP_URL
        self.nl_mcp_url = NL_MCP_URL
    
    async def fetch_historical_metrics(
        self, 
        client_id: str, 
        metric_types: List[str],
        timeframe: str = "last_12_months"
    ) -> Dict[str, Any]:
        """
        Fetch historical metrics for multiple metric types
        
        Args:
            client_id: Client identifier
            metric_types: List of metrics to fetch (revenue, open_rate, click_rate, etc.)
            timeframe: Time period to fetch (last_12_months, last_year, etc.)
        
        Returns:
            Dictionary with metric data organized by type
        """
        try:
            # Get API key for client
            api_key = await self.key_resolver.get_client_klaviyo_key(client_id)
            if not api_key:
                logger.error(f"No API key found for client {client_id}")
                return {"error": "No API key configured"}
            
            # Get client data for metric IDs
            client_doc = self.db.collection('clients').document(client_id).get()
            if not client_doc.exists:
                return {"error": "Client not found"}
            
            client_data = client_doc.to_dict()
            
            results = {}
            
            # Fetch each metric type
            for metric_type in metric_types:
                try:
                    if metric_type == "revenue":
                        # Use placed_order_metric_id for revenue
                        metric_data = await self._fetch_revenue_metrics(
                            client_data, api_key, timeframe
                        )
                    else:
                        # Use campaign metrics for engagement metrics
                        metric_data = await self._fetch_engagement_metrics(
                            client_data, api_key, metric_type, timeframe
                        )
                    
                    results[metric_type] = metric_data
                    
                except Exception as e:
                    logger.error(f"Error fetching {metric_type}: {e}")
                    results[metric_type] = {"error": str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Error in fetch_historical_metrics: {e}")
            return {"error": str(e)}
    
    async def _fetch_revenue_metrics(
        self, 
        client_data: Dict[str, Any], 
        api_key: str, 
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Fetch revenue metrics using Enhanced MCP's query_metric_aggregates
        """
        try:
            # Get placed_order_metric_id
            metric_id = client_data.get('placed_order_metric_id')
            if not metric_id:
                # Try to find it in other fields
                metric_id = (client_data.get('metrics', {}).get('placed_order_metric_id') or
                           client_data.get('klaviyo_placed_order_metric_id'))
            
            if not metric_id:
                return {"error": "No placed_order_metric_id configured"}
            
            # Convert timeframe to start/end dates
            dates = self._parse_timeframe(timeframe)
            
            # Call Enhanced MCP to get aggregated revenue
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.enhanced_mcp_url}/mcp/invoke",
                    json={
                        'method': 'query_metric_aggregates',
                        'params': {
                            'metric_id': metric_id,
                            'measurement': 'sum',
                            'group_by': ['month'],
                            'start_date': dates['start'],
                            'end_date': dates['end'],
                            'apiKey': api_key
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_revenue_data(data)
                else:
                    return {"error": f"MCP error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error fetching revenue metrics: {e}")
            return {"error": str(e)}
    
    async def _fetch_engagement_metrics(
        self, 
        client_data: Dict[str, Any], 
        api_key: str,
        metric_type: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Fetch engagement metrics (open_rate, click_rate, etc.) using campaign metrics
        """
        try:
            # Map metric types to Klaviyo statistics
            metric_mapping = {
                'open_rate': 'open_rate',
                'click_rate': 'click_rate',
                'bounce_rate': 'bounce_rate',
                'unsubscribe_rate': 'unsubscribe_rate',
                'delivered': 'delivered'
            }
            
            if metric_type not in metric_mapping:
                return {"error": f"Unsupported metric type: {metric_type}"}
            
            # Convert timeframe to dates
            dates = self._parse_timeframe(timeframe)
            
            # Use Natural Language MCP for flexible query
            query = f"Get {metric_type.replace('_', ' ')} for campaigns from {dates['start']} to {dates['end']}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.nl_mcp_url + "/query",
                    json={
                        'query': query,
                        'client_id': client_data.get('id') or client_data.get('_doc_id'),
                        'context': {'metric_type': metric_type}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_engagement_data(data, metric_type)
                else:
                    # Fallback to direct MCP call
                    return await self._fetch_campaign_metrics_direct(
                        api_key, metric_mapping[metric_type], dates
                    )
                    
        except Exception as e:
            logger.error(f"Error fetching engagement metrics: {e}")
            return {"error": str(e)}
    
    async def _fetch_campaign_metrics_direct(
        self, 
        api_key: str, 
        statistic: str, 
        dates: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Direct call to Enhanced MCP for campaign metrics
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.enhanced_mcp_url}/mcp/invoke",
                    json={
                        'method': 'get_campaign_metrics',
                        'params': {
                            'metrics': [statistic],
                            'start_date': dates['start'],
                            'end_date': dates['end'],
                            'apiKey': api_key
                        }
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"MCP error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error in direct campaign metrics fetch: {e}")
            return {"error": str(e)}
    
    async def get_prior_year_performance(
        self, 
        client_id: str, 
        year: int, 
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics from the prior year for comparison
        
        Args:
            client_id: Client identifier
            year: Current year (will fetch year-1)
            month: Specific month or None for full year
        
        Returns:
            Dictionary with prior year metrics
        """
        try:
            prior_year = year - 1
            
            if month:
                # Get specific month from prior year
                start_date = f"{prior_year}-{month:02d}-01T00:00:00Z"
                if month == 12:
                    end_date = f"{prior_year}-12-31T23:59:59Z"
                else:
                    end_date = f"{prior_year}-{month+1:02d}-01T00:00:00Z"
            else:
                # Get full prior year
                start_date = f"{prior_year}-01-01T00:00:00Z"
                end_date = f"{prior_year}-12-31T23:59:59Z"
            
            # Fetch all key metrics
            metrics = await self.fetch_historical_metrics(
                client_id,
                ['revenue', 'open_rate', 'click_rate', 'bounce_rate'],
                f"custom_{start_date}_{end_date}"
            )
            
            return {
                'year': prior_year,
                'month': month,
                'metrics': metrics,
                'period': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logger.error(f"Error fetching prior year performance: {e}")
            return {"error": str(e)}
    
    def _parse_timeframe(self, timeframe: str) -> Dict[str, str]:
        """
        Parse timeframe string into start and end dates
        """
        now = datetime.now()
        
        if timeframe == "last_12_months":
            start = (now - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z")
            end = now.strftime("%Y-%m-%dT23:59:59Z")
        elif timeframe == "last_year":
            last_year = now.year - 1
            start = f"{last_year}-01-01T00:00:00Z"
            end = f"{last_year}-12-31T23:59:59Z"
        elif timeframe == "last_30_days":
            start = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
            end = now.strftime("%Y-%m-%dT23:59:59Z")
        elif timeframe == "last_90_days":
            start = (now - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")
            end = now.strftime("%Y-%m-%dT23:59:59Z")
        elif timeframe.startswith("custom_"):
            # Format: custom_START_END
            parts = timeframe.split("_")
            if len(parts) >= 3:
                start = parts[1]
                end = parts[2]
            else:
                # Default to last 30 days
                start = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
                end = now.strftime("%Y-%m-%dT23:59:59Z")
        else:
            # Default to last 30 days
            start = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
            end = now.strftime("%Y-%m-%dT23:59:59Z")
        
        return {"start": start, "end": end}
    
    def _format_revenue_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw revenue data from MCP into structured response
        """
        try:
            formatted = {
                'monthly_values': [],
                'total': 0,
                'average': 0,
                'trend': 'stable'
            }
            
            # Extract monthly values
            if 'data' in raw_data:
                for item in raw_data.get('data', []):
                    month_data = {
                        'month': item.get('month'),
                        'value': item.get('value', 0)
                    }
                    formatted['monthly_values'].append(month_data)
                    formatted['total'] += month_data['value']
            
            # Calculate average
            if formatted['monthly_values']:
                formatted['average'] = formatted['total'] / len(formatted['monthly_values'])
                
                # Calculate trend
                if len(formatted['monthly_values']) > 1:
                    first_half_avg = sum(v['value'] for v in formatted['monthly_values'][:6]) / 6
                    second_half_avg = sum(v['value'] for v in formatted['monthly_values'][6:]) / len(formatted['monthly_values'][6:])
                    
                    if second_half_avg > first_half_avg * 1.1:
                        formatted['trend'] = 'increasing'
                    elif second_half_avg < first_half_avg * 0.9:
                        formatted['trend'] = 'decreasing'
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting revenue data: {e}")
            return raw_data
    
    def _format_engagement_data(
        self, 
        raw_data: Dict[str, Any], 
        metric_type: str
    ) -> Dict[str, Any]:
        """
        Format raw engagement data from MCP into structured response
        """
        try:
            formatted = {
                'metric_type': metric_type,
                'values': [],
                'average': 0,
                'min': None,
                'max': None
            }
            
            # Extract values from NL MCP response
            if 'result' in raw_data and isinstance(raw_data['result'], dict):
                # Handle aggregated data
                if 'monthly_values' in raw_data['result']:
                    formatted['values'] = raw_data['result']['monthly_values']
                elif 'data' in raw_data['result']:
                    formatted['values'] = raw_data['result']['data']
            
            # Calculate statistics
            if formatted['values']:
                numeric_values = [v.get('value', 0) for v in formatted['values'] if 'value' in v]
                if numeric_values:
                    formatted['average'] = sum(numeric_values) / len(numeric_values)
                    formatted['min'] = min(numeric_values)
                    formatted['max'] = max(numeric_values)
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting engagement data: {e}")
            return raw_data