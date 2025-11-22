# MCP Registry System Documentation

**Date:** 2025-01-11
**Status:** Current State Analysis
**Purpose:** Unified Service Discovery and Authentication Platform

## Executive Summary

The EmailPilot application uses a **Model Context Protocol (MCP) Registry** system for service discovery, health monitoring, and AI-enhanced tool management. The system consists of two complementary registries:

1. **MCPServerRegistry** - Basic server health monitoring and discovery
2. **UniversalMCPRegistry** - AI-enhanced tool registration with learning capabilities

### Current State
- **Registered Services:** 5 MCP servers defined
- **Operational Services:** 2 (both Klaviyo)
- **Planned Services:** 2 (Salesforce, Analytics)
- **Total Cloud Run Services:** 17 (from inventory)
- **Gap:** 12-14 services need registration

### Critical Gaps Identified
1. ❌ All URLs configured for `localhost`, not Cloud Run production
2. ❌ Only 5 of 17 services registered in the system
3. ❌ No Clerk authentication integration with registry
4. ❌ Health checks won't work for Cloud Run without URL updates
5. ❌ No connection between MCP registry and unified auth platform

---

## Architecture Overview

### MCPServerRegistry (`app/services/mcp_registry.py`)

**Purpose:** Manages external MCP servers with health monitoring and auto-discovery.

**Key Features:**
- Singleton pattern for global registry instance
- Async health checking with 5-second timeout
- Auto-discovery on ports 9090-9100
- Server status tracking (online, offline, error, unknown, planned)
- Capability categorization (campaigns, metrics, segments, profiles, flows, templates)

**Data Structure:**
```python
@dataclass
class MCPServerSpec:
    id: str                  # Unique server identifier
    name: str                # Human-readable name
    description: str         # Server description
    url: str                 # Base URL (currently localhost)
    port: int                # Server port
    type: str                # e.g., "marketing", "crm", "analytics"
    provider: str            # e.g., "klaviyo", "salesforce"
    version: str             # Server version
    status: str              # online/offline/error/unknown/planned
    capabilities: List[str]  # Tool categories available
    health_endpoint: str     # Health check endpoint (default: /health)
    tools_endpoint: str      # Tools listing endpoint
    invoke_endpoint: str     # Tool invocation endpoint
    auth_required: bool      # Whether auth is needed
    last_check: Optional[str]
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

**Default Registered Servers:**
1. **klaviyo_enhanced** (Port 9095) - Enhanced Klaviyo MCP
   - Type: marketing
   - Capabilities: campaigns, metrics, segments, profiles, flows, templates
   - Status: unknown → needs health check

2. **klaviyo_python** (Port 9090) - Python Klaviyo MCP
   - Type: marketing
   - Status: unknown → needs health check

3. **salesforce_mcp** - PLANNED (Q2 2025)
   - Type: crm
   - Status: planned

4. **analytics_mcp** - PLANNED (Q1 2025)
   - Type: analytics
   - Status: planned

5. **mcp_gateway** (Port 8000) - MCP Gateway
   - Type: gateway
   - URL: http://localhost:8000/api/mcp/gateway

**Health Check Logic:**
```python
async def _check_server_health(self, server_id: str) -> bool:
    server = self.servers[server_id]

    if server.status == "planned":
        return False

    try:
        response = await self.client.get(
            f"{server.url}{server.health_endpoint}",
            timeout=5.0
        )

        if response.status_code == 200:
            server.status = "online"
            server.last_check = datetime.now().isoformat()
            return True
        else:
            server.status = "error"
            return False
    except Exception as e:
        server.status = "offline"
        server.error_message = str(e)
        return False
```

### UniversalMCPRegistry (`app/services/universal_mcp_registry/registry.py`)

**Purpose:** AI-enhanced registry with automatic wrapper generation and learning capabilities.

**Key Features:**
- Automatic AI wrapper generation for MCP tools
- LangChain agent creation
- Pattern learning from usage
- Firestore-backed persistence
- Multi-LLM support (Claude, GPT-4, Gemini)

**Storage Collections:**
- `mcp_registry` - Server registrations and metadata
- `mcp_tools` - Individual tool registrations

**Registration Process:**
```python
async def register_new_mcp(self, mcp_config: Dict[str, Any]):
    1. Create tool registry entry
    2. Generate AI wrapper using AIWrapperGenerator
    3. Create LangChain agent using MCPAgentFactory
    4. Store in Firestore with metrics tracking
    5. Return wrapper endpoint
