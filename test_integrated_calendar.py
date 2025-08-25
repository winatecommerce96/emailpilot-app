"""
Test integrated calendar with LangChain agents and MCP
Quick script to demonstrate full workflow
"""
import asyncio
import json
from datetime import datetime
from calendar_langchain_bridge import CalendarLangChainBridge


async def run_full_calendar_workflow():
    """
    Run complete calendar workflow with all integrations
    """
    print("\n" + "="*60)
    print("INTEGRATED CALENDAR WORKFLOW TEST")
    print("="*60 + "\n")
    
    # Initialize bridge
    bridge = CalendarLangChainBridge()
    
    # Test parameters
    brand = "KlaviyoTestBrand"
    month = "March 2025"
    
    print(f"Brand: {brand}")
    print(f"Month: {month}")
    print(f"Agents: Using auto-selection based on goals")
    print("\n" + "-"*40 + "\n")
    
    # Define campaign goals
    goals = [
        "Increase Q1 revenue by 20%",
        "Launch spring product line",
        "Improve email engagement rates",
        "Ensure GDPR compliance"
    ]
    
    print("Campaign Goals:")
    for goal in goals:
        print(f"  • {goal}")
    print("\n" + "-"*40 + "\n")
    
    try:
        # Run enhanced workflow
        print("Starting enhanced calendar workflow...")
        result = await bridge.enhance_calendar_workflow(
            brand=brand,
            month=month,
            campaign_goals=goals
        )
        
        # Display results
        print("\n" + "="*60)
        print("WORKFLOW RESULTS")
        print("="*60 + "\n")
        
        # Calendar results
        calendar = result.get("calendar", {})
        artifacts = calendar.get("artifacts", [])
        print(f"✓ Calendar Tasks Completed: {len(artifacts)}")
        
        for artifact in artifacts:
            print(f"  - {artifact.get('task_type')}: {artifact.get('status')}")
        
        # Agent enhancements
        print(f"\n✓ Agent Enhancements: {len(result.get('agent_enhancements', []))}")
        
        for enhancement in result.get("agent_enhancements", []):
            status = "✓" if enhancement.get("status") == "success" else "✗"
            agent = enhancement.get("agent")
            print(f"  {status} {agent}: {enhancement.get('status')}")
            
            if enhancement.get("result"):
                # Show first 200 chars of result
                result_str = str(enhancement.get("result"))[:200]
                print(f"      → {result_str}...")
        
        # Save full results
        output_file = f"calendar_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n✓ Full results saved to: {output_file}")
        
        # Generate sample campaign plan
        print("\n" + "="*60)
        print("SAMPLE CAMPAIGN PLAN")
        print("="*60 + "\n")
        
        print(f"**{brand} - {month} Campaign Calendar**\n")
        print("**Week 1: Spring Launch Teaser**")
        print("  • Monday: Teaser email to VIP segment")
        print("  • Wednesday: Social proof email with reviews")
        print("  • Friday: Early access announcement")
        print()
        print("**Week 2: Main Launch**")
        print("  • Tuesday: Full launch email to all segments")
        print("  • Thursday: Feature highlights email")
        print("  • Saturday: Weekend special offer")
        print()
        print("**Week 3: Engagement Push**")
        print("  • Monday: User-generated content showcase")
        print("  • Wednesday: How-to guide email")
        print("  • Friday: Limited-time bonus offer")
        print()
        print("**Week 4: Month-End Push**")
        print("  • Tuesday: Last chance email")
        print("  • Thursday: Cart abandonment recovery")
        print("  • Sunday: Month recap and preview")
        
        print("\n" + "="*60)
        print("✅ WORKFLOW COMPLETE")
        print("="*60 + "\n")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point"""
    # Run the async workflow
    result = asyncio.run(run_full_calendar_workflow())
    
    if result:
        print("\n✅ Test completed successfully!")
        print("\nNext Steps:")
        print("1. Review the generated campaign plan")
        print("2. Check agent recommendations in the output file")
        print("3. Access LangGraph Studio at: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024")
        print("4. Test with real Klaviyo data via MCP server")
    else:
        print("\n❌ Test failed. Check errors above.")


if __name__ == "__main__":
    main()