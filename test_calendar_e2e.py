#!/usr/bin/env python3
"""
End-to-End Calendar Automation Test
Tests the complete calendar automation pipeline with real server interaction
"""
import asyncio
import json
import time
import httpx
from datetime import datetime
from typing import Dict, Any

# Test Configuration
BASE_URL = "http://localhost:8000"
TEST_CLIENT_DATA = {
    "client_display_name": "E2E Test Client",
    "client_firestore_id": "e2e_test_client_" + str(int(time.time())),
    "klaviyo_account_id": "test_klaviyo_e2e",
    "target_month": 10,
    "target_year": 2025,
    "dry_run": True  # Safe for testing
}

class CalendarE2ETest:
    """End-to-end test runner"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        
    async def run_all_tests(self):
        """Run complete E2E test suite"""
        print("🚀 Starting Calendar Automation E2E Tests")
        print("=" * 60)
        
        try:
            # Test 1: Server Health Check
            await self.test_server_health()
            
            # Test 2: Calendar Build Endpoint
            correlation_id = await self.test_calendar_build()
            
            # Test 3: Status Monitoring
            await self.test_status_monitoring(correlation_id)
            
            # Test 4: Frontend Integration
            await self.test_frontend_endpoints()
            
            # Test 5: Data Verification
            await self.test_data_verification()
            
            # Print Results
            self.print_test_results()
            
        except Exception as e:
            print(f"❌ E2E Test Suite Failed: {e}")
            return False
        finally:
            await self.client.aclose()
        
        return all(result["passed"] for result in self.test_results)
    
    async def test_server_health(self):
        """Test server health and orchestrator availability"""
        print("🔍 Testing server health...")
        
        try:
            # Check main health endpoint
            response = await self.client.get(f"{BASE_URL}/health")
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            
            health_data = response.json()
            assert health_data["status"] == "ok", "Health status not OK"
            
            # Check calendar orchestrator health
            response = await self.client.get(f"{BASE_URL}/api/calendar/health")
            assert response.status_code == 200, "Calendar orchestrator health failed"
            
            orchestrator_health = response.json()
            assert orchestrator_health["service"] == "calendar_orchestrator"
            
            self.test_results.append({
                "test": "Server Health",
                "passed": True,
                "message": "All health checks passed"
            })
            print("✅ Server health check passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Server Health", 
                "passed": False,
                "message": str(e)
            })
            print(f"❌ Server health check failed: {e}")
            raise
    
    async def test_calendar_build(self) -> str:
        """Test calendar build endpoint and return correlation ID"""
        print("🔧 Testing calendar build automation...")
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/calendar/build",
                json=TEST_CLIENT_DATA
            )
            
            assert response.status_code == 200, f"Calendar build failed: {response.status_code} - {response.text}"
            
            build_data = response.json()
            assert build_data["success"] is True, "Build success flag not True"
            assert "correlation_id" in build_data, "No correlation ID returned"
            assert "status_endpoint" in build_data, "No status endpoint provided"
            
            correlation_id = build_data["correlation_id"]
            
            self.test_results.append({
                "test": "Calendar Build",
                "passed": True,
                "message": f"Build started with correlation ID: {correlation_id}"
            })
            print(f"✅ Calendar build initiated: {correlation_id}")
            
            return correlation_id
            
        except Exception as e:
            self.test_results.append({
                "test": "Calendar Build",
                "passed": False,
                "message": str(e)
            })
            print(f"❌ Calendar build failed: {e}")
            raise
    
    async def test_status_monitoring(self, correlation_id: str):
        """Test status monitoring and progress tracking"""
        print("📊 Testing status monitoring...")
        
        try:
            max_polls = 30  # 30 seconds max
            poll_interval = 1
            final_status = None
            
            for i in range(max_polls):
                response = await self.client.get(
                    f"{BASE_URL}/api/calendar/build/status/{correlation_id}"
                )
                
                if response.status_code == 404:
                    # Status not found yet, wait and retry
                    await asyncio.sleep(poll_interval)
                    continue
                
                assert response.status_code == 200, f"Status check failed: {response.status_code}"
                
                status_data = response.json()
                assert "status" in status_data, "No status field in response"
                assert "progress" in status_data, "No progress field in response"
                assert "message" in status_data, "No message field in response"
                
                print(f"  📈 Progress: {status_data['progress']:.1f}% - {status_data['message']}")
                
                # Check if complete
                if status_data["status"] in ["completed", "failed"]:
                    final_status = status_data
                    break
                
                await asyncio.sleep(poll_interval)
            
            assert final_status is not None, "Status monitoring timed out"
            assert final_status["status"] == "completed", f"Build failed: {final_status.get('message', 'Unknown error')}"
            assert final_status["progress"] == 100.0, "Progress not 100% on completion"
            
            self.test_results.append({
                "test": "Status Monitoring",
                "passed": True,
                "message": f"Monitoring complete: {final_status['message']}"
            })
            print("✅ Status monitoring completed successfully")
            
        except Exception as e:
            self.test_results.append({
                "test": "Status Monitoring",
                "passed": False,
                "message": str(e)
            })
            print(f"❌ Status monitoring failed: {e}")
            raise
    
    async def test_frontend_endpoints(self):
        """Test frontend-facing endpoints"""
        print("🖥️  Testing frontend endpoints...")
        
        try:
            # Test clients endpoint
            response = await self.client.get(f"{BASE_URL}/api/calendar/clients")
            assert response.status_code == 200, f"Clients endpoint failed: {response.status_code}"
            
            clients_data = response.json()
            assert isinstance(clients_data, list), "Clients data not a list"
            
            # Test events endpoint (should work even if no events)
            response = await self.client.get(f"{BASE_URL}/api/calendar/events")
            assert response.status_code == 200, f"Events endpoint failed: {response.status_code}"
            
            events_data = response.json()
            assert isinstance(events_data, list), "Events data not a list"
            
            # Test calendar stats endpoint
            if clients_data:
                client_id = clients_data[0]["id"]
                response = await self.client.get(f"{BASE_URL}/api/calendar/stats?client_id={client_id}")
                assert response.status_code == 200, f"Stats endpoint failed: {response.status_code}"
                
                stats_data = response.json()
                assert "total_events" in stats_data, "Stats missing total_events"
                assert "event_types" in stats_data, "Stats missing event_types"
            
            self.test_results.append({
                "test": "Frontend Endpoints",
                "passed": True,
                "message": "All frontend endpoints responding correctly"
            })
            print("✅ Frontend endpoints test passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Frontend Endpoints",
                "passed": False,
                "message": str(e)
            })
            print(f"❌ Frontend endpoints test failed: {e}")
            raise
    
    async def test_data_verification(self):
        """Test data integrity and schema compliance"""
        print("🔍 Testing data verification...")
        
        try:
            # Since we used dry_run=True, we won't have actual data written
            # But we can test the schema validation endpoints
            
            # Test that the calendar automation created proper logs
            # (This would need admin access to Firestore in a real scenario)
            
            # For now, test the schema validation by checking endpoint responses
            response = await self.client.get(f"{BASE_URL}/api/calendar/events")
            events_data = response.json()
            
            # Verify event schema if events exist
            for event in events_data:
                required_fields = ["id", "title", "date", "client_id"]
                for field in required_fields:
                    assert field in event, f"Event missing required field: {field}"
            
            self.test_results.append({
                "test": "Data Verification",
                "passed": True,
                "message": f"Schema validation passed for {len(events_data)} events"
            })
            print("✅ Data verification passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Data Verification",
                "passed": False,
                "message": str(e)
            })
            print(f"❌ Data verification failed: {e}")
            raise
    
    def print_test_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("📋 E2E Test Results Summary")
        print("=" * 60)
        
        passed_count = 0
        failed_count = 0
        
        for result in self.test_results:
            status_icon = "✅" if result["passed"] else "❌"
            status_text = "PASSED" if result["passed"] else "FAILED"
            
            print(f"{status_icon} {result['test']}: {status_text}")
            print(f"   Message: {result['message']}")
            
            if result["passed"]:
                passed_count += 1
            else:
                failed_count += 1
        
        print("-" * 60)
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Success Rate: {(passed_count / len(self.test_results) * 100):.1f}%")
        
        if failed_count == 0:
            print("\n🎉 ALL TESTS PASSED! Calendar automation is working correctly.")
        else:
            print(f"\n⚠️  {failed_count} test(s) failed. Please check the implementation.")

# CLI execution functions
async def run_quick_test():
    """Run a quick calendar automation test"""
    print("🚀 Quick Calendar Automation Test")
    print("This will test the calendar build endpoint with dry_run=True")
    print(f"Test payload: {json.dumps(TEST_CLIENT_DATA, indent=2)}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Health check
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print(f"❌ Server not healthy: {response.status_code}")
                return False
            
            # Build calendar
            response = await client.post(f"{BASE_URL}/api/calendar/build", json=TEST_CLIENT_DATA)
            if response.status_code != 200:
                print(f"❌ Calendar build failed: {response.status_code} - {response.text}")
                return False
            
            build_data = response.json()
            correlation_id = build_data["correlation_id"]
            print(f"✅ Calendar automation started: {correlation_id}")
            
            # Monitor for 10 seconds
            for i in range(10):
                response = await client.get(f"{BASE_URL}/api/calendar/build/status/{correlation_id}")
                if response.status_code == 200:
                    status = response.json()
                    print(f"   Progress: {status['progress']:.1f}% - {status['message']}")
                    
                    if status["status"] in ["completed", "failed"]:
                        if status["status"] == "completed":
                            print("🎉 Quick test PASSED!")
                            return True
                        else:
                            print(f"❌ Quick test FAILED: {status['message']}")
                            return False
                
                await asyncio.sleep(1)
            
            print("⏰ Quick test timed out")
            return False
            
        except Exception as e:
            print(f"❌ Quick test error: {e}")
            return False

def create_test_client():
    """Create a test client in Firestore for testing"""
    test_client = {
        "name": "E2E Test Client",
        "email": "test@emailpilot.ai",
        "klaviyo_account_id": "test_klaviyo_e2e",
        "is_active": True,
        "client_voice": "professional",
        "client_background": "Test client for E2E automation testing"
    }
    
    print("Test Client Data:")
    print(json.dumps(test_client, indent=2))
    print("\nUse this data to create a test client via the admin interface")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            # Quick test
            result = asyncio.run(run_quick_test())
            sys.exit(0 if result else 1)
            
        elif command == "create-client":
            # Create test client helper
            create_test_client()
            sys.exit(0)
            
        elif command == "full":
            # Full E2E test suite
            test_runner = CalendarE2ETest()
            result = asyncio.run(test_runner.run_all_tests())
            sys.exit(0 if result else 1)
    
    # Default: run full test suite
    print("Calendar Automation E2E Test")
    print("Commands:")
    print("  python test_calendar_e2e.py quick          # Quick test")
    print("  python test_calendar_e2e.py full           # Full test suite")
    print("  python test_calendar_e2e.py create-client  # Show test client data")
    print()
    
    # Run full test by default
    test_runner = CalendarE2ETest()
    result = asyncio.run(test_runner.run_all_tests())
    sys.exit(0 if result else 1)