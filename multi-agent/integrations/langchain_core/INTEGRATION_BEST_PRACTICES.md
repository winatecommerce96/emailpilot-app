# Enhanced MCP + LangChain Integration Best Practices

This document provides comprehensive best practices for implementing and maintaining the Enhanced MCP + LangChain integration in production environments.

## Architecture Best Practices

### 1. Tool Mapping and Adapter Design

**✅ DO:**
- Use the adapter pattern to maintain separation between Enhanced MCP and LangChain
- Implement non-destructive tool additions that preserve existing functionality  
- Provide clear mapping between Enhanced MCP tool names and LangChain tool names
- Include comprehensive error handling in tool adapters

**❌ DON'T:**
- Directly couple LangChain agents to Enhanced MCP APIs
- Replace existing tools without migration paths
- Ignore backward compatibility during updates

**Example:**
```python
# Good: Using the adapter pattern
from .adapters.enhanced_mcp_adapter import get_enhanced_mcp_tools

class MyAgent:
    def __init__(self):
        existing_tools = get_native_tools()
        enhanced_tools = get_enhanced_mcp_tools()
        self.tools = existing_tools + enhanced_tools  # Non-destructive

# Bad: Direct coupling
class MyAgent:
    def __init__(self):
        self.mcp_client = MCPClient()  # Direct dependency
        self.tools = []  # Replaces existing functionality
```

### 2. Context Management

**✅ DO:**
- Use hierarchical context scoping (system > client > session > task)
- Implement proper context cleanup and expiration
- Provide context inheritance between agents
- Use persistent storage for important context data

**❌ DON'T:**
- Store sensitive data in context without encryption
- Allow context to grow indefinitely without cleanup
- Share context across unrelated sessions

**Example:**
```python
# Good: Proper context scoping
context_manager.set_context(
    "client_api_key",
    encrypted_key,
    scope=ContextScope(level=1, name="client", persistent=True),
    context_id=client_id
)

# Bad: No scoping or security
context_manager.set_context("api_key", raw_key)  # Insecure, no scope
```

### 3. Agent Orchestration

**✅ DO:**
- Use LangGraph for visual workflow orchestration
- Implement proper state management with checkpoints
- Provide clear error handling and recovery paths
- Monitor agent performance and resource usage

**❌ DON'T:**
- Create monolithic agents that do everything
- Ignore inter-agent communication patterns
- Skip workflow visualization and debugging

**Example:**
```python
# Good: Structured workflow with state management
workflow = StateGraph(OrchestrationState)
workflow.add_node("analyze_data", analyze_historical_data)
workflow.add_node("generate_goals", generate_monthly_goals)  
workflow.add_edge("analyze_data", "generate_goals")
graph = workflow.compile(checkpointer=checkpointer)

# Bad: Manual agent chaining without state management
result1 = agent1.run(task)
result2 = agent2.run(result1)  # No state management, poor error handling
```

## Implementation Best Practices

### 1. Error Handling and Recovery

**✅ DO:**
- Implement graceful degradation when Enhanced MCP is unavailable
- Provide clear error messages with actionable information
- Use retry logic with exponential backoff for transient failures
- Log errors with sufficient context for debugging

**❌ DON'T:**
- Fail silently or with generic error messages
- Retry indefinitely without backoff
- Expose internal error details to end users

**Example:**
```python
# Good: Comprehensive error handling
async def call_enhanced_mcp(tool_name: str, arguments: Dict[str, Any], context: ToolContext):
    try:
        return await self._call_with_retry(tool_name, arguments, context)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            # Service unavailable - fall back to cached data
            return self._get_cached_result(tool_name, arguments)
        else:
            # Other HTTP errors - log and return structured error
            logger.error(f"Enhanced MCP call failed: {tool_name} - HTTP {e.response.status_code}")
            return {"success": False, "error": f"Service error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Unexpected error in Enhanced MCP call: {e}", exc_info=True)
        return {"success": False, "error": "An unexpected error occurred"}

# Bad: Poor error handling
def call_mcp(tool_name, args):
    result = requests.post(url, json=args)  # No error handling
    return result.json()  # Will crash on HTTP errors
```

