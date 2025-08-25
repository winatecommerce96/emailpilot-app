#!/usr/bin/env python3
"""
HOW TO USE THE INTEGRATED CALENDAR SYSTEM
This script shows you exactly how to use the system you asked about
"""

# Import the system
from integrated_calendar_system import IntegratedCalendarSystem
import json
from datetime import datetime

def main():
    print("\n" + "="*70)
    print("INTEGRATED CALENDAR SYSTEM - USAGE GUIDE")
    print("="*70 + "\n")
    
    # Step 1: Initialize the system
    print("Step 1: Initializing the system...")
    system = IntegratedCalendarSystem()
    print("✅ System initialized\n")
    
    # Step 2: Auto-start MCP servers (if not already running)
    print("Step 2: Starting MCP servers...")
    mcp_started = system.auto_start_mcp_servers()
    if mcp_started:
        print("✅ MCP servers started successfully")
    else:
        print("⚠️ MCP servers may already be running or failed to start")
    print()
    
    # Step 3: Test LLM connection
    print("Step 3: Testing LLM connection...")
    test_response = system.call_llm_locally(
        prompt="Say 'Hello, Calendar System is working!' in 5 words or less",
        variables={}
    )
    print(f"LLM Response: {test_response}\n")
    
    # Step 4: Edit an agent prompt (example)
    print("Step 4: Customizing agent prompts...")
    system.edit_agent_prompt(
        "campaign_planner",
        """You are a Campaign Planning Expert for {brand} in {month}.
Create a comprehensive email campaign strategy that includes:
- 3-4 emails per week with specific dates
- Clear subject lines for each email
- Target segments (VIP, New, Inactive, etc.)
- Expected open rates and click rates
Format as a structured campaign calendar."""
    )
    print("✅ Campaign planner prompt updated\n")
    
    # Step 5: Run a complete workflow
    print("Step 5: Running complete workflow...")
    print("-"*40)
    
    # YOUR ACTUAL USAGE - This is what you asked about!
    results = system.run_complete_workflow(
        brand="YourBrand",  # Replace with actual brand
        month="March 2025",  # Replace with target month
        goals=[
            "Increase revenue by 25%",
            "Launch spring collection",
            "Re-engage inactive customers"
        ]
    )
    
    print("\n" + "="*70)
    print("WORKFLOW RESULTS")
    print("="*70 + "\n")
    
    # Display results
    if results:
        print(f"Brand: {results['brand']}")
        print(f"Month: {results['month']}")
        print(f"Status: {'✅ Success' if not results.get('error') else '❌ Failed'}")
        
        # Show steps completed
        print("\nSteps Completed:")
        for step in results.get('steps', []):
            status_icon = "✅" if step['status'] == 'success' else "❌"
            print(f"  {status_icon} {step['step']}")
        
        # Show agent results
        agent_results = results.get('agent_results', {})
        if agent_results:
            print(f"\nAgents Used: {len(agent_results)}")
            for agent_name in agent_results:
                print(f"  • {agent_name}")
        
        # Save full results
        output_file = f"workflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Full results saved to: {output_file}")
    
    print("\n" + "="*70)
    print("OTHER USEFUL FUNCTIONS")
    print("="*70 + "\n")
    
    print("1. Assign specific agents to a campaign:")
    print("""
    results = system.assign_agents_to_campaign(
        brand="YourBrand",
        month="March 2025",
        goals=["Increase revenue"],
        custom_agents=["revenue_analyst", "copy_smith"]
    )
    """)
    
    print("2. Call LLM with any prompt:")
    print("""
    response = system.call_llm_locally(
        prompt="Create email subject lines for {brand}",
        variables={"brand": "YourBrand"}
    )
    """)
    
    print("3. Edit agent prompts:")
    print("""
    system.edit_agent_prompt(
        "copy_smith",
        "Your new custom prompt here..."
    )
    """)
    
    print("4. View all available agents:")
    print("""
    for agent_name, prompt in system.agent_prompts.items():
        print(f"{agent_name}: {prompt[:50]}...")
    """)
    
    print("\n" + "="*70)
    print("THAT'S IT! The system is fully integrated and ready to use.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()