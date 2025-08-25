"""
Debug wrapper for LangChain Klaviyo queries to trace errors in advanced queries.
"""

import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/langchain/debug", tags=["LangChain Debug"])


class DebugQuery(BaseModel):
    query: str
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    trace_level: str = "verbose"  # minimal, normal, verbose


class DebugTrace(BaseModel):
    timestamp: str
    stage: str
    status: str  # success, warning, error
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class DebugResponse(BaseModel):
    query: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    traces: List[DebugTrace] = []
    total_duration_ms: float
    recommendations: List[str] = []


class QueryDebugger:
    """Debug wrapper for tracing query processing stages."""
    
    def __init__(self):
        self.traces: List[DebugTrace] = []
        self.start_time = None
        self.recommendations: List[str] = []
        
    def start(self):
        """Start timing the query."""
        self.start_time = datetime.now()
        self.traces = []
        self.recommendations = []
        
    def add_trace(self, stage: str, status: str, message: str, 
                  data: Optional[Dict] = None, error: Optional[str] = None):
        """Add a trace entry."""
        trace = DebugTrace(
            timestamp=datetime.now().isoformat(),
            stage=stage,
            status=status,
            message=message,
            data=data,
            error=error,
            duration_ms=self._get_duration()
        )
        self.traces.append(trace)
        
        # Log the trace
        log_msg = f"[{stage}] {status}: {message}"
        if error:
            logger.error(f"{log_msg} - Error: {error}")
        elif status == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
            
    def _get_duration(self) -> float:
        """Get duration since start in milliseconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds() * 1000
        return 0
        
    def add_recommendation(self, recommendation: str):
        """Add a recommendation based on the debug analysis."""
        self.recommendations.append(recommendation)


@router.post("/trace")
async def debug_query(request: DebugQuery) -> DebugResponse:
    """
    Debug a natural language query with detailed tracing.
    
    Traces through:
    1. Query parsing and interpretation
    2. Client resolution
    3. Date range parsing
    4. Tool/endpoint selection
    5. API call construction
    6. Response processing
    """
    debugger = QueryDebugger()
    debugger.start()
    
    try:
        # Stage 1: Query Analysis
        debugger.add_trace(
            "query_analysis", 
            "success",
            "Starting query analysis",
            {"original_query": request.query}
        )
        
        # Import the processor singleton
        try:
            from app.api.langchain_klaviyo import processor
            debugger.add_trace(
                "initialization",
                "success", 
                "Initialized KlaviyoQueryProcessor"
            )
        except Exception as e:
            debugger.add_trace(
                "initialization",
                "error",
                "Failed to initialize processor",
                error=str(e)
            )
            raise
            
        # Stage 2: Parse complex date ranges
        debugger.add_trace(
            "date_parsing",
            "success",
            "Attempting to parse date ranges"
        )
        
        date_range = processor.parse_complex_date_range(request.query)
        individual_ranges = processor.get_individual_month_ranges(request.query)
        
        if individual_ranges and len(individual_ranges) > 1:
            # Multiple month ranges detected
            debugger.add_trace(
                "date_parsing",
                "success",
                f"Parsed {len(individual_ranges)} separate month ranges",
                {"ranges": individual_ranges, "note": "Each month should be queried separately"}
            )
        elif date_range:
            debugger.add_trace(
                "date_parsing",
                "success",
                f"Parsed date range: {date_range[0]} to {date_range[1]}",
                {"start": date_range[0], "end": date_range[1]}
            )
        else:
            debugger.add_trace(
                "date_parsing",
                "warning",
                "No date range found in query"
            )
            
        # Stage 3: Extract client info
        client_info = processor.extract_client_info(request.query)
        if client_info and client_info.get('client_hint'):
            debugger.add_trace(
                "client_extraction",
                "success",
                f"Extracted client: {client_info.get('client_hint')}",
                client_info
            )
        else:
            debugger.add_trace(
                "client_extraction",
                "warning",
                f"No client found - hint: {client_info.get('client_hint') if client_info else None}",
                client_info if client_info else {}
            )
            debugger.add_recommendation(
                "Include a client name in your query for better results"
            )
            
        # Stage 4: Interpret query to determine intent
        interpretation = processor.interpret_query(request.query)
        query_type = interpretation.get("tool", {}).get("type", "unknown")
        debugger.add_trace(
            "query_type",
            "success",
            f"Determined query type: {query_type}",
            {"type": query_type, "interpretation": interpretation}
        )
        
        # Stage 5: Select appropriate tool
        tool = interpretation.get("tool")
        if tool:
            debugger.add_trace(
                "tool_selection",
                "success",
                f"Selected tool: {tool}",
                {"tool": tool}
            )
        else:
            debugger.add_trace(
                "tool_selection",
                "error",
                "Could not determine appropriate tool"
            )
            debugger.add_recommendation(
                "Try rephrasing your query to be more specific about what data you need"
            )
            
        # Stage 6: Process the query
        debugger.add_trace(
            "query_processing",
            "success",
            "Processing natural language query"
        )
        
        # Make the actual API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8000/api/langchain/klaviyo/query",
                    json={"query": request.query}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    debugger.add_trace(
                        "api_call",
                        "success",
                        "API call successful",
                        {"status_code": response.status_code}
                    )
                    
                    # Analyze the result
                    if "error" in result:
                        debugger.add_trace(
                            "result_analysis",
                            "error",
                            "Query returned an error",
                            error=result["error"]
                        )
                        
                        # Add specific recommendations based on error
                        if "404" in str(result["error"]):
                            debugger.add_recommendation(
                                "The requested endpoint may not exist. Check if the client ID is correct."
                            )
                        elif "authentication" in str(result["error"]).lower():
                            debugger.add_recommendation(
                                "Check if the API key is properly configured for this client."
                            )
                    else:
                        debugger.add_trace(
                            "result_analysis",
                            "success",
                            "Query completed successfully",
                            {"result_keys": list(result.keys()) if isinstance(result, dict) else "list"}
                        )
                        
                    return DebugResponse(
                        query=request.query,
                        success=True,
                        result=result,
                        traces=debugger.traces,
                        total_duration_ms=debugger._get_duration(),
                        recommendations=debugger.recommendations
                    )
                else:
                    debugger.add_trace(
                        "api_call",
                        "error",
                        f"API call failed with status {response.status_code}",
                        {"status_code": response.status_code, "response": response.text}
                    )
                    raise HTTPException(status_code=response.status_code, detail=response.text)
                    
            except httpx.RequestError as e:
                debugger.add_trace(
                    "api_call",
                    "error",
                    "Network error during API call",
                    error=str(e)
                )
                debugger.add_recommendation(
                    "Check if the LangChain service is running on port 8000"
                )
                raise
                
    except Exception as e:
        debugger.add_trace(
            "general_error",
            "error",
            "Unexpected error during query processing",
            error=str(e)
        )
        
        return DebugResponse(
            query=request.query,
            success=False,
            error=str(e),
            traces=debugger.traces,
            total_duration_ms=debugger._get_duration(),
            recommendations=debugger.recommendations
        )


@router.post("/analyze-pattern")
async def analyze_query_pattern(request: DebugQuery) -> Dict[str, Any]:
    """
    Analyze a query pattern to understand how it will be processed.
    """
    from app.api.langchain_klaviyo import processor
    
    analysis = {
        "query": request.query,
        "patterns_matched": [],
        "date_parsing": None,
        "client_detection": None,
        "tool_selection": None,
        "endpoint_mapping": None
    }
    
    # Check which patterns match
    import re
    for pattern_type, tool_config in processor.tool_patterns.items():
        if isinstance(tool_config, dict) and "patterns" in tool_config:
            for pattern in tool_config["patterns"]:
                if re.search(pattern, request.query.lower()):
                analysis["patterns_matched"].append({
                    "type": pattern_type,
                    "pattern": pattern
                })
                
    # Check date parsing
    date_range = processor.parse_complex_date_range(request.query)
    if date_range:
        analysis["date_parsing"] = {
            "detected": True,
            "start": date_range[0],
            "end": date_range[1]
        }
    else:
        analysis["date_parsing"] = {
            "detected": False,
            "hint": "No date range patterns found"
        }
        
    # Check client detection
    client_info = processor.extract_client_info(request.query)
    if client_info:
        analysis["client_detection"] = client_info
    else:
        analysis["client_detection"] = {
            "detected": False,
            "hint": "No client name found in query"
        }
        
    # Determine tool selection using interpret_query
    interpretation = processor.interpret_query(request.query)
    tool = interpretation.get("tool")
    analysis["tool_selection"] = tool.get("type") if tool else "No tool matched"
    
    # Map to endpoint
    if tool:
        endpoint_map = {
            "revenue": "/clients/{client_id}/revenue/last7",
            "weekly_metrics": "/clients/{client_id}/weekly/metrics",
            "campaigns": "/clients/{client_id}/campaigns",
            "flows": "/clients/{client_id}/flows",
            "profiles": "/clients/{client_id}/profiles",
            "events": "/clients/{client_id}/events",
            "segments": "/clients/{client_id}/segments"
        }
        analysis["endpoint_mapping"] = endpoint_map.get(tool, "Unknown endpoint")
        
    return analysis


@router.post("/ai-fix")
async def ai_fix_error(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI-powered error analysis and fix generation.
    Analyzes debug traces and generates code fixes.
    """
    traces = request.get("traces", [])
    error = request.get("error", "")
    query = request.get("query", "")
    
    # Analyze the error pattern
    fix_suggestions = []
    code_changes = []
    
    # Common error patterns and fixes
    if "404 Not Found" in error:
        if "/revenue/custom" in error:
            fix_suggestions.append({
                "type": "endpoint_missing",
                "description": "The /revenue/custom endpoint doesn't exist",
                "fix": "Use /revenue/last7 with start and end parameters instead",
                "code": {
                    "file": "services/klaviyo_api/main.py",
                    "action": "add_endpoint",
                    "snippet": """@app.get("/clients/{client_id}/revenue/custom")
async def revenue_custom(client_id: str, start: str, end: str):
    # Custom date range revenue endpoint
    return await revenue_last7(client_id, start=start, end=end)"""
                }
            })
        elif "/campaigns" in error:
            fix_suggestions.append({
                "type": "endpoint_error",
                "description": "Campaigns endpoint configuration issue",
                "fix": "Check if Klaviyo API key has proper permissions"
            })
            
    elif "fields must be in" in error:
        # Field name mismatch
        import re
        field_match = re.search(r"fields must be in \[(.*?)\].*got \[(.*?)\]", error)
        if field_match:
            valid_fields = field_match.group(1)
            invalid_fields = field_match.group(2)
            fix_suggestions.append({
                "type": "field_mismatch",
                "description": f"Invalid field names: {invalid_fields}",
                "fix": f"Use valid fields: {valid_fields}",
                "code": {
                    "file": "services/klaviyo_api/main.py",
                    "action": "update_fields",
                    "search": invalid_fields,
                    "replace": valid_fields.split(",")[0:3]  # Use first 3 valid fields
                }
            })
            
    elif "No client information found" in str(traces):
        fix_suggestions.append({
            "type": "query_improvement",
            "description": "Query missing client name",
            "fix": "Add client name to your query",
            "example": f"{query} for Rogue Creamery"
        })
        
    elif "No date range found" in str(traces):
        fix_suggestions.append({
            "type": "query_improvement",
            "description": "Query missing date range",
            "fix": "Add a date range like 'month to date' or 'last 30 days'",
            "example": f"{query} for the last 30 days"
        })
    
    # Generate automated fix script if code changes identified
    if any(s.get("code") for s in fix_suggestions):
        code_changes = [s["code"] for s in fix_suggestions if s.get("code")]
        
    return {
        "query": query,
        "error_analysis": {
            "error_type": "endpoint" if "404" in error else "api" if "400" in error else "unknown",
            "error_message": error[:200] if error else "No error message"
        },
        "fix_suggestions": fix_suggestions,
        "code_changes": code_changes,
        "can_auto_fix": len(code_changes) > 0,
        "confidence": 0.8 if fix_suggestions else 0.3
    }


