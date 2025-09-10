#!/usr/bin/env python3
"""
Register the Campaign Grader AI Agent in LangChain's agent_registry collection.
This agent grades campaign calendars against revenue goals and optimization metrics.
Editable in Agent Creator Pro.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from google.cloud import firestore

CAMPAIGN_GRADER_AGENT = {
    "name": "campaign_grader",
    "description": "AI agent that grades campaign calendars against revenue goals, timing optimization, and best practices",
    "version": "1.0",
    "status": "active",
    "agent_type": "system",
    "is_system": True,
    "default_task": "Grade the following campaign calendar: {campaigns_json}",
    "policy": {
        "max_tool_calls": 10,
        "timeout_seconds": 30,
        "allowed_tools": ["performance_analysis", "revenue_calculation", "optimization_scoring"]
    },
    "prompt_template": """You are the Campaign Grader AI, an expert at analyzing email marketing calendars for optimization opportunities.

Your role is to grade campaign calendars based on multiple factors and provide actionable feedback.

## GRADING CRITERIA (Total 100 points):

### 1. Revenue Goal Alignment (40 points)
- Calculate expected revenue from all campaigns
- Compare against monthly/quarterly revenue targets
- Score based on likelihood of achieving goals
- Consider historical conversion rates

### 2. Campaign Timing & Spacing (20 points)
- Optimal spacing between campaigns (3-4 days ideal)
- Avoid clustering (max 2 campaigns within 48 hours)
- Strategic day-of-week distribution
- Time zone considerations

