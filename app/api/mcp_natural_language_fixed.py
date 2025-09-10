"""
Natural Language Wrapper for MCP Gateway - FIXED VERSION
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
    """Strategy for executing a query"""
    tool: str
    params: Dict[str, Any]
    description: str
    priority: int = 0

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
        
        # Get API key for client
        api_key = await key_resolver.get_client_klaviyo_key(request.client_id)
        if not api_key:
            return {
                "success": False,
                "error": f"No API key found for client {request.client_id}"
            }
        
        # Analyze query and create strategies
        strategies = analyze_query_intent(request.query, client_data)
        
        # Execute strategies
        results = []
        for strategy in strategies:
            try:
                # Special handling for revenue queries that need placed_order_metric_id
                if strategy.tool == 'metrics.aggregate' and 'revenue' in request.query.lower():
                    placed_order_metric_id = client_data.get('placed_order_metric_id')
                    if not placed_order_metric_id:
                        results.append({
                            'tool': strategy.tool,
                            'description': strategy.description,
                            'success': False,
                            'error': 'No placed_order_metric_id configured for this client'
                        })
                        continue
                    
                    # Add metric_id to params
                    strategy.params['metric_id'] = placed_order_metric_id
                
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
                            'error': f"HTTP {response.status_code}: {response.text}"
                        })
                        
            except Exception as e:
                logger.error(f"Error executing {strategy.tool}: {e}")
                results.append({
                    'tool': strategy.tool,
                    'description': strategy.description,
                    'success': False,
                    'error': str(e)
                })
        
        # Format results
        interpretation = format_interpretation(request.query, results)
        aggregated_data = aggregate_results(results)
        
        return {
            "success": True,
            "query": request.query,
            "client_id": request.client_id,
            "strategies_executed": len(strategies),
            "interpretation": interpretation,
            "result": aggregated_data,
            "raw_results": results
        }
        
    except Exception as e:
        logger.error(f"Natural language processing error: {e}")
        return {
            "success": False,
            "query": request.query,
            "error": str(e)
        }

def analyze_query_intent(query: str, client_data: Dict[str, Any]) -> List[QueryStrategy]:
    """Analyze query intent and create execution strategies"""
    strategies = []
    query_lower = query.lower()
    
    # Revenue queries
    if 'revenue' in query_lower:
        # Extract time range
        time_range = extract_time_range(query)
        params = {'measurement': 'sum', 'filter': []}
        
        if time_range:
            params['filter'].extend([
                f"greater-or-equal(datetime,{time_range[0]})",
                f"less-than(datetime,{time_range[1]})"
            ])
        
        # Group by campaign if mentioned
        if 'per campaign' in query_lower or 'by campaign' in query_lower:
            params['by'] = ['$attributed_message']
        
        strategies.append(QueryStrategy(
            tool='metrics.aggregate',
            params=params,
            description='Calculate revenue metrics',
            priority=1
        ))
    
    # Campaign performance queries
    if 'campaign' in query_lower and any(word in query_lower for word in ['performance', 'metric', 'open', 'click']):
        strategies.append(QueryStrategy(
            tool='campaigns.list',
            params={'limit': 50},
            description='List campaigns',
            priority=1
        ))
    
    # Segment queries
    if 'segment' in query_lower:
        strategies.append(QueryStrategy(
            tool='segments.list',
            params={'limit': 100},
            description='List segments',
            priority=1
        ))
    
    # Default fallback
    if not strategies:
        strategies.append(QueryStrategy(
            tool='campaigns.list',
            params={'limit': 10},
            description='List recent campaigns',
            priority=1
        ))
    
    return strategies

def extract_time_range(query: str) -> Optional[Tuple[str, str]]:
    """Extract time range from natural language query"""
    query_lower = query.lower()
    now = datetime.now()
    
    if 'last 7 days' in query_lower or 'past week' in query_lower:
        start = (now - timedelta(days=7)).isoformat() + 'Z'
        end = now.isoformat() + 'Z'
        return (start, end)
    
    if 'last 30 days' in query_lower or 'past month' in query_lower:
        start = (now - timedelta(days=30)).isoformat() + 'Z'
        end = now.isoformat() + 'Z'
        return (start, end)
    
    return None

def format_interpretation(query: str, results: List[Dict[str, Any]]) -> str:
    """Format results into human-readable interpretation"""
    successful = [r for r in results if r.get('success')]
    
    if not successful:
        return "I encountered errors processing your request."
    
    # Check for revenue results
    for result in successful:
        if result['tool'] == 'metrics.aggregate' and 'revenue' in query.lower():
            data = result.get('data', {})
            if data and 'data' in data:
                metrics = data['data']
                if metrics and len(metrics) > 0:
                    total = sum(m.get('measurements', {}).get('sum', [0])[0] for m in metrics)
                    return f"Total revenue: ${total:,.2f}"
    
    return f"Executed {len(successful)} operations successfully."

def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate results from multiple tool executions"""
    aggregated = {}
    
    for result in results:
        if result.get('success') and result.get('data'):
            tool = result['tool']
            data = result['data']
            
            if tool == 'metrics.aggregate':
                aggregated['metrics_data'] = data.get('data', [])
                # Calculate total if it's revenue
                if data.get('data'):
                    total = sum(m.get('measurements', {}).get('sum', [0])[0] for m in data['data'])
                    aggregated['total_value'] = total
            elif tool == 'campaigns.list':
                aggregated['campaigns'] = data.get('data', [])
            elif tool == 'segments.list':
                aggregated['segments'] = data.get('data', [])
    
    return aggregated

@router.post("/chat")
async def chat_interface(
    request: NaturalLanguageRequest,
    db: firestore.Client = Depends(get_db),
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """
    Simplified chat interface that returns formatted messages
    """
    # Call process_natural_language
    result = await process_natural_language(request, db, key_resolver)
    
    if not result["success"]:
        return {
            "message": f"I couldn't process that request. {result.get('error', 'Please try rephrasing.')}",
            "success": False
        }
    
    # Use the interpretation from the AI processing
    message = result.get("interpretation", "Query processed successfully")
    
    return {
        "message": message,
        "success": True,
        "data": result.get("result", {})
    }

@router.get("/suggestions")
async def get_suggestions(query: str = "") -> Dict[str, Any]:
    """Get query suggestions based on partial input"""
    suggestions = [
        "Give me total revenue for last 30 days",
        "What are the open and click rates for recent campaigns?",
        "Show me all active segments with their sizes",
        "Calculate revenue per campaign for last month",
        "What times of day have the best open rates?",
        "Which subject lines performed best?",
        "Show engagement metrics for our top segments",
        "What's the average order value this month?",
        "Compare email performance week over week"
    ]
    
    if query:
        # Filter suggestions based on partial query
        query_lower = query.lower()
        filtered = [s for s in suggestions if query_lower in s.lower()]
        return {"suggestions": filtered[:5]}
    
    return {"suggestions": suggestions[:5]}