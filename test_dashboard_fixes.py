#!/usr/bin/env python3
"""
Comprehensive test script for EmailPilot Dashboard fixes verification
Tests all backend API endpoints and provides frontend integration checks
"""

import asyncio
import subprocess
import sys
import json
import os
import time
from pathlib import Path
import requests
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Configuration
BASE_URL = "http://localhost:8000"
TEST_CLIENT_ID = "demo_client_1"

class DashboardFixTester:
    def __init__(self):
        self.results = {
            "backend_api": {},
            "static_files": {},
            "frontend_build": {},
            "cors_config": {},
            "error_handling": {}
        }
        self.errors = []
        self.warnings = []
        
    def log_result(self, category: str, test: str, status: bool, message: str):
        """Log test result"""
        if category not in self.results:
            self.results[category] = {}
        
        self.results[category][test] = {
            "status": "PASS" if status else "FAIL",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {category.upper()}: {test} - {message}")
        
        if not status:
            self.errors.append(f"{category}: {test} - {message}")

    def log_warning(self, category: str, test: str, message: str):
        """Log warning"""
        warning_msg = f"{category}: {test} - {message}"
        self.warnings.append(warning_msg)
        print(f"⚠️ WARNING: {warning_msg}")

    async def test_build_system(self) -> bool:
        """Test 1: Frontend Build System"""
        print("\n" + "="*60)
        print("TESTING: Frontend Build System")
        print("="*60)
        
        # Check if build script exists
        build_script = Path("scripts/build_frontend.sh")
        if not build_script.exists():
            self.log_result("frontend_build", "build_script_exists", False, 
                          "Build script not found at scripts/build_frontend.sh")
            return False
        
        self.log_result("frontend_build", "build_script_exists", True, 
                       "Build script found")
        
        # Check if script is executable
        if not os.access(build_script, os.X_OK):
            self.log_warning("frontend_build", "script_executable", 
                           "Build script is not executable - fixing...")
            subprocess.run(["chmod", "+x", str(build_script)], check=True)
        
        # Run build script
        try:
            print("Running build script...")
            result = subprocess.run([str(build_script)], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=Path.cwd(),
                                  timeout=60)
            
            if result.returncode == 0:
                self.log_result("frontend_build", "build_execution", True, 
                               "Build script completed successfully")
                print(f"Build output: {result.stdout}")
            else:
                self.log_result("frontend_build", "build_execution", False, 
                               f"Build failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_result("frontend_build", "build_execution", False, 
                           "Build script timed out after 60 seconds")
            return False
        except Exception as e:
            self.log_result("frontend_build", "build_execution", False, 
                           f"Build script error: {str(e)}")
            return False
        
        # Check dist directory
        dist_dir = Path("frontend/public/dist")
        if dist_dir.exists():
            dist_files = list(dist_dir.glob("*.js"))
            self.log_result("frontend_build", "dist_files_created", True, 
                           f"Found {len(dist_files)} compiled files")
            
            # Check for key files
            key_files = ["app.js", "component-loader.js"]
            for file_name in key_files:
                file_path = dist_dir / file_name
                if file_path.exists():
                    self.log_result("frontend_build", f"{file_name}_exists", True, 
                                   f"{file_name} compiled successfully")
                else:
                    self.log_result("frontend_build", f"{file_name}_exists", False, 
                                   f"{file_name} not found in dist")
        else:
            self.log_result("frontend_build", "dist_files_created", False, 
                           "Dist directory not created")
            return False
        
        return True

    def test_backend_api_endpoints(self) -> bool:
        """Test 2: Backend API Endpoints"""
        print("\n" + "="*60)
        print("TESTING: Backend API Endpoints")
        print("="*60)
        
        # Test endpoints that should work
        endpoints = [
            ("/api/auth/session", "GET", "session_endpoint"),
            ("/api/auth/me", "GET", "auth_me_endpoint"),
            ("/api/admin/environment", "GET", "admin_environment"),
            ("/api/admin/system/status", "GET", "admin_system_status"),
            (f"/api/performance/mtd/{TEST_CLIENT_ID}", "GET", "performance_mtd"),
            ("/api/goals/clients", "GET", "goals_clients"),
            ("/api/admin/health", "GET", "admin_health"),
        ]
        
        all_passed = True
        
        for endpoint, method, test_name in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        self.log_result("backend_api", test_name, True, 
                                       f"Returns 200 JSON: {len(str(json_data))} chars")
                    except json.JSONDecodeError:
                        self.log_result("backend_api", test_name, False, 
                                       f"Returns 200 but not JSON: {response.text[:100]}")
                        all_passed = False
                
                elif response.status_code == 403 and "auth" in endpoint:
                    # Auth endpoints may return 403 in demo mode - check for clean response
                    try:
                        json_data = response.json()
                        self.log_result("backend_api", test_name, True, 
                                       "Returns clean 403 JSON (demo mode)")
                    except json.JSONDecodeError:
                        self.log_result("backend_api", test_name, False, 
                                       f"Returns 403 but not JSON: {response.text[:100]}")
                        all_passed = False
                
                elif response.status_code == 422:
                    self.log_result("backend_api", test_name, False, 
                                   f"Returns 422 validation error - API signature issue")
                    all_passed = False
                
                else:
                    self.log_result("backend_api", test_name, False, 
                                   f"HTTP {response.status_code}: {response.text[:100]}")
                    all_passed = False
                    
            except requests.ConnectionError:
                self.log_result("backend_api", test_name, False, 
                               "Connection failed - server not running?")
                all_passed = False
            except requests.Timeout:
                self.log_result("backend_api", test_name, False, 
                               "Request timed out")
                all_passed = False
            except Exception as e:
                self.log_result("backend_api", test_name, False, 
                               f"Request error: {str(e)}")
                all_passed = False
        
        return all_passed

    def test_static_file_serving(self) -> bool:
        """Test 3: Static File Serving"""
        print("\n" + "="*60)
        print("TESTING: Static File Serving")
        print("="*60)
        
        # Test dist file serving
        dist_files = [
            ("app.js", "application/javascript"),
            ("component-loader.js", "application/javascript"),
            ("Calendar.js", "application/javascript"),
        ]
        
        all_passed = True
        
        for filename, expected_content_type in dist_files:
            try:
                response = requests.get(f"{BASE_URL}/dist/{filename}", timeout=5)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    if 'javascript' in content_type.lower():
                        self.log_result("static_files", f"{filename}_serving", True, 
                                       f"Serves with correct MIME type: {content_type}")
                    else:
                        self.log_result("static_files", f"{filename}_serving", False, 
                                       f"Wrong MIME type: {content_type}")
                        all_passed = False
                    
                    # Check for HTML error responses
                    if response.text.strip().startswith('<\!DOCTYPE html>'):
                        self.log_result("static_files", f"{filename}_content", False, 
                                       "Returns HTML instead of JavaScript")
                        all_passed = False
                    else:
                        self.log_result("static_files", f"{filename}_content", True, 
                                       f"Returns JavaScript: {len(response.text)} chars")
                else:
                    self.log_result("static_files", f"{filename}_serving", False, 
                                   f"HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_result("static_files", f"{filename}_serving", False, 
                               f"Error: {str(e)}")
                all_passed = False
        
        return all_passed

    def test_cors_configuration(self) -> bool:
        """Test 4: CORS Configuration"""
        print("\n" + "="*60)
        print("TESTING: CORS Configuration")
        print("="*60)
        
        try:
            # Test preflight request
            headers = {
                'Origin': 'http://localhost:8000',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(f"{BASE_URL}/api/auth/session", 
                                      headers=headers, timeout=5)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            }
            
            if cors_headers['Access-Control-Allow-Origin']:
                self.log_result("cors_config", "allow_origin", True, 
                               f"Set to: {cors_headers['Access-Control-Allow-Origin']}")
            else:
                self.log_result("cors_config", "allow_origin", False, 
                               "Access-Control-Allow-Origin not set")
                return False
            
            if cors_headers['Access-Control-Allow-Credentials'] == 'true':
                self.log_result("cors_config", "allow_credentials", True, 
                               "Credentials allowed")
            else:
                self.log_warning("cors_config", "allow_credentials", 
                               "Credentials not explicitly allowed")
            
            return True
            
        except Exception as e:
            self.log_result("cors_config", "preflight_request", False, 
                           f"CORS test error: {str(e)}")
            return False

    def check_index_html_integration(self) -> bool:
        """Test 5: Check if index.html uses compiled files"""
        print("\n" + "="*60)
        print("TESTING: Index.html Integration")
        print("="*60)
        
        index_file = Path("frontend/public/index.html")
        if not index_file.exists():
            self.log_result("frontend_build", "index_html_exists", False, 
                           "index.html not found")
            return False
        
        content = index_file.read_text()
        
        # Check if it's using dist files
        if '/dist/' in content:
            self.log_result("frontend_build", "index_uses_dist", True, 
                           "index.html references dist files")
        else:
            self.log_result("frontend_build", "index_uses_dist", False, 
                           "index.html still uses src files - needs update")
            
            # Suggest the fix
            print("\n📝 REQUIRED ACTION: Update index.html to use compiled files")
            print("   Change script src from 'components/' to 'dist/'")
            print("   Remove 'type=\"text/babel\"' from script tags")
            print("   Remove Babel standalone dependency")
            return False
        
        # Check for Babel dependency
        if '@babel/standalone' in content:
            self.log_warning("frontend_build", "babel_dependency", 
                           "index.html still loads Babel - should be removed")
        else:
            self.log_result("frontend_build", "babel_removed", True, 
                           "Babel standalone dependency removed")
        
        return True

    def test_error_handling(self) -> bool:
        """Test 6: Error Handling"""
        print("\n" + "="*60)
        print("TESTING: Error Handling")
        print("="*60)
        
        # Test non-existent endpoints
        test_endpoints = [
            "/api/nonexistent",
            "/api/performance/mtd/nonexistent_client",
            "/api/goals/invalid_endpoint"
        ]
        
        all_passed = True
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
                
                if response.status_code in [404, 422, 400]:
                    try:
                        json_data = response.json()
                        self.log_result("error_handling", f"error_{response.status_code}", True, 
                                       f"Returns proper JSON error response")
                    except json.JSONDecodeError:
                        self.log_result("error_handling", f"error_{response.status_code}", False, 
                                       "Error response is not JSON")
                        all_passed = False
                else:
                    self.log_warning("error_handling", "unexpected_status", 
                                   f"{endpoint} returned {response.status_code}")
                    
            except Exception as e:
                self.log_result("error_handling", "error_request", False, 
                               f"Error testing {endpoint}: {str(e)}")
                all_passed = False
        
        return all_passed

    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*80)
        print("DASHBOARD FIXES TEST SUMMARY")
        print("="*80)
        
        total_tests = sum(len(category) for category in self.results.values())
        passed_tests = sum(
            sum(1 for test in category.values() if test["status"] == "PASS")
            for category in self.results.values()
        )
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            print(f"\n❌ CRITICAL ISSUES ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Overall assessment
        if not self.errors:
            print(f"\n✅ OVERALL STATUS: ALL TESTS PASSED")
            if self.warnings:
                print("   Some warnings noted - review recommended")
        else:
            print(f"\n❌ OVERALL STATUS: {len(self.errors)} CRITICAL ISSUES FOUND")
            print("   These must be resolved before deployment")

    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting EmailPilot Dashboard Fixes Verification")
        print(f"Testing against: {BASE_URL}")
        print(f"Test Client ID: {TEST_CLIENT_ID}")
        
        # Run all test suites
        test_results = []
        
        test_results.append(await self.test_build_system())
        test_results.append(self.test_backend_api_endpoints())
        test_results.append(self.test_static_file_serving())
        test_results.append(self.test_cors_configuration())
        test_results.append(self.check_index_html_integration())
        test_results.append(self.test_error_handling())
        
        # Generate summary
        self.generate_summary()
        
        # Save results to file
        results_file = Path("dashboard_test_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": BASE_URL,
                "results": self.results,
                "errors": self.errors,
                "warnings": self.warnings,
                "overall_status": "PASS" if not self.errors else "FAIL"
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return all(test_results)

def main():
    """Main function"""
    if len(sys.argv) > 1:
        global BASE_URL
        BASE_URL = sys.argv[1]
    
    tester = DashboardFixTester()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/admin/health", timeout=5)
        print(f"✅ Server is running at {BASE_URL}")
    except requests.ConnectionError:
        print(f"❌ Server is not running at {BASE_URL}")
        print("Please start the server with: python main_firestore.py")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(tester.run_all_tests())
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
EOF < /dev/null