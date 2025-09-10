#!/usr/bin/env python3
"""
Test script for workflow execution functionality
Tests the calendar workflow execution through the API
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_CLIENT = {
    "id": "milagro-mushrooms",
    "name": "Milagro Mushrooms"
}

async def test_calendar_workflow():
    """Test the calendar workflow execution"""
    print("🧪 Testing Calendar Workflow Execution")
    print("=" * 50)
    
    # Prepare test parameters
    next_month = datetime.now().replace(month=datetime.now().month + 1).strftime("%Y-%m")
    
    params = {
        "client_id": TEST_CLIENT["id"],
        "client_name": TEST_CLIENT["name"],
        "selected_month": next_month,
        "campaign_count": 8,
        "sales_goal": 35000,
        "optimization_goal": "balanced",
        "additional_context": "Test execution from workflow manager - focus on holiday promotions",
        "use_mock_data": True  # Use mock data for fast testing
    }
    
    print(f"📅 Parameters:")
    print(f"  Client: {params['client_name']}")
    print(f"  Month: {params['selected_month']}")
    print(f"  Campaigns: {params['campaign_count']}")
    print(f"  Sales Goal: ${params['sales_goal']:,}")
    print(f"  Context: {params['additional_context']}")
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Execute the workflow
            print("🚀 Executing workflow...")
            response = await client.post(
                f"{BASE_URL}/api/calendar/workflow/execute",
                json=params
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success"):
                    print("✅ Workflow executed successfully!")
                    print(f"⏱️  Execution time: {result.get('execution_time', 0):.2f}s")
                    
                    if result.get("calendar"):
                        calendar = result["calendar"]
                        campaigns = calendar.get("campaigns", [])
                        print(f"📊 Generated {len(campaigns)} campaigns")
                        
                        # Display first 3 campaigns
                        for i, campaign in enumerate(campaigns[:3], 1):
                            print(f"\n  Campaign {i}:")
                            print(f"    Name: {campaign.get('name', 'Unnamed')}")
                            print(f"    Date: {campaign.get('date', 'TBD')}")
                            print(f"    Type: {campaign.get('type', 'Unknown')}")
                            print(f"    Segment: {campaign.get('segment', 'All')}")
                        
                        if len(campaigns) > 3:
                            print(f"\n  ... and {len(campaigns) - 3} more campaigns")
                    
                    print("\n🔗 View the calendar at: http://localhost:8000/static/calendar_master.html")
                    return True
                else:
                    print(f"❌ Workflow failed: {result.get('message', 'Unknown error')}")
                    if result.get("errors"):
                        for error in result["errors"]:
                            print(f"   - {error}")
                    return False
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                return False
                
        except httpx.TimeoutException:
            print("⏱️ Request timed out (60s). The workflow might still be running.")
            print("   Check LangGraph Studio for execution status.")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def test_workflow_status():
    """Test checking workflow execution status"""
    print("\n🔍 Testing Workflow Status Check")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/workflow-agents/workflows")
            
            if response.status_code == 200:
                data = response.json()
                workflows = data.get("workflows", [])
                
                print(f"📋 Found {len(workflows)} workflows:")
                for workflow in workflows:
                    status = "✅ Active" if workflow.get("status") == "active" else "⚠️ Inactive"
                    langgraph = "🔗 LangGraph" if workflow.get("langgraph_enabled") else "📝 Standard"
                    print(f"  • {workflow.get('icon', '🔄')} {workflow.get('name', 'Unknown')}")
                    print(f"    {status} | {langgraph} | {workflow.get('complexity', 'Unknown')} complexity")
                
                return True
            else:
                print(f"❌ Failed to fetch workflows: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def main():
    """Run all tests"""
    print("🚀 Workflow Execution Test Suite")
    print("=" * 50)
    print("Make sure the server is running at http://localhost:8000")
    print()
    
    # Test workflow status endpoint
    status_ok = await test_workflow_status()
    
    if status_ok:
        # Test calendar workflow execution
        execution_ok = await test_calendar_workflow()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        print(f"  Workflow Status: {'✅ Passed' if status_ok else '❌ Failed'}")
        print(f"  Calendar Execution: {'✅ Passed' if execution_ok else '❌ Failed'}")
        
        if status_ok and execution_ok:
            print("\n✨ All tests passed! The workflow execution system is working.")
            print("\n📝 Next steps:")
            print("  1. Open http://localhost:8000/static/workflow_manager.html")
            print("  2. Click 'Run' on any workflow card")
            print("  3. Fill in the parameters")
            print("  4. Watch it execute!")
        else:
            print("\n⚠️ Some tests failed. Check the error messages above.")
    else:
        print("\n⚠️ Could not connect to workflows API. Is the server running?")

if __name__ == "__main__":
    asyncio.run(main())