### 2. Performance Optimization

**✅ DO:**
- Implement caching for frequently accessed data
- Use async/await for non-blocking operations
- Monitor and limit concurrent API calls
- Implement connection pooling for HTTP clients

**❌ DON'T:**
- Make synchronous API calls in async contexts
- Cache without TTL or invalidation strategies
- Ignore rate limits and API quotas

**Example:**
```python
# Good: Async with caching and rate limiting
class EnhancedMCPAdapter:
    def __init__(self):
        self.rate_limiter = AsyncRateLimiter(100, 60)  # 100 calls per minute
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5 minute TTL
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]):
        cache_key = f"{tool_name}:{hash(json.dumps(args, sort_keys=True))}"
        
        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        # Make API call
        async with self.http_client.post(url, json=args) as response:
            result = await response.json()
            
        # Cache successful results
        if result.get("success"):
            self.cache[cache_key] = result
            
        return result

# Bad: Blocking calls without caching
def call_tool(tool_name, args):
    response = requests.post(url, json=args, timeout=60)  # Blocks entire thread
    return response.json()  # No caching, no rate limiting
```

### 3. Security and Authentication

**✅ DO:**
- Store API keys securely using secret management systems
- Validate all inputs to prevent injection attacks
- Use HTTPS for all API communications
- Implement proper authentication and authorization

**❌ DON'T:**
- Store API keys in code or configuration files
- Trust user inputs without validation
- Log sensitive information like API keys or tokens

**Example:**
```python
# Good: Secure key management
from google.cloud import secretmanager

class SecureConfigManager:
    def __init__(self):
        self.secret_client = secretmanager.SecretManagerServiceClient()
    
    def get_api_key(self, client_id: str) -> str:
        secret_name = f"projects/{PROJECT_ID}/secrets/klaviyo-api-{client_id}/versions/latest"
        response = self.secret_client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")

# Bad: Insecure key management
API_KEYS = {
    "client1": "pk_abc123...",  # Hardcoded in source code
    "client2": "pk_def456..."   # Visible in version control
}
```

### 4. Testing and Validation

**✅ DO:**
- Write comprehensive unit tests for all components
- Implement integration tests with real Enhanced MCP services
- Use mocking for external dependencies in tests
- Test error conditions and edge cases

**❌ DON'T:**
- Skip testing of error handling paths
- Rely only on happy path testing
- Test against production APIs without proper data

**Example:**
```python
# Good: Comprehensive testing
import pytest
from unittest.mock import AsyncMock, patch

class TestEnhancedMCPAdapter:
    @pytest.fixture
    async def adapter(self):
        return EnhancedMCPAdapter(test_config)
    
    @pytest.mark.asyncio
    async def test_successful_tool_call(self, adapter):
        # Test successful API call
        result = await adapter.call_tool("campaigns.list", {"limit": 5})
        assert result["success"] is True
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_error_handling(self, adapter):
        # Test HTTP error handling
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError("Service unavailable", request=None, response=None)
            
            result = await adapter.call_tool("campaigns.list", {"limit": 5})
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, adapter):
        # Test rate limiting behavior
        tasks = [adapter.call_tool("metrics.list", {}) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should complete without rate limit errors
        assert all(r.get("success") for r in results)

# Bad: Minimal testing
def test_tool_call():
    adapter = EnhancedMCPAdapter()
    result = adapter.call_tool("campaigns.list", {})  # Only tests happy path
    assert result  # Weak assertion
```

## Deployment Best Practices

### 1. Environment Configuration

**✅ DO:**
- Use environment-specific configuration files
- Implement proper secret management for different environments
- Use infrastructure as code for consistent deployments
- Monitor resource usage and scale appropriately

**❌ DON'T:**
- Use the same configuration for all environments
- Deploy without proper health checks
- Ignore resource limits and quotas

### 2. Monitoring and Observability

