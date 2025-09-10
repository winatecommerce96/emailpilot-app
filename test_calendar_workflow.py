#!/usr/bin/env python3
"""
Test Calendar Workflow - Simplified version without LLM dependencies
Demonstrates the workflow structure with mock data
"""

import asyncio
import json
from typing import Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "multi-agent"))

# Import agent definitions
from integrations.langchain_core.agents.historical_analyst import analyze_campaign_history
from integrations.langchain_core.agents.segment_strategist import analyze_segments
from integrations.langchain_core.agents.content_optimizer import generate_campaign_ideas
from integrations.langchain_core.agents.calendar_orchestrator import orchestrate_calendar

async def run_test_workflow(
    client_id: str,
    client_name: str,
    selected_month: str,
    campaign_count: int = 8,
    sales_goal: float = 50000
) -> Dict[str, Any]:
    """
    Run the calendar workflow with mock data (no LLM required)
    """
    print(f"\n🚀 Starting workflow for {client_name}")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Step 1: Analyze historical data (mock)
    print("📊 Step 1: Analyzing historical campaigns...")
    mock_campaigns = [
        {
            "name": f"Campaign {i}",
            "open_rate": 0.20 + (i * 0.01),
            "click_rate": 0.03 + (i * 0.002),
            "revenue": 5000 + (i * 1000),
            "send_time": f"{10 + i}:00"
        }
        for i in range(10)
    ]
    
    historical_insights = analyze_campaign_history(
        campaigns=mock_campaigns,
        thresholds={"min_open_rate": 0.15, "min_click_rate": 0.02, "min_revenue": 1000}
    )
    print(f"   ✓ Found {historical_insights['summary']['total_campaigns']} campaigns")
    print(f"   ✓ Avg open rate: {historical_insights['summary']['avg_open_rate']:.1%}")
    print(f"   ✓ Best send time: {historical_insights['timing_insights']['best_send_hour']}")
    
    # Step 2: Analyze segments (mock)
    print("\n👥 Step 2: Analyzing customer segments...")
    mock_segments = [
        {
            "name": "VIP Customers",
            "member_count": 500,
            "avg_order_value": 150,
            "engagement_rate": 0.35,
            "value_tier": "high"
        },
        {
            "name": "Regular Buyers",
            "member_count": 2000,
            "avg_order_value": 75,
            "engagement_rate": 0.25,
            "value_tier": "medium"
        },
        {
            "name": "New Subscribers",
            "member_count": 800,
            "avg_order_value": 50,
            "engagement_rate": 0.20,
            "value_tier": "growth"
        }
    ]
    
    segment_analysis = analyze_segments(
        segments=mock_segments,
        criteria={"min_segment_size": 100, "value_segments": ["high", "medium"]}
    )
    print(f"   ✓ Identified {segment_analysis['summary']['viable_segments']} viable segments")
    print(f"   ✓ Total audience: {segment_analysis['summary']['total_audience']:,}")
    
    # Step 3: Generate content ideas
    print("\n✏️ Step 3: Generating content ideas...")
    content_ideas = generate_campaign_ideas(
        client_name=client_name,
        brand_voice="professional and friendly",
        optimization_goal="balanced",
        campaign_count=campaign_count
    )
    print(f"   ✓ Generated {len(content_ideas)} campaign concepts")
    
    # Step 4: Orchestrate calendar
    print("\n📅 Step 4: Creating optimized calendar...")
    final_calendar = orchestrate_calendar(
        client_name=client_name,
        selected_month=selected_month,
        campaign_count=campaign_count,
        sales_goal=sales_goal,
        insights={
            "historical": historical_insights,
            "segments": segment_analysis,
            "content": content_ideas
        }
    )
    
    print(f"   ✓ Scheduled {len(final_calendar['campaigns'])} campaigns")
    print(f"   ✓ Expected revenue: ${final_calendar['summary']['expected_revenue']:,.2f}")
    print(f"   ✓ Goal achievement: {final_calendar['summary']['goal_achievement']:.1f}%")
    
    # Step 5: Validation
    print("\n✅ Step 5: Validating calendar...")
    validation = final_calendar["validation"]
    print(f"   ✓ Meets revenue goal: {validation['meets_revenue_goal']}")
    print(f"   ✓ Proper spacing: {validation['proper_spacing']}")
    print(f"   ✓ All content assigned: {validation['all_content_assigned']}")
    
    execution_time = (datetime.now() - start_time).total_seconds()
    print(f"\n⏱️ Total execution time: {execution_time:.2f}s")
    print("=" * 60)
    
    return final_calendar

async def main():
    """Test the workflow"""
    
    # Test for Rogue Creamery
    result = await run_test_workflow(
        client_id="rogue-creamery",
        client_name="Rogue Creamery",
        selected_month="2025-02",
        campaign_count=8,
        sales_goal=75000
    )
    
    # Print sample campaigns
    print("\n📧 Sample Campaigns from Calendar:")
    print("-" * 60)
    for campaign in result["campaigns"][:3]:
        print(f"\n📅 {campaign['date']} at {campaign['time']}")
        print(f"   Name: {campaign['name']}")
        print(f"   Segment: {campaign['segment']}")
        print(f"   Subject: {campaign['subject_line_a']}")
        print(f"   Expected Revenue: ${campaign['expected_metrics']['revenue']:,.2f}")
    
    # Save to file
    output_file = f"test_calendar_{result['client']}_{result['month']}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Full calendar saved to {output_file}")
    
    return result

if __name__ == "__main__":
    result = asyncio.run(main())