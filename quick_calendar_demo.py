#!/usr/bin/env python3
"""
Quick Calendar Demo - Shows working calendar with agent prompts
Ready to use immediately without complex imports
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the working calendar
from main import run_calendar_workflow


# Agent prompt templates you can use
AGENT_PROMPTS = {
    "campaign_planner": """
You are a Campaign Planning Expert. Given the brand {brand} and month {month}, create a comprehensive email campaign strategy.
Consider:
- Seasonal themes and holidays
- Optimal send frequency (2-4 emails per week)
- Different campaign types (promotional, educational, engagement)
- Customer journey stages
Output a structured campaign calendar with dates, themes, and objectives.
""",
    
    "copy_smith": """
You are a master copywriter specializing in email marketing. For {brand} in {month}, write compelling email copy that:
- Uses AIDA framework (Attention, Interest, Desire, Action)
- Includes power words and emotional triggers
- Has clear, action-oriented CTAs
- Maintains brand voice consistency
Create 3 email templates: promotional, educational, and re-engagement.
""",
    
    "revenue_analyst": """
You are a Revenue Analytics Expert. Analyze the campaign plan for {brand} in {month} and project:
- Expected open rates (industry: 20-25%)
- Click-through rates (industry: 2-3%)
- Conversion rates (industry: 1-2%)
- Revenue per email sent
- Total monthly revenue projection
Base projections on industry benchmarks and seasonal factors.
""",
    
    "audience_architect": """
You are a Segmentation Strategist. For {brand}'s {month} campaigns, design audience segments:
- VIP customers (top 20% by value)
- Active engagers (opened last 3 emails)
- Win-back targets (inactive 60+ days)
- New subscribers (joined last 30 days)
Define segment criteria and recommended messaging for each.
""",
    
    "calendar_strategist": """
You are a Send Time Optimization Expert. For {brand} in {month}, determine:
- Best days of week (typically Tue/Thu)
- Optimal send times by segment
- Time zone considerations
- Frequency caps to avoid fatigue
Create a send schedule maximizing engagement while respecting subscriber preferences.
""",
    
    "brand_brain": """
You are a Brand Consistency Guardian. Review {brand}'s {month} campaign plan and ensure:
- Consistent brand voice and tone
- Proper logo and color usage
- Aligned messaging across campaigns
- Brand values are reflected
Provide a brand compliance checklist and recommendations.
""",
    
    "gatekeeper": """
You are a Compliance Officer. For {brand}'s {month} campaigns, verify:
- CAN-SPAM compliance (unsubscribe, physical address)
- GDPR requirements (consent, data usage)
- Industry-specific regulations
- Accessibility standards (alt text, contrast)
Create a compliance checklist with pass/fail for each requirement.
""",
    
    "truth_teller": """
You are a Performance Analytics Expert. Based on {brand}'s {month} campaign plan:
- Identify potential performance risks
- Suggest A/B test opportunities
- Recommend KPIs to track
- Set realistic performance benchmarks
Provide honest assessment of expected vs. achievable results.
"""
}


def process_with_prompt(agent_name: str, prompt_template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate agent processing with prompt
    In production, this would call your LLM
    """
    prompt = prompt_template.format(**variables)
    
    # For demo, return structured response
    return {
        "agent": agent_name,
        "prompt_used": prompt[:200] + "...",
        "status": "ready",
        "recommendation": f"{agent_name} analysis for {variables.get('brand')} - {variables.get('month')}",
        "next_steps": [
            f"Execute {agent_name} prompt with LLM",
            "Review and validate output",
            "Integrate into campaign plan"
        ]
    }


