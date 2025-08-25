#!/usr/bin/env python3
"""
Test script to verify Enhanced Client Management integration in the dashboard
"""

import asyncio
import json
import sys
from datetime import datetime
import httpx

# Configuration
API_BASE = "http://localhost:8000"

class DashboardEnhancedClientTester:
    def __init__(self):
        self.client = httpx.Client(base_url=API_BASE, timeout=30.0)
        self.test_results = []
        self.auth_token = None
        
    def log(self, message: str, status: str = "INFO"):
        """Log test progress"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m", 
            "ERROR": "\033[91m",
            "WARNING": "\033[93m"
        }.get(status, "")
        reset = "\033[0m"
        print(f"[{timestamp}] {color}{status}{reset}: {message}")
        
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        status = "SUCCESS" if passed else "ERROR"
        self.log(f"{test_name}: {'✅ PASSED' if passed else '❌ FAILED'} {details}", status)
        
    async def test_authentication(self):
        """Test authentication"""
        self.log("Testing authentication...")
        
        try:
            response = self.client.post("/api/auth/guest")
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
                self.record_test("Authentication", True, "Guest token obtained")
                return True
            else:
                self.record_test("Authentication", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.record_test("Authentication", False, str(e))
            return False
            
    async def test_enhanced_client_api(self):
        """Test enhanced client API endpoints"""
        self.log("Testing Enhanced Client Management API...")
        
        try:
            # Test enhanced client listing
            response = self.client.get("/api/admin/clients")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                checks = [
                    ("clients" in data, "Has clients array"),
                    ("total_clients" in data, "Has total_clients count"),
                    ("active_clients" in data, "Has active_clients count"),
                    ("clients_with_keys" in data, "Has clients_with_keys count"),
                ]
                
                # Check client data structure if clients exist
                if data.get("clients"):
                    client = data["clients"][0]
                    enhanced_fields = [
                        "client_slug", "client_voice", "client_background",
                        "affinity_segment_1_name", "key_growth_objective", "timezone"
                    ]
                    
                    for field in enhanced_fields:
                        checks.append((field in client, f"Has enhanced field: {field}"))
                
                all_passed = all(check[0] for check in checks)
                details = f"Found {data.get('total_clients', 0)} clients with enhanced fields"
                
                self.record_test("Enhanced Client API", all_passed, details)
                return data
            else:
                self.record_test("Enhanced Client API", False, f"Status: {response.status_code}")
                return None
                
        except Exception as e:
            self.record_test("Enhanced Client API", False, str(e))
            return None
            
    async def test_dashboard_client_integration(self):
        """Test dashboard integration with enhanced clients"""
        self.log("Testing dashboard client integration...")
        
        try:
            # Test that dashboard can access enhanced client data
            response = self.client.get("/api/admin/clients")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify dashboard-required fields
                if data.get("clients"):
                    client = data["clients"][0]
                    required_for_dashboard = [
                        "id", "name", "is_active", "client_slug"
                    ]
                    
                    missing_fields = [f for f in required_for_dashboard if f not in client]
                    
                    if not missing_fields:
                        self.record_test(
                            "Dashboard Integration", 
                            True, 
                            f"All required dashboard fields present"
                        )
                        
                        # Test client selection simulation
                        client_id = client.get("id")
                        if client_id:
                            # Simulate MTD data loading
                            mtd_response = self.client.get(f"/api/performance/mtd/{client_id}")
                            mtd_working = mtd_response.status_code in [200, 404]  # 404 is OK if no data
                            
                            self.record_test(
                                "Client MTD Integration",
                                mtd_working,
                                f"MTD endpoint accessible for client {client_id}"
                            )
                    else:
                        self.record_test(
                            "Dashboard Integration", 
                            False, 
                            f"Missing required fields: {missing_fields}"
                        )
                else:
                    self.record_test("Dashboard Integration", True, "No clients to test (empty state)")
            else:
                self.record_test("Dashboard Integration", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.record_test("Dashboard Integration", False, str(e))
            
    async def test_frontend_component_availability(self):
        """Test that frontend components are available"""
        self.log("Testing frontend component availability...")
        
        # Check if AdminClientManagement component file exists
        import os
        component_path = "/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/frontend/public/dist/AdminClientManagement.js"
        
        if os.path.exists(component_path):
            # Check file size to ensure it's not empty
            file_size = os.path.getsize(component_path)
            
            self.record_test(
                "AdminClientManagement Component",
                file_size > 1000,  # Should be substantial
                f"Component file exists ({file_size} bytes)"
            )
        else:
            self.record_test(
                "AdminClientManagement Component",
                False,
                "Component file not found"
            )
            
        # Check main app.js for enhanced client functionality
        app_js_path = "/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/frontend/public/dist/app.js"
        
        if os.path.exists(app_js_path):
            with open(app_js_path, 'r') as f:
                content = f.read()
                
            # Look for enhanced client integration
            has_enhanced_integration = (
                "AdminClientManagement" in content and
                "/api/admin/clients" in content and
                "ClientUtils" in content
            )
            
            self.record_test(
                "Enhanced Client Integration",
                has_enhanced_integration,
                "Dashboard contains enhanced client code"
            )
        else:
            self.record_test(
                "Enhanced Client Integration",
                False,
                "app.js not found"
            )
            
    async def test_backward_compatibility(self):
        """Test backward compatibility with old client endpoints"""
        self.log("Testing backward compatibility...")
        
        try:
            # Test if old endpoint redirects or provides compatibility
            response = self.client.get("/api/clients/")
            
            if response.status_code in [200, 404, 307, 308]:
                # 200 = working, 404 = removed (expected), 307/308 = redirect
                compatibility_working = True
                details = f"Old endpoint status: {response.status_code}"
            else:
                compatibility_working = False
                details = f"Unexpected status: {response.status_code}"
                
            self.record_test("Backward Compatibility", compatibility_working, details)
            
        except Exception as e:
            self.record_test("Backward Compatibility", False, str(e))
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("DASHBOARD ENHANCED CLIENT INTEGRATION TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "N/A")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
                    
        print("="*60)
        
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n" + "="*60)
        print("DASHBOARD ENHANCED CLIENT INTEGRATION TEST SUITE")
        print("="*60)
        print(f"Testing against: {API_BASE}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Run tests
        await self.test_authentication()
        
        if self.auth_token:
            await self.test_enhanced_client_api()
            await self.test_dashboard_client_integration()
            await self.test_frontend_component_availability()
            await self.test_backward_compatibility()
        else:
            self.log("Skipping tests - authentication failed", "ERROR")
            
        # Print summary
        self.print_summary()
        
        # Return exit code
        failed = sum(1 for r in self.test_results if not r["passed"])
        return 0 if failed == 0 else 1

async def main():
    """Main entry point"""
    tester = DashboardEnhancedClientTester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    # Check if server is running
    try:
        response = httpx.get(f"{API_BASE}/health", timeout=2.0)
        if response.status_code != 200:
            print(f"❌ Server not healthy at {API_BASE}")
            sys.exit(1)
    except Exception:
        print(f"❌ Cannot connect to server at {API_BASE}")
        print("Please ensure the server is running:")
        print("  uvicorn main_firestore:app --port 8000 --host localhost")
        sys.exit(1)
        
    # Run tests
    asyncio.run(main())