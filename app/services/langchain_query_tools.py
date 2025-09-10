"""
LangChain-compatible tools for comprehensive query system
Provides structured tools with proper typing and tracing
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_core.tools import tool
from langsmith import traceable

from app.services.comprehensive_query_handler import ComprehensiveQueryHandler

logger = logging.getLogger(__name__)

# Pydantic models for tool inputs/outputs
class ComprehensiveQueryInput(BaseModel):
    """Input schema for comprehensive query tool"""
    query: str = Field(description="Natural language query (can be multi-line)")
    client_id: str = Field(description="Client identifier for Klaviyo")
    context: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional context (revenue_metric_id, etc.)"
    )
    include_ai_analysis: bool = Field(
        default=True,
        description="Whether to include AI analysis in results"
    )

class ComprehensiveQueryOutput(BaseModel):
    """Output schema for comprehensive query results"""
    success: bool = Field(description="Whether query executed successfully")
    total_requests: int = Field(description="Number of requests parsed from query")
    successful_requests: int = Field(description="Number of successfully executed requests")
    aggregated_data: Dict[str, Any] = Field(description="Aggregated results from all queries")
    ai_analysis: Optional[Dict[str, Any]] = Field(description="AI-ready analysis if requested")
    error: Optional[str] = Field(description="Error message if failed")
    trace_id: Optional[str] = Field(description="LangSmith trace ID")

class QueryParseInput(BaseModel):
    """Input for query parsing tool"""
    query: str = Field(description="Natural language query to parse")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Query context")

class QueryParseOutput(BaseModel):
    """Output from query parsing"""
    query_parts: List[str] = Field(description="Individual query parts")
    requests: List[Dict[str, Any]] = Field(description="Parsed request specifications")
    time_ranges: List[Dict[str, Any]] = Field(description="Extracted time ranges")
    metrics: List[str] = Field(description="Identified metrics")

# Initialize handler
_handler = ComprehensiveQueryHandler()

@traceable(name="comprehensive_query_tool", tags=["mcp", "query", "klaviyo"])
async def execute_comprehensive_query(
    query: str,
    client_id: str,
    context: Optional[Dict[str, Any]] = None,
    include_ai_analysis: bool = True
) -> Dict[str, Any]:
    """
    Execute a comprehensive multi-part query with LangSmith tracing
    
    This tool handles complex queries by:
    1. Parsing natural language into individual requests
    2. Executing requests in parallel via Enhanced MCP
    3. Aggregating results
    4. Generating AI-ready analysis
    
    Args:
        query: Natural language query (can be multi-line)
        client_id: Client identifier
        context: Additional context for query execution
        include_ai_analysis: Whether to generate AI analysis
    
    Returns:
        Comprehensive query results with aggregated data
    """
    try:
        logger.info(f"🎯 Executing comprehensive query for {client_id}")
        
        # Add default context if not provided
        if context is None:
            context = {}
        
        # Ensure we have a revenue metric ID
        if 'revenue_metric_id' not in context:
            context['revenue_metric_id'] = 'TPWsCU'  # Default Klaviyo metric
        
        # Execute the comprehensive query
        result = await _handler.process_comprehensive_query(
            query=query,
            client_id=client_id,
            context=context
        )
        
        # Format response
        response = {
            'success': result.get('success', False),
            'total_requests': result.get('total_requests', 0),
            'successful_requests': result.get('successful_requests', 0),
            'aggregated_data': result.get('aggregated_data', {}),
            'error': result.get('error')
        }
        
        if include_ai_analysis:
            response['ai_analysis'] = result.get('ai_ready_analysis')
        
        # Add trace ID if available
        import langsmith
        if hasattr(langsmith, 'get_current_run_tree'):
            try:
                run_tree = langsmith.get_current_run_tree()
                if run_tree:
                    response['trace_id'] = str(run_tree.id)
            except:
                pass
        
        return response
        
    except Exception as e:
        logger.error(f"Comprehensive query failed: {e}", exc_info=True)
        return {
            'success': False,
            'total_requests': 0,
            'successful_requests': 0,
            'aggregated_data': {},
            'error': str(e)
        }

@traceable(name="parse_query", tags=["parsing", "nlp"])
def parse_comprehensive_query(
    query: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Parse a natural language query into executable requests
    
    This tool analyzes the query to identify:
    - Individual query parts (multi-line or multi-sentence)
    - Time ranges mentioned
    - Specific metrics requested
    - Query intent (campaigns, segments, revenue, etc.)
    
    Args:
        query: Natural language query
        context: Additional context for parsing
    
    Returns:
        Parsed query components
    """
    try:
        # Parse the query
        requests = _handler._parse_comprehensive_query(query, context or {})
        
        # Extract components for analysis
        query_parts = []
        time_ranges = []
        metrics = set()
        
        for req in requests:
            query_parts.append(req.description)
            if req.time_range:
                time_ranges.append(req.time_range)
            metrics.update(req.metrics)
        
        return {
            'query_parts': query_parts,
            'requests': [
                {
                    'query_type': req.query_type,
                    'tool': req.tool,
                    'params': req.params,
                    'description': req.description,
                    'metrics': req.metrics
                }
                for req in requests
            ],
            'time_ranges': time_ranges,
            'metrics': list(metrics)
        }
        
    except Exception as e:
        logger.error(f"Query parsing failed: {e}")
        return {
            'query_parts': [],
            'requests': [],
            'time_ranges': [],
            'metrics': [],
            'error': str(e)
        }

