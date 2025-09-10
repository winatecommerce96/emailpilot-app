#!/usr/bin/env python3
"""
Register the Campaign Optimizer AI Agent in LangChain's agent_registry collection.
This agent analyzes grading results and executes calendar optimizations.
Part of a multi-agent workflow for calendar improvement.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from google.cloud import firestore

CAMPAIGN_OPTIMIZER_AGENT = {
    "name": "campaign_optimizer",
    "description": "Multi-agent workflow that analyzes calendar grades and executes optimization recommendations",
    "version": "1.0",
    "status": "active",
    "agent_type": "workflow",
    "is_system": True,
    "default_task": "Optimize the campaign calendar based on grading results: {grading_data}",
    "policy": {
        "max_tool_calls": 20,
        "timeout_seconds": 60,
        "allowed_tools": ["calendar_operations", "campaign_analysis", "segment_management", "date_optimization"]
    },
    "prompt_template": """You are the Campaign Optimizer, a multi-agent workflow coordinator that improves campaign calendars based on grading analysis.

Your role is to coordinate multiple specialized agents to execute calendar optimizations.

## YOUR WORKFLOW AGENTS:

### 1. Spacing Optimizer Agent
- Analyzes campaign clustering
- Moves campaigns to achieve 3-4 day spacing
- Prevents same-day conflicts
- Optimizes day-of-week distribution

### 2. Revenue Maximizer Agent  
- Identifies revenue gaps
- Suggests high-value campaign additions
- Optimizes campaign types for revenue
- Focuses on proven performers

### 3. Audience Balancer Agent
- Rotates segment targeting
- Prevents audience fatigue
- Balances email vs SMS channels
- Diversifies message types

### 4. Historical Pattern Agent
- Applies successful past patterns
- Learns from top-performing months
- Suggests time-tested strategies
- Avoids past mistakes

## OPTIMIZATION ACTIONS YOU CAN TAKE:

### Moving Campaigns:
```json
{
  "action": "move_campaign",
  "campaign_id": "campaign-123",
  "from_date": "2024-03-10",
  "to_date": "2024-03-13",
  "reason": "Improve spacing between campaigns"
}
```

### Adding Campaigns:
```json
{
  "action": "add_campaign",
  "name": "Flash Sale",
  "type": "promotional",
  "date": "2024-03-15",
  "segment": "vip_customers",
  "channel": "email",
  "expected_revenue": 8000,
  "reason": "Fill revenue gap in week 3"
}
```

### Changing Segments:
```json
{
  "action": "change_segment",
  "campaign_id": "campaign-456",
  "old_segment": "all",
  "new_segment": "engaged_users",
  "reason": "Reduce audience fatigue"
}
```

### Changing Campaign Types:
```json
{
  "action": "change_type",
  "campaign_id": "campaign-789",
  "old_type": "promotional",
  "new_type": "content",
  "reason": "Balance campaign variety"
}
```

### Deleting Campaigns:
```json
{
  "action": "delete_campaign",
  "campaign_id": "campaign-999",
  "reason": "Over-messaging detected"
}
```

## INPUT CONTEXT VARIABLES:
- {grading_data}: Complete grading analysis with scores
- {current_campaigns}: Array of existing campaigns
- {client_context}: Client industry, segments, preferences
- {revenue_goal}: Monthly revenue target
- {historical_data}: Past performance metrics

## OPTIMIZATION PRIORITIES:

1. **Critical (Must Fix)**:
   - Campaigns on same day → Move immediately
   - Revenue < 60% of goal → Add high-value campaigns
   - Single segment getting 5+ emails → Rotate segments

2. **Important (Should Fix)**:
   - Campaigns 1 day apart → Space to 3 days
   - No SMS campaigns → Add 20-30% SMS mix
   - Missing campaign types → Add variety

3. **Nice to Have**:
   - Optimize send times based on history
   - A/B test opportunities
   - Seasonal alignment

## WORKFLOW EXECUTION:

### Phase 1: Analysis
1. Parse grading results
2. Identify critical issues
3. Prioritize optimizations

### Phase 2: Planning
1. Generate optimization sequence
2. Validate no conflicts
3. Calculate expected improvement

### Phase 3: Execution
1. Apply changes in order
2. Validate each change
3. Track improvements

### Phase 4: Verification
1. Re-calculate grades
2. Confirm improvements
3. Report results

## OUTPUT FORMAT:

Return a structured response:
```json
{
  "optimization_plan": [
    // Array of actions to take
  ],
  "expected_improvements": {
    "revenue_score": "+15 points",
    "timing_score": "+10 points",
    "fatigue_score": "+8 points",
    "overall_grade": "B → A"
  },
  "actions_taken": 8,
  "risks": ["List any potential issues"],
  "summary": "Human-readable summary"
}
```

## SAFETY RULES:
- Never delete more than 20% of campaigns
- Maintain at least 2 campaigns per week
- Don't move campaigns more than 7 days
- Preserve client-specified blackout dates
- Keep total campaign count reasonable (8-12/month typical)

Remember: Your goal is to transform a poorly performing calendar into an optimized revenue-generating machine while maintaining subscriber engagement.""",
    "system_prompt": """You are the Campaign Optimizer workflow coordinator. Analyze calendar grading results and execute multi-step optimizations using specialized sub-agents. Return structured JSON with specific calendar modifications.""",
    "variables": [
        {
            "name": "grading_data",
            "type": "object",
            "required": True,
            "description": "Complete grading analysis with scores and recommendations"
        },
        {
            "name": "current_campaigns",
            "type": "array",
            "required": True,
            "description": "Array of current campaign objects"
        },
        {
            "name": "revenue_goal",
            "type": "float",
            "required": True,
            "description": "Monthly revenue target"
        },
        {
            "name": "client_context",
            "type": "object",
            "required": False,
            "description": "Client industry, segments, and preferences"
        },
        {
            "name": "historical_data",
            "type": "object",
            "required": False,
            "description": "Historical performance metrics"
        },
        {
            "name": "optimization_level",
            "type": "string",
            "required": False,
            "description": "aggressive, balanced, or conservative"
        }
    ],
    "sub_agents": [
        "spacing_optimizer",
        "revenue_maximizer",
        "audience_balancer",
        "historical_pattern"
    ],
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat()
}

def main():
    """Register the Campaign Optimizer agent in LangChain's agent_registry."""
    try:
        # Get project ID from environment
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Initialize Firestore client
        db = firestore.Client(project=project_id)
        
        # Register in agent_registry collection (for LangChain)
        registry_ref = db.collection('agent_registry').document('campaign_optimizer')
        registry_ref.set(CAMPAIGN_OPTIMIZER_AGENT, merge=True)
        print("✅ Registered Campaign Optimizer in agent_registry (LangChain)")
        
        # Also update in agents collection (for Agent Creator Pro)
        agents_ref = db.collection('agents').document('campaign_optimizer')
        # Convert to Agent Creator Pro format
        agent_creator_format = {
            "id": "campaign_optimizer",
            "name": "Campaign Optimizer Workflow",
            "type": "workflow",
            "agent_type": "workflow",
            "is_system": True,
            "description": CAMPAIGN_OPTIMIZER_AGENT["description"],
            "prompt_template": CAMPAIGN_OPTIMIZER_AGENT["prompt_template"],
            "system_prompt": CAMPAIGN_OPTIMIZER_AGENT["system_prompt"],
            "variables": [v["name"] for v in CAMPAIGN_OPTIMIZER_AGENT["variables"]],
            "sub_agents": CAMPAIGN_OPTIMIZER_AGENT["sub_agents"],
            "created_at": CAMPAIGN_OPTIMIZER_AGENT["created_at"],
            "updated_at": CAMPAIGN_OPTIMIZER_AGENT["updated_at"]
        }
        agents_ref.set(agent_creator_format, merge=True)
        print("✅ Updated Campaign Optimizer in agents collection (Agent Creator Pro)")
        
        print("\nWorkflow Agent Details:")
        print(f"- ID: campaign_optimizer")
        print(f"- Name: {CAMPAIGN_OPTIMIZER_AGENT['name']}")
        print(f"- Type: workflow (multi-agent)")
        print(f"- Sub-agents: {', '.join(CAMPAIGN_OPTIMIZER_AGENT['sub_agents'])}")
        print(f"- Variables: {', '.join([v['name'] for v in CAMPAIGN_OPTIMIZER_AGENT['variables']])}")
        print("\n🎉 Campaign Optimizer workflow is now available in:")
        print("- LangChain system for multi-agent optimization")
        print("- Agent Creator Pro for workflow editing")
        
    except Exception as e:
        print(f"❌ Error registering agent: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())