```

**Firestore Schema:**
```json
// mcp_registry collection
{
  "id": "mcp_id",
  "name": "MCP Name",
  "wrapper": {
    "endpoint": "/api/mcp/{mcp_id}/invoke",
    "class_name": "WrapperClassName",
    "llm_model": "claude-3-opus",
    "learning_enabled": true
  },
  "agent": {
    "name": "agent_name",
    "llm_model": "gpt-4"
  },
  "metrics": {
    "total_queries": 0,
    "success_rate": 0.0,
    "patterns_learned": 0
  }
}

// mcp_tools collection
{
  "mcp_id": "parent_mcp_id",
  "tool_id": "tool_identifier",
  "name": "Tool Name",
  "description": "Tool Description",
  "parameters": {...},
  "created_at": "2025-01-11T..."
}
```

---

## API Endpoints (`app/api/mcp_registry.py`)

### List Servers
```
GET /api/mcp/registry/servers
Query Parameters:
  - type: Filter by server type (marketing, crm, analytics)
  - capability: Filter by capability (campaigns, metrics, etc.)
  - status: Filter by status (online, offline, error)
  - online_only: Boolean to show only online servers

Response:
{
  "success": true,
  "count": 5,
  "servers": [...]
}
```

### Get Server Details
```
GET /api/mcp/registry/servers/{server_id}

Response:
{
  "success": true,
  "server": {...}
}
```

### Register New Server
```
POST /api/mcp/registry/servers/register
Body: RegisterServerRequest
{
  "id": "server_id",
  "name": "Server Name",
  "url": "http://...",
  "port": 9090,
  "type": "marketing",
  "provider": "provider_name",
  "capabilities": ["campaigns", "metrics"]
}

Response:
{
  "success": true,
  "server_id": "server_id",
  "message": "Server registered successfully"
}
```

### Unregister Server
```
DELETE /api/mcp/registry/servers/{server_id}

Response:
{
  "success": true,
  "message": "Server unregistered successfully"
}
```

### Check All Health
```
POST /api/mcp/registry/health/check-all

Response:
{
  "success": true,
  "total_servers": 5,
  "online": 2,
  "offline": 1,
  "error": 0,
  "planned": 2
}
```

### Discover Servers
```
POST /api/mcp/registry/discover
Query Parameters:
  - start_port: Starting port (default: 9090)
  - end_port: Ending port (default: 9100)

Response:
{
  "success": true,
  "discovered": 2,
  "servers": [...]
}
```

---

## Cloud Run Services Inventory

### Currently in MCP Registry (5 services)
1. ✅ klaviyo_enhanced (localhost:9095)
2. ✅ klaviyo_python (localhost:9090)
3. 🔮 salesforce_mcp (planned Q2 2025)
4. 🔮 analytics_mcp (planned Q1 2025)
5. ✅ mcp_gateway (localhost:8000)

### Cloud Run Services NOT in Registry (12+ services)

From the completed inventory (Task #1), these services need registration:

#### MCP Services
1. **mcp-health** - MCP Health Check Service
   - URL: https://mcp-health-935786836546.us-central1.run.app
   - Type: monitoring
   - Capabilities: health_checks, system_status

2. **mcp-models** - MCP Models Service
   - URL: https://mcp-models-935786836546.us-central1.run.app
   - Type: ai
   - Capabilities: model_management, llm_selection

3. **klaviyo-mcp-service** - Klaviyo MCP Service
   - URL: https://klaviyo-mcp-service-935786836546.us-central1.run.app
   - Type: marketing
   - Capabilities: campaigns, metrics, segments, profiles

#### Client-Specific Services (7 Klaviyo clients)
4. **Colorado Hemp Honey Klaviyo**
5. **Rogue Creamery Klaviyo**
6. **Vlasic Klaviyo**
7. **FASO Klaviyo**
8. **Milagro Klaviyo**
9. **Wheelchair Getaways Klaviyo**
10. **Chris Bean Klaviyo**

#### Core Application Services
11. **emailpilot-app** - Main EmailPilot Application
    - URL: https://emailpilot-app-935786836546.us-central1.run.app
    - Type: application
    - Capabilities: calendar, auth, admin

12. **emailpilot-simple** - Simplified EmailPilot
    - URL: https://emailpilot-simple-p3cxgvcsla-uc.a.run.app
    - Type: application
    - Capabilities: basic_email_automation

---

## Critical Gaps Analysis

### 1. URL Configuration Gap
**Problem:** All registered servers use `localhost` URLs
**Impact:** Health checks fail for deployed Cloud Run services
**Required Action:** Update all URLs to Cloud Run production URLs

**Example Fix Needed:**
```python
# Current
url="http://localhost:9095"

