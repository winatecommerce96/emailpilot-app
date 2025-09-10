#!/usr/bin/env python3
"""
Test script for Calendar Orchestrator V2
Tests the enhanced multi-agent orchestration with Klaviyo MCP Enhanced
"""
import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_orchestrator_health():
    """Test if the orchestrator endpoint is healthy"""
    print("🔍 Testing orchestrator health...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/calendar/v2/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Orchestrator is {data.get('status', 'unknown')}")
                print(f"   Version: {data.get('version', 'unknown')}")
                print(f"   Features: {json.dumps(data.get('features', {}), indent=2)}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to orchestrator: {e}")
            return False

async def test_mcp_gateway():
    """Test if MCP Gateway is operational"""
    print("\n🔍 Testing MCP Gateway...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/api/mcp/gateway/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ MCP Gateway is {data.get('gateway', 'unknown')}")
                
                # Check Enhanced MCP
                enhanced = data.get('enhanced_mcp', {})
                if enhanced.get('enabled'):
                    print(f"✅ Klaviyo Enhanced MCP is enabled at {enhanced.get('url')}")
                else:
                    print(f"⚠️  Klaviyo Enhanced MCP is disabled")
                    
                return True
            else:
                print(f"❌ MCP Gateway check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to MCP Gateway: {e}")
            return False

async def test_orchestration(client_id="rogue-creamery", month="2025-03", dialogue=None):
    """Test the full orchestration flow"""
    print(f"\n🚀 Testing full orchestration for {client_id} - {month}")
    if dialogue:
        print(f"   With dialogue: {dialogue[:50]}...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Prepare request
            request_data = {
                "client_id": client_id,
                "month": month,
                "dialogue_input": dialogue,
                "include_historical": True,
                "include_recent": True,
                "use_ai_planning": True
            }
            
            print("\n📨 Sending orchestration request...")
            response = await client.post(
                "http://localhost:8000/api/calendar/v2/orchestrate",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Orchestration completed successfully!")
                print(f"   Calendar ID: {result.get('calendar_id')}")
                print(f"   Total Campaigns: {result.get('total_campaigns')}")
                print(f"   Expected Revenue: ${result.get('expected_revenue', 0):,.2f}")
                print(f"   AI Generated: {result.get('ai_generated')}")
                print(f"   Dialogue Incorporated: {result.get('dialogue_incorporated')}")
                print(f"   Processing Time: {result.get('processing_time', 0):.2f}s")
                
                # Show campaigns
                events = result.get('calendar_events', [])
                if events:
                    print(f"\n📅 Generated Campaigns:")
                    for i, event in enumerate(events[:5], 1):  # Show first 5
                        print(f"   {i}. {event.get('title')} - {event.get('planned_send_datetime')}")
                        print(f"      Segment: {event.get('segment')}")
                        print(f"      Expected Revenue: ${event.get('expected_revenue', 0):,.2f}")
                        print(f"      Confidence: {event.get('confidence_score', 0):.0%}")
                
                return True
            else:
                print(f"❌ Orchestration failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except httpx.TimeoutException:
            print(f"❌ Orchestration timed out (>60s)")
            return False
        except Exception as e:
            print(f"❌ Orchestration error: {e}")
            return False

async def test_streaming_orchestration(client_id="rogue-creamery", month="2025-03"):
    """Test the streaming orchestration endpoint"""
    print(f"\n🌊 Testing streaming orchestration for {client_id} - {month}")
    
    # Note: httpx doesn't natively support SSE, so we'll use a simple approach
    print("⚠️  Streaming test requires manual verification in browser")
    print(f"   Open: http://localhost:8000/api/calendar/v2/orchestrate/stream?client_id={client_id}&month={month}")
    return True

async def test_orchestration_status(calendar_id):
    """Test getting orchestration status"""
    print(f"\n🔍 Testing orchestration status for {calendar_id}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://localhost:8000/api/calendar/v2/status/{calendar_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Calendar status retrieved")
                print(f"   Status: {data.get('status')}")
                print(f"   Total Campaigns: {data.get('total_campaigns')}")
                print(f"   Expected Revenue: ${data.get('expected_revenue', 0):,.2f}")
                print(f"   Features: {json.dumps(data.get('features', {}), indent=2)}")
                return True
            elif response.status_code == 404:
                print(f"⚠️  Calendar not found")
                return False
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return False

async def test_client_insights(client_id="rogue-creamery"):
    """Test getting AI insights for a client"""
    print(f"\n💡 Testing AI insights for {client_id}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://localhost:8000/api/calendar/v2/insights/{client_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Insights retrieved")
                print(f"   Total Orchestrations: {data.get('total_orchestrations')}")
                
                insights = data.get('insights', {})
                if insights:
                    print(f"   Average Revenue: ${insights.get('average_expected_revenue', 0):,.2f}")
                    print(f"   AI Adoption: {insights.get('ai_adoption_rate', 0):.0%}")
                    print(f"   Dialogue Usage: {insights.get('dialogue_usage_rate', 0):.0%}")
                
                recommendations = data.get('recommendations', [])
                if recommendations:
                    print(f"\n   📝 Recommendations:")
                    for rec in recommendations:
                        print(f"      - {rec}")
                
                return True
            else:
                print(f"❌ Insights retrieval failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Insights error: {e}")
            return False

async def main():
    """Run all tests"""
    print("="*70)
    print("CALENDAR ORCHESTRATOR V2 TEST SUITE")
    print("="*70)
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Check prerequisites
    health_ok = await test_orchestrator_health()
    if not health_ok:
        print("\n⚠️  Orchestrator not healthy. Make sure the server is running:")
        print("   uvicorn main_firestore:app --port 8000 --host localhost --reload")
        return
    
    mcp_ok = await test_mcp_gateway()
    if not mcp_ok:
        print("\n⚠️  MCP Gateway not operational. Check if Enhanced MCP is running:")
        print("   cd services/klaviyo_mcp_enhanced && npm start")
    
    # Test orchestration with different scenarios
    print("\n" + "="*70)
    print("TEST 1: Basic Orchestration (No Dialogue)")
    print("="*70)
    await test_orchestration(
        client_id="rogue-creamery",
        month="2025-03"
    )
    
    print("\n" + "="*70)
    print("TEST 2: Orchestration with Dialogue Input")
    print("="*70)
    await test_orchestration(
        client_id="rogue-creamery",
        month="2025-04",
        dialogue="Focus on cheese promotions and spring themes. Include Easter campaign and Earth Day sustainability message."
    )
    
    # Test status and insights
    print("\n" + "="*70)
    print("TEST 3: Calendar Status Check")
    print("="*70)
    await test_orchestration_status("rogue-creamery_202503")
    
    print("\n" + "="*70)
    print("TEST 4: Client Insights")
    print("="*70)
    await test_client_insights("rogue-creamery")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)
    print(f"Completed at: {datetime.now().isoformat()}")
    print("\n📋 Next Steps:")
    print("1. Check the Firestore console for created calendar events")
    print("2. Test the frontend component at /calendar page")
    print("3. Verify LangSmith traces at https://smith.langchain.com/")
    print("4. Check MCP Gateway logs for Klaviyo Enhanced interactions")

if __name__ == "__main__":
    asyncio.run(main())