# Create structured tools for LangChain
comprehensive_query_tool = StructuredTool.from_function(
    func=execute_comprehensive_query,
    name="comprehensive_klaviyo_query",
    description="""Execute complex multi-part Klaviyo queries. 
    Handles queries like 'Get campaign performance for last 30 days and list all segments with engagement rates'.
    Automatically parses, executes in parallel, and aggregates results.""",
    args_schema=ComprehensiveQueryInput,
    return_direct=False,
    coroutine=execute_comprehensive_query  # Support async execution
)

query_parser_tool = StructuredTool.from_function(
    func=parse_comprehensive_query,
    name="parse_klaviyo_query",
    description="Parse natural language queries into structured Klaviyo API requests",
    args_schema=QueryParseInput,
    return_direct=False
)

# Convenience function to get all tools
def get_comprehensive_query_tools() -> List[StructuredTool]:
    """Get all comprehensive query tools for LangChain agents"""
    return [comprehensive_query_tool, query_parser_tool]

# Tool for calendar workflow integration
@tool("calendar_data_gathering", return_direct=False)
@traceable(name="calendar_data_gathering", tags=["calendar", "workflow"])
async def gather_calendar_data(
    client_id: str,
    month: str,
    requirements: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gather all necessary data for calendar planning
    
    This tool executes a comprehensive set of queries to collect:
    - Campaign performance metrics
    - Segment analysis
    - Revenue data
    - Optimal send times
    - Content performance
    
    Args:
        client_id: Client identifier
        month: Target month for planning (YYYY-MM)
        requirements: Additional data requirements in natural language
    
    Returns:
        Comprehensive data package for calendar planning
    """
    # Build comprehensive query based on standard calendar needs
    base_queries = [
        f"Get campaign performance metrics for last 30 days including open_rate, click_rate, conversion_rate",
        f"List all active segments with size, engagement rates, and value metrics",
        f"Calculate revenue metrics for last 30 days including total revenue, revenue per campaign",
        f"Analyze optimal send times by day of week and hour",
        f"Get top performing subject lines and content themes"
    ]
    
    # Add custom requirements if provided
    if requirements:
        base_queries.append(requirements)
    
    # Combine into single query
    full_query = "\n".join(base_queries)
    
    # Execute comprehensive query
    result = await execute_comprehensive_query(
        query=full_query,
        client_id=client_id,
        context={'calendar_month': month},
        include_ai_analysis=True
    )
    
    # Format for calendar workflow
    return {
        'client_id': client_id,
        'month': month,
        'data_collected': result.get('successful_requests', 0) > 0,
        'metrics': result.get('aggregated_data', {}),
        'insights': result.get('ai_analysis', {}),
        'ready_for_planning': result.get('success', False)
    }