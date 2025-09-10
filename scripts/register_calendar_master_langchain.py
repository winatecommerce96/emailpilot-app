#!/usr/bin/env python3
"""
Register the Calendar Master AI Agent in LangChain's agent_registry collection.
This allows the agent to be used by LangChain and edited in Agent Creator Enhanced.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from google.cloud import firestore

CALENDAR_MASTER_AGENT = {
    "name": "calendar_master",
    "description": "AI assistant for managing email campaign calendars with natural language commands",
    "version": "1.0",
    "status": "active",
    "agent_type": "system",
    "is_system": True,
    "default_task": "Process the following calendar command: {message}",
    "policy": {
        "max_tool_calls": 10,
        "timeout_seconds": 30,
        "allowed_tools": ["calendar_operations", "campaign_analysis"]
    },
    "prompt_template": """You are the Calendar Master AI Assistant, a specialized agent for managing email marketing campaigns on a visual calendar.

Your primary responsibilities:
1. Parse natural language commands about campaigns
2. Execute calendar operations (add, move, delete, list)
3. Provide helpful feedback about campaign scheduling
4. Analyze campaign performance metrics

AVAILABLE COMMANDS YOU CAN PROCESS:

## Adding Campaigns:
- "Add a promotional campaign on the 15th"
- "Create a content email on the 20th"
- "Schedule an engagement survey for next Tuesday"
- "Put a seasonal campaign on Black Friday"

When adding, extract:
- Campaign type (promotional/content/engagement/seasonal)
- Date (specific day number or relative date)
- Time (default to 10:00 if not specified)

## Moving Campaigns:
- "Move the campaign from the 10th to the 15th"
- "Reschedule the newsletter from Monday to Friday"
- "Change the promotional email to the 20th"

## Deleting Campaigns:
- "Delete the campaign on the 20th"
- "Remove all promotional campaigns"
- "Clear the calendar"
- "Cancel the email on the 15th"

## Listing/Viewing:
- "What campaigns are scheduled?"
- "Show me next week's emails"
- "List all promotional campaigns"
- "What's on the 15th?"

## Analytics:
- "What's the expected revenue?"
- "Show campaign statistics"
- "How many campaigns this month?"
- "What's the average open rate?"

## Context Variables Available:
- {client_name}: Current client name
- {campaign_count}: Number of campaigns
- {total_revenue}: Expected revenue sum
- {current_month}: Current calendar month
- {campaigns_list}: List of campaign details

## Response Format:
Always respond with:
1. A clear confirmation of what action was taken
2. Relevant details about the result
3. Helpful suggestions for next steps

Examples:
- "✅ Added promotional campaign on March 15th at 10:00 AM"
- "📊 You have 8 campaigns scheduled with $45,000 expected revenue"
- "❌ No campaign found on the 20th to delete"

## Special Instructions:
- Be concise but informative
- Use emojis to make responses friendlier
- Suggest optimal campaign timing based on best practices
- Alert if there are too many campaigns on one day (>2)
- Recommend campaign types based on gaps in the schedule

Remember: You're helping marketers optimize their email campaign calendar for maximum engagement and revenue.""",
    "system_prompt": """You are the Calendar Master AI Assistant. Process natural language commands to manage email campaigns on a calendar. Parse commands like 'Add promotional campaign on the 15th' or 'Move campaign from 10th to 20th'. Be helpful, concise, and use emojis.""",
    "variables": [
        {
            "name": "message",
            "type": "string",
            "required": True,
            "description": "Natural language command about calendar operations"
        },
        {
            "name": "client_name",
            "type": "string",
            "required": False,
            "description": "Current client name"
        },
        {
            "name": "campaign_count",
            "type": "integer",
            "required": False,
            "description": "Number of campaigns currently scheduled"
        },
        {
            "name": "total_revenue",
            "type": "float",
            "required": False,
            "description": "Total expected revenue from campaigns"
        },
        {
            "name": "current_month",
            "type": "string",
            "required": False,
            "description": "Current calendar month and year"
        },
        {
            "name": "campaigns_list",
            "type": "string",
            "required": False,
            "description": "JSON string of campaign details"
        }
    ],
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat()
}

def main():
    """Register the Calendar Master agent in LangChain's agent_registry."""
    try:
        # Get project ID from environment
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Initialize Firestore client
        db = firestore.Client(project=project_id)
        
        # Register in agent_registry collection (for LangChain)
        registry_ref = db.collection('agent_registry').document('calendar_master')
        registry_ref.set(CALENDAR_MASTER_AGENT, merge=True)
        print("✅ Registered Calendar Master in agent_registry (LangChain)")
        
        # Also update in agents collection (for Agent Creator Pro)
        agents_ref = db.collection('agents').document('calendar_master')
        # Convert to Agent Creator Pro format
        agent_creator_format = {
            "id": "calendar_master",
            "name": "Calendar Master Assistant",
            "type": "system",
            "agent_type": "system",
            "is_system": True,
            "description": CALENDAR_MASTER_AGENT["description"],
            "prompt_template": CALENDAR_MASTER_AGENT["prompt_template"],
            "system_prompt": CALENDAR_MASTER_AGENT["system_prompt"],
            "variables": ["client_name", "campaign_count", "total_revenue", "current_month", "campaigns_list"],
            "created_at": CALENDAR_MASTER_AGENT["created_at"],
            "updated_at": CALENDAR_MASTER_AGENT["updated_at"]
        }
        agents_ref.set(agent_creator_format, merge=True)
        print("✅ Updated Calendar Master in agents collection (Agent Creator Pro)")
        
        print("\nAgent Details:")
        print(f"- ID: calendar_master")
        print(f"- Name: {CALENDAR_MASTER_AGENT['name']}")
        print(f"- Status: {CALENDAR_MASTER_AGENT['status']}")
        print(f"- Variables: {', '.join([v['name'] for v in CALENDAR_MASTER_AGENT['variables']])}")
        print("\n🎉 Calendar Master agent is now available in:")
        print("- LangChain system for processing")
        print("- Agent Creator Enhanced for editing")
        
    except Exception as e:
        print(f"❌ Error registering agent: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())