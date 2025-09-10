"""
Natural Language Wrapper for MCP Gateway
AI-enhanced query understanding with intelligent multi-tool orchestration
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from google.cloud import firestore
import httpx
import json

from app.deps import get_db
from app.api.mcp_gateway import invoke_mcp_tool, MCPRequest
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp/nl", tags=["MCP Natural Language"])

# MCP server configuration
ENHANCED_MCP_URL = "http://localhost:9095"

class NaturalLanguageRequest(BaseModel):
    """Natural language query request"""
    query: str
    client_id: Optional[str] = None
    context: Dict[str, Any] = {}

class QueryStrategy(BaseModel):
    """Strategy for executing part of a query"""
    tool: str
    params: Dict[str, Any]
    description: str
    priority: int = 0

class NLResponse(BaseModel):
    """Natural language response"""
    interpretation: str
    tool_used: str
    result: Any
    success: bool
def extract_time_range(query: str) -> Optional[Tuple[str, str]]:
    """Extract time range from natural language query"""
    now = datetime.now()
    query_lower = query.lower()
    
    # Common time patterns
    if 'last 365 days' in query_lower or 'last year' in query_lower:
        start = now - timedelta(days=365)
        return (start.isoformat(), now.isoformat())
    elif 'last 90 days' in query_lower:
        start = now - timedelta(days=90)
        return (start.isoformat(), now.isoformat())
    elif 'last 30 days' in query_lower or 'last month' in query_lower:
        start = now - timedelta(days=30)
        return (start.isoformat(), now.isoformat())
    elif 'last 7 days' in query_lower or 'last week' in query_lower:
        start = now - timedelta(days=7)
        return (start.isoformat(), now.isoformat())
    elif 'today' in query_lower:
        start = now.replace(hour=0, minute=0, second=0)
        return (start.isoformat(), now.isoformat())
    elif 'yesterday' in query_lower:
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0)
        end = yesterday.replace(hour=23, minute=59, second=59)
        return (start.isoformat(), end.isoformat())
    
    # Default to last 30 days for general queries
    return ((now - timedelta(days=30)).isoformat(), now.isoformat())

def analyze_query_intent(query: str, client_data: Dict[str, Any]) -> List[QueryStrategy]:
    """
    Analyze query intent and create multi-tool execution strategies
    """
    strategies = []
    query_lower = query.lower()
    time_range = extract_time_range(query)
    
    # Get client's metric IDs
    placed_order_metric_id = client_data.get('placed_order_metric_id')
    
    # Revenue queries
    if any(word in query_lower for word in ['revenue', 'sales', 'income', 'earnings', 'money']):
        if not placed_order_metric_id:
            strategies.append(QueryStrategy(
                tool='error',
                params={'message': 'Client missing placed_order_metric_id in Firestore'},
                description='Cannot calculate revenue without metric ID',
                priority=0
            ))
        else:
            params = {
                'metric_id': placed_order_metric_id,
                'measurements': ['sum_value', 'count', 'unique'],
                'interval': 'day'
            }
            
            if time_range:
                params['filter'] = [
                    f"greater-or-equal(datetime,{time_range[0]})",
                    f"less-than(datetime,{time_range[1]})"
                ]
            
            # Group by campaign if mentioned
            if 'per campaign' in query_lower or 'by campaign' in query_lower:
                params['by'] = ['$attributed_message']
            elif 'by segment' in query_lower:
                params['by'] = ['$segment']
            
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params=params,
                description='Calculate revenue metrics',
                priority=1
            ))
    
    # Campaign performance queries
    if ('campaign' in query_lower and 'performance' in query_lower) or \
       ('campaign' in query_lower and 'metric' in query_lower):
        # List campaigns
        campaign_params = {'limit': 100}
        if time_range:
            campaign_params['filter'] = f"greater-or-equal(created,{time_range[0]})"
        
        strategies.append(QueryStrategy(
            tool='campaigns.list',
            params=campaign_params,
            description='List campaigns',
            priority=1
        ))
        
        # Get performance metrics
        metric_types = []
        if 'open' in query_lower or 'all' in query_lower:
            metric_types.append(('TPpPhm', 'Opens'))
        if 'click' in query_lower or 'all' in query_lower:
            metric_types.append(('TPpPho', 'Clicks'))
        if 'conversion' in query_lower:
            metric_types.append((placed_order_metric_id, 'Conversions'))
        
        for metric_id, metric_name in metric_types:
            if metric_id:
                params = {
                    'metric_id': metric_id,
                    'measurements': ['sum_value', 'count', 'unique'],
                    'interval': 'day',
                    'by': ['$attributed_message']
                }
                
                if time_range:
                    params['filter'] = [
                        f"greater-or-equal(datetime,{time_range[0]})",
                        f"less-than(datetime,{time_range[1]})"
                    ]
                
                strategies.append(QueryStrategy(
                    tool='metrics.aggregate',
                    params=params,
                    description=f'Get {metric_name} metrics',
                    priority=2
                ))
    
    # Segment analysis
    if 'segment' in query_lower:
        strategies.append(QueryStrategy(
            tool='segments.list',
            params={'limit': 100},
            description='List segments',
            priority=1
        ))
        
        if 'engagement' in query_lower or 'value' in query_lower or 'metric' in query_lower:
            # Add segment metrics
            for metric_id, metric_name in [('TPpPhm', 'Opens'), ('TPpPho', 'Clicks')]:
                params = {
                    'metric_id': metric_id,
                    'measurements': ['sum_value', 'count', 'unique'],
                    'interval': 'month',
                    'by': ['$segment']
                }
                
                if time_range:
                    params['filter'] = [
                        f"greater-or-equal(datetime,{time_range[0]})",
                        f"less-than(datetime,{time_range[1]})"
                    ]
                
                strategies.append(QueryStrategy(
                    tool='metrics.aggregate',
                    params=params,
                    description=f'Segment {metric_name} analysis',
                    priority=2
                ))
    
    # Send time optimization
    if 'send time' in query_lower or 'optimal time' in query_lower or 'best time' in query_lower:
        # Analyze by hour and day
        for metric_id, metric_name in [('TPpPhm', 'Opens'), ('TPpPho', 'Clicks')]:
            # By hour
            params_hour = {
                'metric_id': metric_id,
                'measurements': ['sum_value', 'count', 'unique'],
                'interval': 'hour',
                'by': ['$hour_of_day']
            }
            if time_range:
                params_hour['filter'] = [
                    f"greater-or-equal(datetime,{time_range[0]})",
                    f"less-than(datetime,{time_range[1]})"
                ]
            
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params=params_hour,
                description=f'{metric_name} by hour',
                priority=1
            ))
            
            # By day of week
            params_day = {
                'metric_id': metric_id,
                'measurements': ['sum_value', 'count', 'unique'],
                'interval': 'day',
                'by': ['$day_of_week']
            }
            if time_range:
                params_day['filter'] = [
                    f"greater-or-equal(datetime,{time_range[0]})",
                    f"less-than(datetime,{time_range[1]})"
                ]
            
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params=params_day,
                description=f'{metric_name} by day of week',
                priority=2
            ))
    
    # Subject line and content analysis
    if 'subject line' in query_lower or 'content' in query_lower or 'top performing' in query_lower:
        # Get campaigns
        campaign_params = {
            'limit': 100,
            'include': ['subject', 'body']
        }
        if time_range:
            campaign_params['filter'] = f"greater-or-equal(created,{time_range[0]})"
        
        strategies.append(QueryStrategy(
            tool='campaigns.list',
            params=campaign_params,
            description='Get campaigns with content',
            priority=1
        ))
        
        # Get performance by campaign
        for metric_id, metric_name in [('TPpPhm', 'Opens'), ('TPpPho', 'Clicks')]:
            params = {
                'metric_id': metric_id,
                'measurements': ['sum_value', 'count', 'unique'],
                'interval': 'day',
                'by': ['$attributed_message']
            }
            
            if time_range:
                params['filter'] = [
                    f"greater-or-equal(datetime,{time_range[0]})",
                    f"less-than(datetime,{time_range[1]})"
                ]
            
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params=params,
                description=f'Content {metric_name} analysis',
                priority=2
            ))
    
    # Default strategies if no specific intent detected
    if not strategies:
        strategies.append(QueryStrategy(
            tool='campaigns.list',
            params={'limit': 10},
            description='List recent campaigns',
            priority=1
        ))
    
    return strategies

@router.post("/query")
async def process_natural_language(
    request: NaturalLanguageRequest,
    db: firestore.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Process a natural language query with intelligent multi-tool orchestration
    """
    try:
        # Default client if not specified
        if not request.client_id:
            request.client_id = "christopher-bean-coffee"
        
        # Get client data from Firestore
        client_doc = db.collection('clients').document(request.client_id).get()
        if not client_doc.exists:
            return {
                "success": False,
                "error": f"Client {request.client_id} not found"
            }
        
        client_data = client_doc.to_dict()
        
        # Get API key for client (key_resolver is already async)
        api_key = await key_resolver.get_client_klaviyo_key(request.client_id)
        if not api_key:
            return {
                "success": False,
                "error": f"No API key found for client {request.client_id}"
            }
        
        # Analyze query and create execution strategies
        strategies = analyze_query_intent(request.query, client_data)
        
        # Execute each strategy
        results = []
        for strategy in sorted(strategies, key=lambda x: x.priority):
            try:
                if strategy.tool == 'error':
                    results.append({
                        'tool': strategy.tool,
                        'description': strategy.description,
                        'success': False,
                        'error': strategy.params.get('message')
                    })
                    continue
                
                # Execute MCP tool via Enhanced MCP server
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{ENHANCED_MCP_URL}/mcp/invoke",
                        json={
                            'method': strategy.tool,
                            'params': {**strategy.params, 'apiKey': api_key}
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result_data = response.json()
                        results.append({
                            'tool': strategy.tool,
                            'description': strategy.description,
                            'success': True,
                            'data': result_data
                        })
                    else:
                        results.append({
                            'tool': strategy.tool,
                            'description': strategy.description,
                            'success': False,
                            'error': f"HTTP {response.status_code}"
                        })
                        
            except Exception as e:
                logger.error(f"Error executing {strategy.tool}: {e}")
                results.append({
                    'tool': strategy.tool,
                    'description': strategy.description,
                    'success': False,
                    'error': str(e)
                })
        
        # Aggregate and format results
        formatted_response = format_multi_tool_results(request.query, results)
        
        return {
            "success": True,
            "query": request.query,
            "client_id": request.client_id,
            "strategies_executed": len(strategies),
            "interpretation": formatted_response['interpretation'],
            "result": formatted_response['result'],
            "raw_results": results
        }
        
    except Exception as e:
        logger.error(f"Natural language processing error: {e}")
        return {
            "success": False,
            "query": request.query,
            "error": str(e)
        }

def format_multi_tool_results(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format results from multiple tool executions into a coherent response
    """
    query_lower = query.lower()
    formatted = {
        'interpretation': '',
        'result': {}
    }
    
    # Check for any errors
    errors = [r for r in results if not r.get('success')]
    if errors:
        formatted['interpretation'] = f"Encountered {len(errors)} error(s) while processing"
        formatted['result']['errors'] = [e.get('error') for e in errors]
    
    # Aggregate successful results
    successful = [r for r in results if r.get('success')]
    
    # Revenue queries
    if 'revenue' in query_lower:
        revenue_data = [r for r in successful if 'metrics.aggregate' in r.get('tool', '')]
        if revenue_data:
            # Sum up revenue values
            total_revenue = 0
            for r in revenue_data:
                data = r.get('data', {}).get('data', {})
                if isinstance(data, dict) and 'attributes' in data:
                    values = data['attributes'].get('data', [])
                    for v in values:
                        if 'values' in v:
                            total_revenue += sum(v['values'])
            
            formatted['interpretation'] = f"Calculated revenue metrics"
            formatted['result']['total_revenue'] = total_revenue
            formatted['result']['period'] = extract_time_range(query)
    
    # Campaign performance queries
    elif 'campaign' in query_lower and 'performance' in query_lower:
        campaigns = [r for r in successful if 'campaigns.list' in r.get('tool', '')]
        metrics = [r for r in successful if 'metrics.aggregate' in r.get('tool', '')]
        
        if campaigns:
            campaign_data = campaigns[0].get('data', {}).get('data', {}).get('data', [])
            formatted['result']['total_campaigns'] = len(campaign_data)
        
        if metrics:
            formatted['result']['metrics'] = {}
            for m in metrics:
                desc = m.get('description', '')
                if 'Opens' in desc:
                    formatted['result']['metrics']['opens'] = m.get('data')
                elif 'Clicks' in desc:
                    formatted['result']['metrics']['clicks'] = m.get('data')
                elif 'Conversions' in desc:
                    formatted['result']['metrics']['conversions'] = m.get('data')
        
        formatted['interpretation'] = "Retrieved campaign performance metrics"
    
    # Segment analysis
    elif 'segment' in query_lower:
        segments = [r for r in successful if 'segments.list' in r.get('tool', '')]
        if segments:
            segment_data = segments[0].get('data', {}).get('data', {}).get('data', [])
            formatted['result']['total_segments'] = len(segment_data)
            formatted['result']['segments'] = [
                {
                    'name': s.get('attributes', {}).get('name'),
                    'id': s.get('id')
                }
                for s in segment_data[:10]
            ]
        formatted['interpretation'] = "Analyzed segments"
    
    # Send time optimization
    elif 'send time' in query_lower or 'optimal time' in query_lower:
        time_metrics = [r for r in successful if 'by hour' in r.get('description', '')]
        day_metrics = [r for r in successful if 'by day' in r.get('description', '')]
        
        formatted['result']['send_time_analysis'] = {
            'by_hour': [m.get('data') for m in time_metrics],
            'by_day': [m.get('data') for m in day_metrics]
        }
        formatted['interpretation'] = "Analyzed optimal send times"
    
    # Generic fallback
    else:
        formatted['interpretation'] = f"Executed {len(successful)} operations"
        formatted['result']['operations'] = [
            {'tool': r.get('tool'), 'description': r.get('description')}
            for r in successful
        ]
    
    return formatted

def format_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format MCP results for natural language response
    """
    if not result.get("success"):
        return {
            "message": "Unable to retrieve data",
            "error": result.get("detail", "Unknown error")
        }
    
    data = result.get("data", {})
    
    # Format based on tool type
    if tool_name == "campaigns.list":
        campaigns = data.get("data", {}).get("data", [])
        if campaigns:
            return {
                "count": len(campaigns),
                "campaigns": [
                    {
                        "name": c.get("attributes", {}).get("name", "Unnamed"),
                        "status": c.get("attributes", {}).get("status"),
                        "created": c.get("attributes", {}).get("created_at")
                    }
                    for c in campaigns[:5]
                ]
            }
        return {"message": "No campaigns found"}
    
    elif tool_name == "metrics.list":
        metrics = data.get("data", {}).get("data", [])
        if metrics:
            return {
                "count": len(metrics),
                "metrics": [
                    {
                        "name": m.get("attributes", {}).get("name", "Unnamed"),
                        "integration": m.get("attributes", {}).get("integration"),
                        "id": m.get("id")
                    }
                    for m in metrics[:10]
                ]
            }
        return {"message": "No metrics found"}
    
    elif tool_name == "segments.list":
        segments = data.get("data", {}).get("data", [])
        if segments:
            return {
                "count": len(segments),
                "segments": [
                    {
                        "name": s.get("attributes", {}).get("name", "Unnamed"),
                        "created": s.get("attributes", {}).get("created_at")
                    }
                    for s in segments[:5]
                ]
            }
        return {"message": "No segments found"}
    
    elif tool_name in ["revenue.last7", "revenue.last30"]:
        if data:
            return {
                "total_revenue": data.get("total", 0),
                "campaign_revenue": data.get("campaign_total", 0),
                "flow_revenue": data.get("flow_total", 0),
                "period": "last 7 days" if "last7" in tool_name else "last 30 days"
            }
        return {"message": "Revenue data not available"}
    
    # Default format
    return data

@router.post("/chat")
async def chat_interface(
    request: NaturalLanguageRequest,
    db: firestore.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Simplified chat interface that returns formatted messages
    """
    # Call process_natural_language directly, FastAPI will inject dependencies
    from fastapi import Request as FastAPIRequest
    from starlette.requests import Request
    
    # Simply forward the request to the main endpoint
    return await process_natural_language(request, db, key_resolver)
    
    if not result["success"]:
        return {
            "message": f"I couldn't process that request. {result.get('error', 'Please try rephrasing.')}",
            "success": False
        }
    
    # Format chat response based on result
    if result.get("tool_used") == "help":
        capabilities = result["result"]["capabilities"]
        return {
            "message": "I can help you with:\n" + "\n".join(f"• {cap}" for cap in capabilities),
            "success": True
        }
    
    formatted = result.get("result", {})
    tool = result.get("tool_used", "")
    
    # Build friendly response
    if "campaigns" in tool:
        if formatted.get("campaigns"):
            campaigns = formatted["campaigns"]
            message = f"Found {formatted['count']} campaigns:\n"
            message += "\n".join(f"• {c['name']} ({c['status']})" for c in campaigns)
        else:
            message = formatted.get("message", "No campaigns found")
            
    elif "metrics" in tool:
        if formatted.get("metrics"):
            metrics = formatted["metrics"]
            message = f"Found {formatted['count']} metrics:\n"
            message += "\n".join(f"• {m['name']} ({m['integration']})" for m in metrics[:5])
            if formatted['count'] > 5:
                message += f"\n... and {formatted['count'] - 5} more"
        else:
            message = formatted.get("message", "No metrics found")
            
    elif "segments" in tool:
        if formatted.get("segments"):
            segments = formatted["segments"]
            message = f"Found {formatted['count']} segments:\n"
            message += "\n".join(f"• {s['name']}" for s in segments)
        else:
            message = formatted.get("message", "No segments found")
            
    elif "revenue" in tool:
        if formatted.get("total_revenue") is not None:
            message = f"Revenue for {formatted.get('period', 'selected period')}:\n"
            message += f"• Total: ${formatted['total_revenue']:,.2f}\n"
            message += f"• From Campaigns: ${formatted['campaign_revenue']:,.2f}\n"
            message += f"• From Flows: ${formatted['flow_revenue']:,.2f}"
        else:
            message = formatted.get("message", "Revenue data not available")
    else:
        # Generic response
        message = f"Processed {tool} request successfully"
        if isinstance(formatted, dict) and formatted.get("message"):
            message = formatted["message"]
    
    return {
        "message": message,
        "success": True,
        "tool_used": tool,
        "details": formatted
    }

@router.get("/suggestions")
async def get_suggestions(query: str = "") -> Dict[str, Any]:
    """
    Get query suggestions based on partial input
    """
    suggestions = [
        "Show me the latest campaigns",
        "List all metrics",
        "What segments do we have?",
        "Show revenue for last 7 days",
        "Display email templates",
        "Check campaign performance",
        "Show automation flows",
        "List top performing campaigns",
        "What's our monthly revenue?",
        "Show customer segments"
    ]
    
    if query:
        query_lower = query.lower()
        filtered = [s for s in suggestions if query_lower in s.lower()]
        return {"suggestions": filtered[:5]}
    
    return {"suggestions": suggestions[:5]}