@router.post("/apply-fix")
async def apply_ai_fix(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply an AI-suggested fix to the codebase.
    """
    code_change = request.get("code_change", {})
    
    if not code_change:
        raise HTTPException(status_code=400, detail="No code change provided")
    
    try:
        file_path = code_change.get("file")
        action = code_change.get("action")
        
        if action == "add_endpoint":
            # Add new endpoint to file
            snippet = code_change.get("snippet", "")
            # In real implementation, would modify the file
            # For safety, just return what would be done
            return {
                "status": "preview",
                "message": f"Would add endpoint to {file_path}",
                "preview": snippet,
                "applied": False
            }
            
        elif action == "update_fields":
            # Update field names
            search = code_change.get("search", "")
            replace = code_change.get("replace", [])
            return {
                "status": "preview",
                "message": f"Would update fields in {file_path}",
                "change": f"Replace '{search}' with '{','.join(replace)}'",
                "applied": False
            }
            
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
            
    except Exception as e:
        logger.error(f"Error applying fix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query-patterns")
async def get_query_patterns() -> Dict[str, Any]:
    """
    Get current query patterns and handlers for editing.
    """
    from app.api.langchain_klaviyo import processor
    
    return {
        "tool_patterns": processor.tool_patterns,
        "complex_date_patterns": processor.complex_date_patterns,
        "client_patterns": [
            r'\b(rogue\s*creamery|tillamook|oregon\s*fruit|face\s*rock|pendleton|widmer|portland\s*gear)\b',
            r'for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'client\s+([A-Za-z0-9_-]+)'
        ],
        "endpoints": {
            "revenue": "/clients/{client_id}/revenue/last7",
            "weekly_metrics": "/clients/{client_id}/weekly/metrics", 
            "campaigns": "/clients/{client_id}/campaigns",
            "flows": "/clients/{client_id}/flows",
            "profiles": "/clients/{client_id}/profiles",
            "events": "/clients/{client_id}/events",
            "segments": "/clients/{client_id}/segments",
            "lists": "/clients/{client_id}/lists",
            "templates": "/clients/{client_id}/templates"
        }
    }


@router.post("/update-pattern")
async def update_query_pattern(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a query pattern or handler.
    """
    pattern_type = request.get("pattern_type")  # tool_patterns, date_patterns, etc.
    pattern_key = request.get("pattern_key")    # revenue, campaigns, etc.
    new_patterns = request.get("patterns")      # List of regex patterns
    
    # In production, this would update the actual processor
    # For now, return what would be updated
    return {
        "status": "preview",
        "message": f"Would update {pattern_type}.{pattern_key}",
        "current_patterns": new_patterns,
        "note": "Pattern updates require service restart to take effect"
    }


@router.post("/test-pattern")
async def test_query_pattern(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test a query against a pattern to see if it matches.
    """
    query = request.get("query", "")
    pattern = request.get("pattern", "")
    
    import re
    try:
        match = re.search(pattern, query.lower())
        return {
            "query": query,
            "pattern": pattern,
            "matches": bool(match),
            "match_details": {
                "matched_text": match.group(0) if match else None,
                "groups": match.groups() if match else None,
                "span": match.span() if match else None
            } if match else None
        }
    except re.error as e:
        return {
            "query": query,
            "pattern": pattern,
            "matches": False,
            "error": f"Invalid regex pattern: {str(e)}"
        }


@router.get("/test-endpoints")
async def test_klaviyo_endpoints() -> Dict[str, Any]:
    """
    Test all Klaviyo API endpoints to verify they're working.
    """
    results = {}
    test_client_id = "x4Sp2G7srfwLA0LPksUX"  # Rogue Creamery
    
    endpoints = [
        ("Revenue", f"http://localhost:9090/clients/{test_client_id}/revenue/last7"),
        ("Weekly Metrics", f"http://localhost:9090/clients/{test_client_id}/weekly/metrics"),
        ("Campaigns", f"http://localhost:9090/clients/{test_client_id}/campaigns?limit=2"),
        ("Flows", f"http://localhost:9090/clients/{test_client_id}/flows?limit=2"),
        ("Profiles", f"http://localhost:9090/clients/{test_client_id}/profiles?limit=2"),
        ("Events", f"http://localhost:9090/clients/{test_client_id}/events?limit=2"),
        ("Metrics", f"http://localhost:9090/clients/{test_client_id}/metrics?limit=2"),
        ("Segments", f"http://localhost:9090/clients/{test_client_id}/segments?limit=2"),
        ("Lists", f"http://localhost:9090/clients/{test_client_id}/lists?limit=2"),
        ("Templates", f"http://localhost:9090/clients/{test_client_id}/templates?limit=2")
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, url in endpoints:
            try:
                response = await client.get(url)
                results[name] = {
                    "status": "success" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "url": url
                }
                if response.status_code != 200:
                    results[name]["error"] = response.text[:200]
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "url": url
                }
                
    return results