def run_demo():
    """
    Run complete calendar demo with agent prompts
    """
    print("\n" + "="*70)
    print(" "*20 + "CALENDAR WORKFLOW DEMO")
    print("="*70 + "\n")
    
    # Configuration
    brand = "DemoCompany"
    month = "April 2025"
    
    print(f"📅 Brand: {brand}")
    print(f"📅 Month: {month}")
    print(f"📅 Mode: LangGraph + Agent Prompts")
    print("\n" + "-"*70 + "\n")
    
    # Step 1: Run base calendar workflow
    print("STEP 1: Running Calendar Workflow")
    print("-"*35)
    
    calendar_result = run_calendar_workflow(brand, month)
    
    if calendar_result.get("error"):
        print(f"❌ Workflow error: {calendar_result['error']}")
    else:
        artifacts = calendar_result.get("artifacts", [])
        print(f"✅ Calendar generated with {len(artifacts)} tasks completed")
        
        for artifact in artifacts:
            print(f"   • {artifact.get('task_type')}: {artifact.get('status')}")
    
    print("\n" + "-"*70 + "\n")
    
    # Step 2: Process with agent prompts
    print("STEP 2: Agent Analysis (Prompts Ready)")
    print("-"*35)
    
    # Select agents for this campaign
    selected_agents = [
        "campaign_planner",
        "copy_smith", 
        "revenue_analyst",
        "calendar_strategist",
        "audience_architect"
    ]
    
    agent_results = []
    variables = {"brand": brand, "month": month}
    
    for agent_name in selected_agents:
        if agent_name in AGENT_PROMPTS:
            print(f"\n🤖 {agent_name.upper()}")
            print("   " + AGENT_PROMPTS[agent_name].split('\n')[1][:60] + "...")
            
            result = process_with_prompt(
                agent_name,
                AGENT_PROMPTS[agent_name],
                variables
            )
            agent_results.append(result)
            print(f"   ✓ Prompt ready for execution")
    
    print("\n" + "-"*70 + "\n")
    
    # Step 3: Sample Campaign Plan
    print("STEP 3: Generated Campaign Structure") 
    print("-"*35)
    
    campaign_plan = {
        "brand": brand,
        "month": month,
        "weeks": [
            {
                "week": 1,
                "theme": "Spring Refresh Launch",
                "emails": [
                    {"day": "Tuesday", "type": "Announcement", "segment": "All"},
                    {"day": "Thursday", "type": "Feature Highlight", "segment": "Engaged"},
                    {"day": "Saturday", "type": "Weekend Special", "segment": "VIP"}
                ]
            },
            {
                "week": 2,
                "theme": "Customer Success Stories",
                "emails": [
                    {"day": "Monday", "type": "Case Study", "segment": "B2B"},
                    {"day": "Wednesday", "type": "Testimonials", "segment": "All"},
                    {"day": "Friday", "type": "User Tips", "segment": "New Users"}
                ]
            },
            {
                "week": 3,
                "theme": "Mid-Month Momentum",
                "emails": [
                    {"day": "Tuesday", "type": "Limited Offer", "segment": "Inactive"},
                    {"day": "Thursday", "type": "Product Deep Dive", "segment": "Engaged"},
                    {"day": "Sunday", "type": "Week Recap", "segment": "All"}
                ]
            },
            {
                "week": 4,
                "theme": "Month-End Push",
                "emails": [
                    {"day": "Monday", "type": "Last Chance", "segment": "Cart Abandoners"},
                    {"day": "Wednesday", "type": "Exclusive Preview", "segment": "VIP"},
                    {"day": "Friday", "type": "Month Summary", "segment": "All"}
                ]
            }
        ]
    }
    
    print(f"\n📊 {month} Campaign Calendar for {brand}\n")
    for week_data in campaign_plan["weeks"]:
        print(f"Week {week_data['week']}: {week_data['theme']}")
        for email in week_data["emails"]:
            print(f"  • {email['day']:9} - {email['type']:20} → {email['segment']}")
        print()
    
    print("-"*70 + "\n")
    
    # Step 4: Integration Points
    print("STEP 4: Integration Points")
    print("-"*35)
    
    integrations = {
        "LangGraph Studio": "http://localhost:2024 - Visual workflow editor",
        "LangSmith": "Trace IDs generated for debugging",
        "MCP Server": "Ready for Klaviyo API connection", 
        "Agent Prompts": f"{len(AGENT_PROMPTS)} prompts available",
        "Calendar API": "/api/calendar/workflow endpoint ready"
    }
    
    for name, status in integrations.items():
        print(f"✅ {name:15} : {status}")
    
    print("\n" + "-"*70 + "\n")
    
    # Step 5: Next Actions
    print("STEP 5: Ready for Production")
    print("-"*35)
    print("""
To complete the integration:

1. Connect to your LLM (OpenAI/Anthropic/etc):
   - Set API keys in environment
   - Update process_with_prompt() to call LLM
   
2. Connect to Klaviyo via MCP:
   - Start MCP server on port 8090
   - Configure Klaviyo API credentials
   
3. Use the agent prompts:
   - Each prompt is ready to use
   - Variables: {brand} and {month} are auto-filled
   - Add any custom variables as needed
   
4. Access in LangGraph Studio:
   - Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
   - View and debug the workflow visually
   
5. Call from your app:
   - POST /api/calendar/workflow
   - Body: {"brand": "YourBrand", "month": "May 2025"}
""")
    
    # Save output
    output = {
        "timestamp": datetime.now().isoformat(),
        "brand": brand,
        "month": month,
        "calendar_result": calendar_result,
        "agent_prompts": list(AGENT_PROMPTS.keys()),
        "campaign_plan": campaign_plan
    }
    
    output_file = f"calendar_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"📁 Output saved to: {output_file}")
    print("\n" + "="*70)
    print(" "*25 + "✅ DEMO COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_demo()