### 3. Audience Fatigue Prevention (20 points)
- Segment rotation (don't hit same segment repeatedly)
- Channel diversity (email vs SMS balance)
- Message variety (promotional vs content vs engagement)
- Frequency caps per subscriber

### 4. Historical Performance Patterns (20 points)
- Compare to successful past months
- Learn from previous campaign performance
- Seasonal alignment
- Day/time optimization based on past opens

## INPUT VARIABLES:
- {campaigns_json}: JSON array of scheduled campaigns
- {revenue_goal}: Monthly revenue target
- {client_name}: Client name for context
- {historical_performance}: Past campaign metrics
- {current_month}: Month being graded
- {audience_segments}: Available audience segments
- {industry_type}: Client's industry vertical

## GRADING OUTPUT FORMAT:

### Overall Grade: [A+ to F]
**Score: XX/100**

#### 📊 Revenue Alignment: XX/40
- Current projection: $XX,XXX
- Goal: $XX,XXX
- Gap: $X,XXX (XX%)
- **Recommendation**: [Specific action to improve revenue]

#### ⏰ Timing & Spacing: XX/20
- Campaign density: X.X campaigns/week
- Clustering issues: [List any problems]
- **Recommendation**: [Specific timing adjustments]

#### 😴 Audience Fatigue: XX/20
- Segment overlap: XX%
- Highest frequency segment: [Name] (X emails/month)
- **Recommendation**: [Specific audience adjustments]

#### 📈 Historical Alignment: XX/20
- Comparison to best month: XX% match
- Key differences: [List major variations]
- **Recommendation**: [Specific historical insights]

### 🎯 TOP 3 IMPROVEMENTS:
1. [Most impactful change with expected revenue impact]
2. [Second priority change with reasoning]
3. [Third priority change with reasoning]

### 💡 AI INSIGHTS:
- [Unique pattern or opportunity detected]
- [Competitive advantage suggestion]
- [Risk mitigation advice]

## GRADING SCALE:
- A+ (95-100): Exceptional optimization, likely to exceed goals
- A (90-94): Excellent calendar, well-optimized
- B (80-89): Good calendar with minor improvements needed
- C (70-79): Average, several optimization opportunities
- D (60-69): Below average, significant changes recommended
- F (<60): Poor optimization, major overhaul needed

## SPECIAL CONSIDERATIONS:
- Holiday periods require adjusted spacing rules
- B2B vs B2C have different optimal send times
- Seasonal businesses need concentrated campaigns
- New product launches can justify higher frequency

## COMPARISON MODE:
When {original_campaigns} is provided, also calculate:
- Delta score (original vs modified)
- Key improvements made
- Remaining opportunities
- Risk assessment of changes

Remember: Your goal is to help coordinators optimize for maximum revenue while maintaining subscriber engagement and brand reputation.""",
    "system_prompt": """You are the Campaign Grader AI. Analyze email marketing calendars and provide detailed grades based on revenue goals, timing optimization, audience fatigue prevention, and historical performance. Give actionable recommendations with each grade component.""",
    "variables": [
        {
            "name": "campaigns_json",
            "type": "string",
            "required": True,
            "description": "JSON string of campaign array with dates, types, segments, and metrics"
        },
        {
            "name": "revenue_goal",
            "type": "float",
            "required": True,
            "description": "Monthly revenue target in dollars"
        },
        {
            "name": "client_name",
            "type": "string",
            "required": False,
            "description": "Client name for personalized feedback"
        },
        {
            "name": "historical_performance",
            "type": "string",
            "required": False,
            "description": "JSON string of past campaign performance metrics"
        },
        {
            "name": "current_month",
            "type": "string",
            "required": False,
            "description": "Month and year being graded"
        },
        {
            "name": "audience_segments",
            "type": "string",
            "required": False,
            "description": "JSON array of available audience segments"
        },
        {
            "name": "industry_type",
            "type": "string",
            "required": False,
            "description": "Client's industry (e-commerce, SaaS, B2B, etc.)"
        },
        {
            "name": "original_campaigns",
            "type": "string",
            "required": False,
            "description": "Original campaign calendar for comparison (before modifications)"
        }
    ],
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat()
}

def main():
    """Register the Campaign Grader agent in LangChain's agent_registry."""
    try:
        # Get project ID from environment
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Initialize Firestore client
        db = firestore.Client(project=project_id)
        
        # Register in agent_registry collection (for LangChain)
        registry_ref = db.collection('agent_registry').document('campaign_grader')
        registry_ref.set(CAMPAIGN_GRADER_AGENT, merge=True)
        print("✅ Registered Campaign Grader in agent_registry (LangChain)")
        
        # Also update in agents collection (for Agent Creator Pro)
        agents_ref = db.collection('agents').document('campaign_grader')
        # Convert to Agent Creator Pro format
        agent_creator_format = {
            "id": "campaign_grader",
            "name": "Campaign Grader AI",
            "type": "system",
            "agent_type": "system",
            "is_system": True,
            "description": CAMPAIGN_GRADER_AGENT["description"],
            "prompt_template": CAMPAIGN_GRADER_AGENT["prompt_template"],
            "system_prompt": CAMPAIGN_GRADER_AGENT["system_prompt"],
            "variables": [v["name"] for v in CAMPAIGN_GRADER_AGENT["variables"]],
            "created_at": CAMPAIGN_GRADER_AGENT["created_at"],
            "updated_at": CAMPAIGN_GRADER_AGENT["updated_at"]
        }
        agents_ref.set(agent_creator_format, merge=True)
        print("✅ Updated Campaign Grader in agents collection (Agent Creator Pro)")
        
        print("\nAgent Details:")
        print(f"- ID: campaign_grader")
        print(f"- Name: {CAMPAIGN_GRADER_AGENT['name']}")
        print(f"- Status: {CAMPAIGN_GRADER_AGENT['status']}")
        print(f"- Variables: {', '.join([v['name'] for v in CAMPAIGN_GRADER_AGENT['variables']])}")
        print("\n🎉 Campaign Grader agent is now available in:")
        print("- LangChain system for processing")
        print("- Agent Creator Pro for editing")
        
    except Exception as e:
        print(f"❌ Error registering agent: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())