#!/usr/bin/env python3
"""
Test script for Enhanced Client Management with Secret Manager integration
Tests the complete flow of client CRUD operations and LangChain variable discovery
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional
import httpx
import random
import string

# Configuration
API_BASE = "http://localhost:8000"
TEST_CLIENT_PREFIX = "test_client_"

class ClientManagementTester:
    def __init__(self):
        self.client = httpx.Client(base_url=API_BASE, timeout=30.0)
        self.test_results = []
        self.test_client_id = None
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
        
    def generate_test_client_data(self) -> Dict:
        """Generate comprehensive test client data"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        client_name = f"Test Client {random_suffix}"
        
        return {
            # Basic Info
            "name": client_name,
            "description": f"Test client for automated testing - {datetime.now().isoformat()}",
            "contact_email": f"test_{random_suffix}@example.com",
            "contact_name": f"Test Contact {random_suffix}",
            "website": f"https://test-{random_suffix}.example.com",
            "is_active": True,
            
            # API Info
            "klaviyo_api_key": f"pk_test_{random_suffix}_{'x' * 32}",  # Fake test key
            "metric_id": f"TEST_METRIC_{random_suffix}",
            
            # Brand Manager
            "client_voice": "Professional, friendly, and approachable test voice",
            "client_background": "Test company specializing in automated testing",
            
            # PM
            "asana_project_link": f"https://app.asana.com/test/{random_suffix}",
            
            # Affinity Segments
            "affinity_segment_1_name": "Test Segment 1",
            "affinity_segment_1_definition": "Users who love testing",
            "affinity_segment_2_name": "Test Segment 2", 
            "affinity_segment_2_definition": "Power testers with high engagement",
            "affinity_segment_3_name": "Test Segment 3",
            "affinity_segment_3_definition": "Automated test enthusiasts",
            
            # Growth
            "key_growth_objective": "testing_coverage",
            "timezone": "America/New_York"
        }
        
    async def test_authentication(self):
        """Test authentication"""
        self.log("Testing authentication...")
        
        try:
            # Try guest login for testing
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
            
    async def test_create_client(self):
        """Test creating a new client with all fields"""
        self.log("Testing client creation with Secret Manager...")
        
        client_data = self.generate_test_client_data()
        
        try:
            response = self.client.post("/api/admin/clients", json=client_data)
            
            if response.status_code == 200:
                data = response.json()
                self.test_client_id = data.get("client_id")
                
                # Verify response structure
                checks = [
                    ("client_id" in data, "Client ID returned"),
                    (data.get("name") == client_data["name"], "Name matches"),
                    ("client_slug" in data, "Client slug generated"),
                    (data.get("has_klaviyo_key") == True, "API key stored"),
                    ("klaviyo_api_key_secret" in data, "Secret reference created"),
                    ("klaviyo_api_key" not in data, "Raw API key not exposed"),
                ]
                
                all_passed = all(check[0] for check in checks)
                details = ", ".join([check[1] for check in checks if check[0]])
                failures = ", ".join([check[1] for check in checks if not check[0]])
                
                self.record_test(
                    "Create Client", 
                    all_passed,
                    details if all_passed else f"Failed: {failures}"
                )
                
                # Log created client details
                self.log(f"Created client: {data.get('name')} (ID: {self.test_client_id})")
                self.log(f"Client slug: {data.get('client_slug')}")
                self.log(f"Secret reference: {data.get('klaviyo_api_key_secret')}")
                
                return self.test_client_id
            else:
                error = response.json() if response.text else {}
                self.record_test("Create Client", False, f"Status {response.status_code}: {error}")
                return None
                
        except Exception as e:
            self.record_test("Create Client", False, str(e))
            return None
            
    async def test_get_client(self):
        """Test retrieving client with all fields"""
        if not self.test_client_id:
            self.log("Skipping GET test - no client ID", "WARNING")
            return
            
        self.log(f"Testing client retrieval for {self.test_client_id}...")
        
        try:
            response = self.client.get(f"/api/admin/clients/{self.test_client_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check all field categories are present
                required_fields = [
                    # Basic
                    "name", "client_slug", "description", "is_active",
                    # Brand
                    "client_voice", "client_background",
                    # Segments
                    "affinity_segment_1_name", "affinity_segment_1_definition",
                    # Growth
                    "key_growth_objective", "timezone",
                    # Metadata
                    "created_at", "updated_at"
                ]
                
                missing_fields = [f for f in required_fields if f not in data]
                
                self.record_test(
                    "Get Client",
                    len(missing_fields) == 0,
                    f"All fields present" if not missing_fields else f"Missing: {missing_fields}"
                )
                
                # Verify API key handling
                if "klaviyo_api_key" in data:
                    self.record_test("API Key Security", False, "Raw API key exposed!")
                else:
                    self.record_test("API Key Security", True, "Raw key not exposed")
                    
            else:
                self.record_test("Get Client", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.record_test("Get Client", False, str(e))
            
    async def test_update_client(self):
        """Test updating client fields"""
        if not self.test_client_id:
            self.log("Skipping UPDATE test - no client ID", "WARNING")
            return
            
        self.log(f"Testing client update for {self.test_client_id}...")
        
        update_data = {
            "description": f"Updated test description at {datetime.now().isoformat()}",
            "client_voice": "Updated professional voice with more enthusiasm",
            "affinity_segment_1_name": "Updated Test Segment",
            "key_growth_objective": "increased_testing"
        }
        
        try:
            response = self.client.put(
                f"/api/admin/clients/{self.test_client_id}",
                json=update_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify updates
                checks = [
                    (data.get("description") == update_data["description"], "Description updated"),
                    (data.get("client_voice") == update_data["client_voice"], "Voice updated"),
                    (data.get("affinity_segment_1_name") == update_data["affinity_segment_1_name"], "Segment updated"),
                    (data.get("key_growth_objective") == update_data["key_growth_objective"], "Growth objective updated"),
                    ("updated_at" in data, "Timestamp updated"),
                ]
                
                all_passed = all(check[0] for check in checks)
                self.record_test(
                    "Update Client",
                    all_passed,
                    ", ".join([check[1] for check in checks if check[0]])
                )
            else:
                self.record_test("Update Client", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.record_test("Update Client", False, str(e))
            
    async def test_langchain_variables(self):
        """Test LangChain variable discovery"""
        self.log("Testing LangChain variable discovery...")
        
        try:
            # Test general schema discovery
            response = self.client.get("/api/admin/langchain/orchestration/variables/agent")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for client variables
                client_vars = [
                    v for v in data.get("variables", [])
                    if v.get("source", "").startswith("firestore.clients")
                ]
                
                # Check for new fields
                expected_fields = [
                    "client_slug", "client_voice", "client_background",
                    "affinity_segment_1_name", "key_growth_objective", "timezone"
                ]
                
                found_fields = [v.get("name") for v in client_vars]
                missing = [f for f in expected_fields if f not in found_fields]
                
                self.record_test(
                    "LangChain Variables",
                    len(missing) == 0,
                    f"Found {len(client_vars)} client variables" if not missing else f"Missing: {missing}"
                )
                
                # Test client-specific discovery if we have a client
                if self.test_client_id:
                    response = self.client.get(
                        f"/api/admin/langchain/orchestration/variables/agent?client_id={self.test_client_id}"
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.record_test(
                            "Client-Specific Variables",
                            True,
                            f"Retrieved {data.get('total_variables', 0)} variables"
                        )
                    else:
                        self.record_test("Client-Specific Variables", False, f"Status: {response.status_code}")
                        
            else:
                self.record_test("LangChain Variables", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.record_test("LangChain Variables", False, str(e))
            
    async def test_list_clients(self):
        """Test listing all clients"""
        self.log("Testing client listing...")
        
        try:
            response = self.client.get("/api/admin/clients")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                has_structure = all([
                    "clients" in data,
                    "total_clients" in data,
                    "active_clients" in data,
                    "clients_with_keys" in data
                ])
                
                self.record_test(
                    "List Clients",
                    has_structure,
                    f"Found {data.get('total_clients', 0)} clients"
                )
                
                # Verify our test client is in the list
                if self.test_client_id:
                    test_client = next(
                        (c for c in data.get("clients", []) if c.get("id") == self.test_client_id),
                        None
                    )
                    
                    self.record_test(
                        "Test Client in List",
                        test_client is not None,
                        "Test client found" if test_client else "Test client not found"
                    )
            else:
                self.record_test("List Clients", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.record_test("List Clients", False, str(e))
            
    async def cleanup_test_client(self):
        """Clean up test client"""
        if not self.test_client_id:
            return
            
        self.log(f"Cleaning up test client {self.test_client_id}...")
        
        try:
            response = self.client.delete(f"/api/admin/clients/{self.test_client_id}")
            
            if response.status_code in [200, 204]:
                self.record_test("Cleanup", True, "Test client deleted")
            else:
                self.record_test("Cleanup", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.record_test("Cleanup", False, str(e))
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
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
        print("ENHANCED CLIENT MANAGEMENT TEST SUITE")
        print("="*60)
        print(f"Testing against: {API_BASE}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Run tests
        await self.test_authentication()
        
        if self.auth_token:
            await self.test_create_client()
            await self.test_get_client()
            await self.test_update_client()
            await self.test_list_clients()
            await self.test_langchain_variables()
            await self.cleanup_test_client()
        else:
            self.log("Skipping tests - authentication failed", "ERROR")
            
        # Print summary
        self.print_summary()
        
        # Return exit code
        failed = sum(1 for r in self.test_results if not r["passed"])
        return 0 if failed == 0 else 1

async def main():
    """Main entry point"""
    tester = ClientManagementTester()
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