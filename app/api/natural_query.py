"""
Natural Language Query API

Provides endpoints for querying Klaviyo data using natural language,
with intelligent parsing and fallback to direct MCP tool invocation.
"""
from fastapi import APIRouter, HTTPException, Depends, Query as QueryParam
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from app.services.intelligent_query_service import IntelligentQueryService, QueryMode
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver
from app.deps import get_db
from google.cloud import firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["Natural Language Query"])


class NaturalQueryRequest(BaseModel):
    """Request model for natural language queries"""
    query: str = Field(..., description="Natural language query or tool name")
    client_id: str = Field(..., description="Client ID for data context")
    mode: str = Field("auto", description="Query mode: intelligent, direct, or auto")
    fallback_tool: Optional[str] = Field(None, description="Fallback tool name if intelligent mode fails")
    fallback_params: Optional[Dict[str, Any]] = Field(None, description="Fallback tool parameters")
    tool_params: Optional[Dict[str, Any]] = Field(None, description="Direct tool parameters (for direct mode)")


class QueryResponse(BaseModel):
    """Response model for query results"""
    success: bool
    query: str
    client_id: str
    mode: str
    results: Optional[Any] = None
    error: Optional[str] = None
    strategies_used: Optional[int] = None
    processing_time_ms: Optional[float] = None


# Note: Query service will be initialized per-request with database connection


@router.post("/natural", response_model=QueryResponse)
async def natural_language_query(
    request: NaturalQueryRequest,
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver),
    db: firestore.Client = Depends(get_db)
) -> QueryResponse:
    """
    Execute a natural language query against Klaviyo data.
    
    Modes:
    - intelligent: Parse natural language and build smart query strategies
    - direct: Treat query as tool name and execute directly with provided params
    - auto: Try intelligent first, fallback to direct on failure
    """
    import time
    start_time = time.time()
    
    try:
        # Initialize query service with database connection
        query_service = IntelligentQueryService(db=db)
        
        # Validate client has API key
        api_key = await key_resolver.get_client_klaviyo_key(request.client_id)
        if not api_key:
            raise HTTPException(
                status_code=404,
                detail=f"No API key found for client {request.client_id}"
            )
        
        # Convert mode string to enum
        try:
            mode = QueryMode(request.mode.lower())
        except ValueError:
            mode = QueryMode.AUTO
        
        # Execute query based on mode
        if mode == QueryMode.DIRECT:
            # Direct mode - use query as tool name
            result = await query_service.direct_mcp_call(
                tool_name=request.query,
                client_id=request.client_id,
                params=request.tool_params
            )
        else:
            # Intelligent or Auto mode
            result = await query_service.query(
                natural_query=request.query,
                client_id=request.client_id,
                mode=mode,
                fallback_tool=request.fallback_tool,
                fallback_params=request.fallback_params
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log the result for debugging
        logger.info(f"Query result: {result}")
        
        return QueryResponse(
            success=result.get('success', False),
            query=request.query,
            client_id=request.client_id,
            mode=result.get('mode', request.mode),
            results=result.get('results') or result.get('data'),
            error=result.get('error', '') or result.get('details', ''),
            strategies_used=result.get('successful_strategies'),
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Natural language query failed: {e}")
        processing_time = (time.time() - start_time) * 1000
        
        return QueryResponse(
            success=False,
            query=request.query,
            client_id=request.client_id,
            mode=request.mode,
            error=str(e),
            processing_time_ms=processing_time
        )


@router.get("/suggest")
async def suggest_queries(
    context: str = QueryParam("general", description="Context for suggestions: calendar, performance, segments, etc.")
) -> Dict[str, Any]:
    """
    Get suggested natural language queries based on context.
    """
    suggestions = {
        "calendar": [
            "Show campaign performance for last month",
            "Get email engagement metrics for last 30 days",
            "Find top performing campaigns this quarter",
            "Show optimal send times based on opens",
            "List segments with highest engagement"
        ],
        "performance": [
            "Show email performance metrics for last 30 days",
            "Get click-through rates by campaign type",
            "Compare this month's performance to last month",
            "Show revenue by email campaign",
            "Find campaigns with highest conversion rates"
        ],
        "segments": [
            "List all active segments",
            "Show segment sizes and growth",
            "Find segments with recent activity",
            "Get engagement rates by segment",
            "Show segment overlap analysis"
        ],
        "campaigns": [
            "Show all campaigns from last week",
            "List scheduled campaigns",
            "Find campaigns targeting specific segment",
            "Show campaign performance summary",
            "Get campaigns with specific tags"
        ],
        "general": [
            "Show me all campaigns",
            "Get metrics for the last 30 days",
            "List all segments",
            "Show recent email performance",
            "Find active flows"
        ]
    }
    
    context_lower = context.lower()
    if context_lower in suggestions:
        return {
            "context": context,
            "suggestions": suggestions[context_lower]
        }
    else:
        return {
            "context": "general",
            "suggestions": suggestions["general"]
        }


@router.post("/test")
async def test_query_parsing(
    query: str = QueryParam(..., description="Natural language query to test")
) -> Dict[str, Any]:
    """
    Test the query parser without executing queries.
    Returns the strategies that would be executed.
    """
    from app.services.intelligent_query_service import QueryStrategyBuilder
    
    builder = QueryStrategyBuilder()
    strategies = builder.build(query)
    
    return {
        "query": query,
        "strategies": [
            {
                "tool": s.tool,
                "params": s.params,
                "description": s.description,
                "has_fallback": s.fallback_tool is not None
            }
            for s in strategies
        ],
        "total_strategies": len(strategies),
        "direct_tool_guess": builder.guess_direct_tool(query)
    }