#!/usr/bin/env python3
"""
Test script to verify LangSmith tracing is working correctly
Creates a complete trace that should show up in the LangSmith dashboard
"""

import os
import asyncio
from datetime import datetime
from langsmith import Client
from langsmith.run_helpers import traceable
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import httpx

# Set environment variables
os.environ["LANGSMITH_API_KEY"] = "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"
os.environ["LANGSMITH_PROJECT"] = "emailpilot-calendar"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["OPENAI_API_KEY"] = "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"

# Initialize LangSmith client
client = Client()

@traceable(
    run_type="chain",
    name="calendar_planning_workflow",
    project_name="emailpilot-calendar",
    tags=["test", "calendar", "planning"]
)
async def plan_campaign_workflow(brand: str, month: str):
    """Main workflow for campaign planning with proper tracing"""
    
    print(f"Starting campaign planning for {brand} in {month}")
    
    # Step 1: Analyze current metrics
    metrics = await analyze_metrics(brand, month)
    
    # Step 2: Generate campaign ideas
    ideas = await generate_campaign_ideas(brand, month, metrics)
    
    # Step 3: Create calendar events
    events = await create_calendar_events(brand, month, ideas)
    
    # Step 4: Optimize timing
    optimized = await optimize_send_times(brand, events)
    
    return {
        "brand": brand,
        "month": month,
        "metrics": metrics,
        "ideas": ideas,
        "events": events,
        "optimized": optimized
    }

@traceable(
    run_type="chain",
    name="analyze_metrics",
    tags=["metrics", "analysis"]
)
async def analyze_metrics(brand: str, month: str) -> dict:
    """Analyze metrics for the brand"""
    print(f"  Analyzing metrics for {brand}...")
    
    # Simulate API call to Klaviyo
    await asyncio.sleep(0.5)
    
    return {
        "open_rate": 24.5,
        "click_rate": 3.2,
        "revenue": 14138.83,
        "subscribers": 15234
    }

@traceable(
    run_type="llm",
    name="generate_campaign_ideas",
    tags=["llm", "creative"]
)
async def generate_campaign_ideas(brand: str, month: str, metrics: dict) -> list:
    """Generate campaign ideas using LLM"""
    print(f"  Generating campaign ideas...")
    
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
    
    messages = [
        SystemMessage(content="You are a creative email marketing strategist."),
        HumanMessage(content=f"""
        Generate 3 campaign ideas for {brand} in {month}.
        Current metrics: {metrics}
        
        Provide brief, creative campaign themes.
        """)
    ]
    
    response = await llm.ainvoke(messages)
    
    # Parse response into list
    ideas = [
        "Spring Collection Launch",
        "Customer Appreciation Week",
        "Flash Sale Friday"
    ]
    
    return ideas

@traceable(
    run_type="chain",
    name="create_calendar_events",
    tags=["calendar", "events"]
)
async def create_calendar_events(brand: str, month: str, ideas: list) -> list:
    """Create calendar events from ideas"""
    print(f"  Creating calendar events...")
    
    events = []
    for i, idea in enumerate(ideas):
        event = {
            "id": f"evt_{i+1}",
            "title": idea,
            "brand": brand,
            "date": f"{month}-{(i+1)*7:02d}",
            "type": "campaign"
        }
        events.append(event)
    
    return events

@traceable(
    run_type="tool",
    name="optimize_send_times",
    tags=["optimization", "timing"]
)
async def optimize_send_times(brand: str, events: list) -> dict:
    """Optimize send times for events"""
    print(f"  Optimizing send times...")
    
    # Simulate optimization logic
    await asyncio.sleep(0.3)
    
    optimized = {
        "best_day": "Tuesday",
        "best_time": "10:00 AM",
        "timezone": "EST",
        "events_optimized": len(events)
    }
    
    return optimized

@traceable(
    run_type="chain",
    name="test_langgraph_connection",
    tags=["langgraph", "integration"]
)
async def test_langgraph_connection():
    """Test connection to LangGraph server"""
    print("Testing LangGraph connection...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:2024/assistants/agent")
            
            if response.status_code == 200:
                print("  ✅ LangGraph server is accessible")
                return {"status": "connected", "assistant": "agent"}
            else:
                print(f"  ❌ LangGraph returned {response.status_code}")
                return {"status": "error", "code": response.status_code}
    except Exception as e:
        print(f"  ❌ Failed to connect to LangGraph: {e}")
        return {"status": "disconnected", "error": str(e)}

async def main():
    """Run the complete test workflow"""
    print("=" * 60)
    print("LangSmith Tracing Test for EmailPilot Calendar")
    print("=" * 60)
    
    # Test LangGraph connection
    langgraph_status = await test_langgraph_connection()
    print(f"LangGraph status: {langgraph_status}")
    
    # Run the main workflow
    result = await plan_campaign_workflow(
        brand="Test Brand",
        month="2025-02"
    )
    
    print("\n" + "=" * 60)
    print("Workflow completed successfully!")
    print("=" * 60)
    
    # Print trace URL
    project = os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
    print(f"\n🔍 View trace in LangSmith:")
    print(f"   https://smith.langchain.com/projects/{project}")
    
    print("\n📊 Result summary:")
    print(f"   Brand: {result['brand']}")
    print(f"   Month: {result['month']}")
    print(f"   Events created: {len(result['events'])}")
    print(f"   Optimization: {result['optimized']['best_day']} at {result['optimized']['best_time']}")
    
    return result

if __name__ == "__main__":
    # Run the async main function
    result = asyncio.run(main())
    print("\n✅ Test completed!")