**✅ DO:**
- Implement comprehensive logging with structured data
- Monitor key performance metrics (latency, error rates, throughput)
- Use distributed tracing for multi-agent workflows
- Set up alerting for critical failures

**❌ DON'T:**
- Log only errors without context
- Monitor without actionable alerts
- Ignore performance degradation over time

**Example:**
```python
# Good: Structured logging with context
import structlog

logger = structlog.get_logger()

async def execute_workflow(workflow_name: str, state: Dict[str, Any]):
    logger.info(
        "workflow_started",
        workflow_name=workflow_name,
        client_id=state.get("client_id"),
        session_id=state.get("session_id"),
        timestamp=datetime.utcnow().isoformat()
    )
    
    try:
        result = await self._run_workflow(workflow_name, state)
        
        logger.info(
            "workflow_completed",
            workflow_name=workflow_name,
            duration_ms=result.get("duration_ms"),
            success=True
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "workflow_failed",
            workflow_name=workflow_name,
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc()
        )
        raise

# Bad: Unstructured logging
def execute_workflow(workflow_name, state):
    print(f"Starting workflow {workflow_name}")  # Unstructured
    try:
        result = self._run_workflow(workflow_name, state)
        print("Done")  # No context
        return result
    except Exception as e:
        print(f"Error: {e}")  # No structured data
        raise
```

### 3. Documentation and Maintenance

**✅ DO:**
- Maintain comprehensive API documentation
- Document configuration options and environment variables
- Provide clear examples and tutorials
- Keep dependencies up to date with security patches

**❌ DON'T:**
- Deploy without documentation
- Ignore security updates
- Use deprecated libraries or APIs

## Migration Best Practices

### 1. Gradual Rollout

**✅ DO:**
- Implement feature flags for gradual enabling of Enhanced MCP tools
- Run parallel systems during migration period
- Monitor metrics before and after migration
- Provide rollback capabilities

**❌ DON'T:**
- Switch all agents to Enhanced MCP simultaneously
- Migrate without proper testing in production-like environments
- Remove old systems immediately after migration

### 2. Data Migration

**✅ DO:**
- Migrate context data with proper validation
- Maintain backward compatibility during transition
- Test data integrity after migration
- Backup data before migration

**❌ DON'T:**
- Migrate without data validation
- Lose historical context during migration
- Skip data integrity checks

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Enhanced MCP tools returning errors
**Symptoms:** Tools fail with HTTP errors or timeout exceptions
**Solutions:**
1. Check Enhanced MCP service health
2. Verify API keys and client configuration
3. Check network connectivity and firewall rules
4. Review rate limiting and quota usage

#### Issue: Context not persisting between agents
**Symptoms:** Agents don't have access to context from previous executions
**Solutions:**
1. Verify Firestore connectivity and permissions
2. Check context scope and TTL settings
3. Ensure proper context_id usage across agents
4. Review context cleanup and expiration logic

#### Issue: LangGraph workflows failing
**Symptoms:** Workflows fail at specific nodes or don't complete
**Solutions:**
1. Check agent execution logs for specific errors
2. Verify state transitions and edge conditions
3. Test individual agents outside of workflow
4. Review checkpoint storage and recovery

#### Issue: Performance degradation
**Symptoms:** Slow response times or high resource usage
**Solutions:**
1. Review caching configuration and hit rates
2. Monitor API call patterns and rate limiting
3. Check concurrent execution limits
4. Profile memory usage and garbage collection

## Conclusion

Following these best practices will ensure a robust, maintainable, and performant Enhanced MCP + LangChain integration. Regular review and updates of these practices as the system evolves will help maintain high quality and reliability.

Key principles to remember:
- **Separation of Concerns**: Keep Enhanced MCP, LangChain, and LangGraph components properly separated
- **Error Resilience**: Always plan for and handle failure scenarios gracefully
- **Performance**: Monitor and optimize for both latency and throughput
- **Security**: Never compromise on security for convenience
- **Observability**: Make the system easy to monitor, debug, and troubleshoot