# Should be
url="https://klaviyo-mcp-service-935786836546.us-central1.run.app"
```

### 2. Service Coverage Gap
**Problem:** Only 5 servers registered vs. 17 Cloud Run services
**Impact:** 12+ services not discoverable through registry
**Required Action:** Register all Cloud Run services with proper metadata

### 3. Authentication Integration Gap
**Problem:** Registry tracks `auth_required` but doesn't integrate with Clerk
**Impact:** No unified authentication across services
**Required Action:** Connect MCP registry with Clerk authentication system

**Integration Points Needed:**
- Add Clerk token validation to MCP registry
- Include auth tokens in health check requests
- Store Clerk user ID with service registrations
- Implement service-level access control

### 4. Health Monitoring Gap
**Problem:** Health checks only work for localhost services
**Impact:** Can't monitor production service availability
**Required Action:**
- Update health check URLs to Cloud Run endpoints
- Add authentication headers for protected services
- Implement retry logic for transient failures

### 5. Calendar OAuth Removal Gap
**Problem:** Calendar still has OAuth code (Task #2 pending)
**Impact:** Conflicting authentication systems
**Required Action:** Remove calendar-specific OAuth, use Clerk exclusively

---

## Recommendations

### Immediate Actions (Priority 1)
1. ✅ **Complete this documentation** (Task #7)
2. 🔄 **Register remaining 14 services** (Task #8)
   - Use Cloud Run production URLs
   - Include proper capabilities metadata
   - Set correct authentication flags
3. 🔄 **Update production URLs** (Task #9)
   - Replace all localhost URLs
   - Add environment variable support
   - Test health checks against production

### Short-term Actions (Priority 2)
4. **Integrate Clerk authentication**
   - Add Clerk middleware to MCP endpoints
   - Store user-service access mappings
   - Implement service-level permissions
5. **Remove calendar OAuth code** (Task #2)
   - Clean up Google OAuth flows
   - Migrate to Clerk exclusively
6. **Test unified auth platform** (Task #10)
   - Verify all 17 services authenticate through Clerk
   - Test cross-service communication
   - Validate access controls

### Long-term Actions (Priority 3)
7. **Implement auto-discovery for Cloud Run**
   - Use GCP APIs to discover running services
   - Auto-register new deployments
   - Update URLs on service restart
8. **Add comprehensive monitoring**
   - Service uptime tracking
   - Error rate monitoring
   - Performance metrics
9. **Build admin dashboard**
   - Visual registry management
   - Health status overview
   - Service configuration UI

---

## Technical Debt

### Code Organization
- Two separate registry systems (MCPServerRegistry + UniversalMCPRegistry) with overlapping responsibilities
- Inconsistent naming (MCP Registry vs. ACL System)
- Firestore schema not versioned

### Configuration Management
- Hardcoded localhost URLs
- No environment-specific configurations
- Port ranges hardcoded (9090-9100)

### Error Handling
- Generic exception catching in health checks
- No retry logic for transient failures
- Limited error reporting

### Testing
- No unit tests for registry operations
- No integration tests for health checks
- No mock servers for testing

---

## Next Steps

**Task #8: Register Remaining 14 Services**
- Create server specs for all 17 Cloud Run services
- Use production URLs from inventory
- Test health checks for each service
- Verify registration in Firestore

**Task #9: Update Production URLs**
- Audit all localhost references
- Replace with Cloud Run URLs
- Add environment variable support
- Test health monitoring

**Task #10: Test Unified Auth Platform**
- Verify Clerk authentication works across all services
- Test service-to-service communication
- Validate access control rules
- Document authentication flow

---

## Appendix A: Server Registration Template

```python
MCPServerSpec(
    id="service_name",
    name="Human Readable Name",
    description="Service description",
    url="https://service-name-935786836546.us-central1.run.app",
    port=443,  # HTTPS
    type="service_type",  # marketing, crm, analytics, monitoring, ai, application
    provider="provider_name",  # klaviyo, google, anthropic, internal
    version="1.0.0",
    status="unknown",  # Will be checked
    capabilities=[
        "capability1",
        "capability2"
    ],
    health_endpoint="/health",
    tools_endpoint="/api/tools",
    invoke_endpoint="/api/invoke",
    auth_required=True,  # All production services require auth
    metadata={
        "cloud_run_service": True,
        "region": "us-central1",
        "project_id": "935786836546",
        "clerk_enabled": True
    }
)
```

## Appendix B: Health Check Implementation

```python
# For Cloud Run services with authentication
async def check_cloud_run_health(
    url: str,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """Check health of Cloud Run service with optional auth"""
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{url}/health",
                headers=headers,
                timeout=10.0,
                follow_redirects=True
            )

            return {
                "status": "online" if response.status_code == 200 else "error",
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "last_check": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "offline",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
```

---

**Document Version:** 1.0
**Last Updated:** 2025-01-11
**Author:** EmailPilot Engineering Team
**Status:** ✅ Complete
