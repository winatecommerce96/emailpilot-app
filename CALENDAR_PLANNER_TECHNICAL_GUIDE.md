# Calendar Planner Technical Documentation

## System Architecture Overview

The Calendar Planner is a sophisticated AI-powered campaign planning system that leverages LangChain's multi-agent framework to generate comprehensive email and SMS marketing calendars. This document explains the complete technical implementation from frontend to backend.

## Table of Contents
1. [Architecture Components](#architecture-components)
2. [Frontend Implementation](#frontend-implementation)
3. [LangChain Agent System](#langchain-agent-system)
4. [API Integration Layer](#api-integration-layer)
5. [Data Flow](#data-flow)
6. [MCP Integration Points](#mcp-integration-points)
7. [Tools and Services](#tools-and-services)
8. [Variable System](#variable-system)
9. [Execution Pipeline](#execution-pipeline)
10. [Error Handling](#error-handling)

---

## 1. Architecture Components

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (HTML/JS)                       │
│                  calendar_planner.html                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend                             │
│            /api/admin/langchain/agents/                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              LangChain Agent Registry                        │
│         multi-agent/integrations/langchain_core/             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            Calendar Planner Agent                            │
│    agents/calendar_planner.py + Prompt Template              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              External Services & Tools                       │
│   - Klaviyo API (campaigns, segments, metrics)               │
│   - Firestore (client data, configuration)                   │
│   - AI Models (GPT-4/Claude for generation)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Frontend Implementation

### File: `/frontend/public/calendar_planner.html`

#### Key Components:

##### A. Form Data Collection
```javascript
// Collects these required variables:
const variables = {
    client_name: string,              // e.g., "Milagro Mushrooms"
    selected_month: string,            // YYYY-MM format
    client_sales_goal: number,         // Monthly revenue target
    affinity_segment_1_name: string,   // Primary customer segment
    affinity_segment_2_name: string,   // Secondary segment
    affinity_segment_3_name: string,   // Optional tertiary segment
    key_growth_objective: string,      // Primary business goal
    key_dates: string,                 // JSON of promotional dates
    unengaged_segment_size: number     // Size of at-risk customers
}
```

##### B. API Communication
```javascript
// Makes POST request to LangChain agent endpoint
const task = `Create campaign calendar for ${client_name} for ${selected_month}`;
const response = await fetch(
    `${API_BASE}/api/admin/langchain/agents/calendar_planner/runs?task=${task}`,
    {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variables: variables })
    }
);
```

##### C. Result Processing
- Parses JSON response containing campaign array
- Displays campaigns in organized UI
- Calculates statistics (email vs SMS counts)
- Provides CSV export functionality

---

## 3. LangChain Agent System

### File: `/multi-agent/integrations/langchain_core/agents/calendar_planner.py`

#### Agent Definition Structure:
```python
CALENDAR_PLANNER_AGENT = {
    "name": "calendar_planner",
    "description": "Expert calendar planner for email and SMS campaigns",
    "version": "1.0",
    "status": "active",
    "default_task": "Create campaign calendar for {client_name}",
    "policy": {
        "max_tool_calls": 20,        # Maximum external API calls
        "timeout_seconds": 120,       # Execution timeout
        "allowed_tools": [            # Available tools for the agent
            "klaviyo_campaigns",
            "klaviyo_segments",
            "firestore_ro",
            "calculate",
            "generate_campaign_ideas"
        ]
    },
    "variables": [...],              # Input parameters
    "prompt_template": "..."         # AI instruction template
}
```

#### Core Functions:

##### A. Campaign Generation Logic
```python
def format_campaign_plan(raw_output: str) -> List[Dict[str, Any]]:
    """
    Converts agent's text output to structured JSON
    Parses tab-separated values into campaign objects
    """
    campaigns = []
    for line in raw_output.split('\n'):
        if '\t' in line:
            parts = line.split('\t')
            campaign = {
                "week": parts[0],
                "sendDate": parts[1],
                "sendTime": parts[2],
                "segments": parts[3],
                "subjectLineAB": parts[4],
                "previewText": parts[5],
                "heroH1": parts[6],
                "subhead": parts[7],
                "heroImage": parts[8],
                "ctaCopy": parts[9],
                "offer": parts[10],
                "abTestIdea": parts[11],
                "secondaryMessageSMS": parts[12]
            }
            campaigns.append(campaign)
    return campaigns
```

##### B. Validation System
```python
def validate_campaign_plan(plan: List[Dict], requirements: Dict) -> Dict:
    """
    Validates campaign plan against business rules:
    - Checks for 20 email campaigns minimum
    - Validates 4 SMS campaigns
    - Ensures max 2 sends per week
    - Verifies revenue distribution across segments
    """
    validation = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {}
    }
    # Validation logic...
    return validation
```

---

## 4. API Integration Layer

### File: `/multi-agent/integrations/langchain_core/admin/api.py`

#### Endpoint: `POST /api/admin/langchain/agents/{agent_id}/runs`

```python
@router.post("/agents/{agent_id}/runs")
async def start_agent_run(
    agent_id: str,
    task: str = Query(...),           # Task description
    brand: Optional[str] = None,
    variables: Optional[Dict] = None   # Agent-specific parameters
):
    """
    Initiates agent execution:
    1. Validates agent exists in registry
    2. Checks required variables
    3. Creates execution context
    4. Returns run_id for tracking
    """
    run_id = str(uuid.uuid4())
    # Agent execution logic...
    return {
        "run_id": run_id,
        "agent_id": agent_id,
        "status": "running",
        "task": task,
        "variables": variables
    }
```

---

## 5. Data Flow

### Complete Request/Response Cycle:

```
1. User Input (Frontend)
   ↓
2. Form Validation & Variable Collection
   ↓
3. HTTP POST to LangChain API
   ↓
4. Agent Registry Lookup
   ↓
5. Variable Injection into Prompt Template
   ↓
6. AI Model Invocation (GPT-4/Claude)
   ↓
7. Tool Execution (if needed):
   - Klaviyo API calls for historical data
   - Firestore queries for client config
   - Calculation tools for metrics
   ↓
8. Response Generation & Formatting
   ↓
9. Validation & Post-processing
   ↓
10. JSON Response to Frontend
   ↓
11. UI Display & Export Options
```

---

## 6. MCP Integration Points

While the Calendar Planner doesn't directly use MCP (Model Context Protocol), it integrates with MCP-enabled services:

### A. Klaviyo MCP Integration
```python
# The agent can access Klaviyo data through MCP tools
available_mcp_tools = [
    "klaviyo_campaigns",      # Get historical campaign data
    "klaviyo_segments",       # Retrieve segment information
    "klaviyo_metrics"         # Access performance metrics
]

# Example MCP tool call within agent:
klaviyo_data = await mcp_client.call_tool(
    "klaviyo_campaigns",
    {
        "client_id": client_id,
        "date_range": selected_month
    }
)
```

### B. Firestore MCP Access
```python
# Client configuration retrieval
client_config = await mcp_client.call_tool(
    "firestore_ro",
    {
        "collection": "clients",
        "document": client_name
    }
)
```

---

## 7. Tools and Services

### Available Tools for Calendar Planner Agent:

#### A. Klaviyo Tools
- **klaviyo_campaigns**: Retrieves historical campaign performance
- **klaviyo_segments**: Gets segment sizes and characteristics
- **klaviyo_flows**: Analyzes automated flow performance
- **klaviyo_metrics**: Pulls revenue and engagement metrics

#### B. Data Tools
- **firestore_ro**: Read-only access to Firestore database
- **calculate**: Mathematical operations for revenue projections
- **date_tools**: Date manipulation and calendar calculations

#### C. AI Tools
- **generate_campaign_ideas**: Uses AI to create campaign concepts
- **optimize_send_times**: Analyzes best send times
- **segment_analyzer**: Determines optimal segment targeting

---

## 8. Variable System

### Dynamic Variable Resolution:

The system supports 53+ dynamic variables that are resolved at runtime:

```python
# Variable categories:
1. User Input Variables (from form)
   - client_name, selected_month, etc.

2. System Variables (auto-populated)
   - current_date, timezone, user_id

3. Firestore Variables (from database)
   - client.klaviyo_api_key
   - client.industry
   - client.average_order_value

4. Calculated Variables (derived)
   - days_in_month
   - weekly_revenue_target (client_sales_goal / 4)
   - segment_revenue_targets

# Variable injection example:
prompt = prompt_template.format(
    client_name=variables['client_name'],
    selected_month=variables['selected_month'],
    client_sales_goal=variables['client_sales_goal'],
    # ... all other variables
)
```

### Variable Validation:
```python
def validate_variables(agent_def: Dict, provided_vars: Dict) -> Dict:
    """
    Ensures all required variables are present
    Validates types and formats
    Applies default values where defined
    """
    errors = []
    for var_def in agent_def['variables']:
        if var_def['required'] and var_def['name'] not in provided_vars:
            errors.append(f"Missing required variable: {var_def['name']}")
        # Type checking, pattern matching, etc.
    return {"valid": len(errors) == 0, "errors": errors}
```

---

## 9. Execution Pipeline

### Detailed Execution Flow:

```python
class CalendarPlannerExecutor:
    async def execute(self, variables: Dict) -> Dict:
        """
        Main execution pipeline for calendar planning
        """
        # Step 1: Context Preparation
        context = await self.prepare_context(variables)
        
        # Step 2: Historical Data Retrieval
        historical_data = await self.fetch_historical_data(
            variables['client_name'],
            variables['selected_month']
        )
        
        # Step 3: Segment Analysis
        segments = await self.analyze_segments(
            variables['affinity_segment_1_name'],
            variables['affinity_segment_2_name'],
            variables.get('affinity_segment_3_name')
        )
        
        # Step 4: AI Generation
        prompt = self.build_prompt(variables, context, historical_data, segments)
        ai_response = await self.llm.generate(prompt)
        
        # Step 5: Parse and Structure Output
        campaigns = self.parse_campaigns(ai_response)
        
        # Step 6: Validation
        validation = self.validate_campaigns(campaigns, variables)
        
        # Step 7: Optimization
        optimized = self.optimize_schedule(campaigns)
        
        return {
            "campaigns": optimized,
            "validation": validation,
            "metadata": {
                "generated_at": datetime.now(),
                "agent_version": "1.0",
                "total_campaigns": len(optimized)
            }
        }
```

### Campaign Planning Rules Engine:

```python
class CampaignRules:
    """
    Business rules enforced by the planner
    """
    
    RULES = {
        "send_caps": {
            "standard_weekly_max": 2,
            "unengaged_monthly_extra": 2
        },
        "campaign_distribution": {
            "email_count": 20,
            "sms_count": 4
        },
        "revenue_distribution": {
            "two_segments": {"primary": 70, "secondary": 30},
            "three_segments": {"primary": 70, "secondary": 15, "tertiary": 15}
        },
        "promotional_limits": {
            "max_promo_campaigns": 1,
            "promo_duration_days": 7
        },
        "segmentation_rules": {
            "must_include_full_list": True,
            "monitor_unengaged_percentage": True,
            "flag_deliverability_threshold": 0.15
        }
    }
    
    def apply_rules(self, campaigns: List[Dict]) -> List[Dict]:
        """
        Applies all business rules to campaign plan
        """
        campaigns = self.enforce_send_caps(campaigns)
        campaigns = self.balance_segments(campaigns)
        campaigns = self.optimize_send_times(campaigns)
        campaigns = self.ensure_list_health(campaigns)
        return campaigns
```

---

## 10. Error Handling

### Multi-Level Error Management:

```python
class ErrorHandler:
    """
    Comprehensive error handling system
    """
    
    @staticmethod
    async def handle_agent_error(error: Exception, context: Dict) -> Dict:
        """
        Handles errors at different levels
        """
        if isinstance(error, ValidationError):
            return {
                "status": "validation_error",
                "message": "Invalid input parameters",
                "details": error.errors()
            }
        
        elif isinstance(error, TimeoutError):
            return {
                "status": "timeout",
                "message": "Agent execution timed out",
                "partial_result": context.get('partial_result')
            }
        
        elif isinstance(error, APIError):
            # Handle Klaviyo/Firestore API errors
            return {
                "status": "api_error",
                "message": f"External service error: {error.service}",
                "retry_after": error.retry_after
            }
        
        else:
            # Generic error handling
            logger.error(f"Unexpected error: {error}", exc_info=True)
            return {
                "status": "error",
                "message": "An unexpected error occurred",
                "error_id": str(uuid.uuid4())
            }
```

### Frontend Error Display:
```javascript
function handleError(error) {
    // User-friendly error messages
    const errorMessages = {
        'validation_error': 'Please check your input values',
        'timeout': 'The operation took too long. Please try again.',
        'api_error': 'Unable to connect to external services',
        'error': 'Something went wrong. Please try again.'
    };
    
    const message = errorMessages[error.status] || error.message;
    showError(message);
    
    // Log detailed error for debugging
    console.error('Calendar Planner Error:', error);
}
```

---

## Developer Quick Start

### To modify the Calendar Planner:

1. **Frontend Changes**: Edit `/frontend/public/calendar_planner.html`
2. **Agent Logic**: Modify `/multi-agent/integrations/langchain_core/agents/calendar_planner.py`
3. **Add New Variables**: Update agent definition in `calendar_planner.py` and form in HTML
4. **Change Prompt**: Update `prompt_template` in agent definition
5. **Add Tools**: Register new tools in agent's `allowed_tools` policy

### Testing:
```bash
# Test the agent directly
curl -X POST "http://localhost:8000/api/admin/langchain/agents/calendar_planner/runs?task=Test" \
  -H "Content-Type: application/json" \
  -d '{"variables": {...}}'

# Check agent registration
curl http://localhost:8000/api/admin/langchain/agents | jq '.agents[] | select(.name=="calendar_planner")'
```

### Common Issues:
1. **Agent not found**: Run seed endpoint to register agents
2. **Variable errors**: Check all required variables are provided
3. **Timeout**: Increase `timeout_seconds` in agent policy
4. **No results**: Check AI model API keys are configured

---

## Architecture Decisions

### Why LangChain?
- Provides structured agent framework
- Built-in tool integration
- Variable management system
- Execution tracking and monitoring

### Why Not Direct MCP?
- LangChain provides higher-level abstractions
- Better suited for complex multi-step planning
- Easier prompt management and versioning
- Built-in validation and error handling

### Future Enhancements:
1. Real-time execution with WebSocket updates
2. Historical plan comparison
3. A/B test result integration
4. Automated plan deployment to Klaviyo
5. Multi-client batch planning

---

## Conclusion

The Calendar Planner represents a sophisticated integration of:
- Modern web frontend (HTML5/JavaScript)
- FastAPI backend with async processing
- LangChain multi-agent orchestration
- External service integration (Klaviyo, Firestore)
- AI-powered content generation

This architecture provides flexibility, scalability, and maintainability while delivering powerful campaign planning capabilities.