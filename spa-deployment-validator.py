#!/usr/bin/env python3
"""
SPA Deployment Validator for EmailPilot
Validates that Single Page Application is correctly deployed and configured
"""

import requests
import json
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class TestStatus(Enum):
    """Test result status"""
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    WARNING = "⚠️ WARNING"
    SKIPPED = "⏭️ SKIPPED"

@dataclass
class SPAValidationTest:
    """Individual SPA validation test"""
    name: str
    description: str
    path: str
    expected_behavior: str
    critical: bool = True

class SPADeploymentValidator:
    """
    Validates SPA deployment for EmailPilot
    Ensures client-side routing, static assets, and API proxying work correctly
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results = []
        self.passed_count = 0
        self.failed_count = 0
        self.warning_count = 0
        
    def run_all_tests(self) -> Dict[str, any]:
        """Run complete SPA validation suite"""
        print("🧪 EmailPilot SPA Deployment Validation")
        print("=" * 50)
        print(f"Target: {self.base_url}")
        print("")
        
        # Test suites
        self.test_spa_routing()
        self.test_static_assets()
        self.test_api_proxy()
        self.test_deep_linking()
        self.test_error_handling()
        self.test_performance()
        self.test_security_headers()
        
        # Generate report
        return self.generate_report()
    
    def test_spa_routing(self) -> None:
        """Test client-side routing functionality"""
        print("📍 Testing SPA Routing...")
        
        spa_routes = [
            SPAValidationTest(
                name="Root Route",
                description="Test root path serves index.html",
                path="/",
                expected_behavior="Should return 200 with index.html content"
            ),
            SPAValidationTest(
                name="Dashboard Route",
                description="Test client-side route",
                path="/dashboard",
                expected_behavior="Should return 200 with index.html (not 404)"
            ),
            SPAValidationTest(
                name="Nested Route",
                description="Test deep nested route",
                path="/settings/profile/edit",
                expected_behavior="Should return 200 with index.html for React Router"
            ),
            SPAValidationTest(
                name="Non-existent Route",
                description="Test 404 handling",
                path="/this-route-does-not-exist-12345",
                expected_behavior="Should return 200 with index.html (SPA handles 404)"
            ),
            SPAValidationTest(
                name="Route with Parameters",
                description="Test parameterized route",
                path="/campaigns/abc-123-def",
                expected_behavior="Should return 200 with index.html"
            )
        ]
        
        for test in spa_routes:
            self._run_routing_test(test)
    
    def test_static_assets(self) -> None:
        """Test static asset serving"""
        print("\n📦 Testing Static Assets...")
        
        asset_tests = [
            SPAValidationTest(
                name="JavaScript Bundle",
                description="Test JS bundle loading",
                path="/static/js/main.js",
                expected_behavior="Should return 200 with JS content and cache headers",
                critical=True
            ),
            SPAValidationTest(
                name="CSS Styles",
                description="Test CSS loading",
                path="/static/css/main.css",
                expected_behavior="Should return 200 with CSS content and cache headers",
                critical=True
            ),
            SPAValidationTest(
                name="Favicon",
                description="Test favicon loading",
                path="/favicon.ico",
                expected_behavior="Should return 200 with icon file",
                critical=False
            ),
            SPAValidationTest(
                name="Manifest",
                description="Test PWA manifest",
                path="/manifest.json",
                expected_behavior="Should return 200 with manifest JSON",
                critical=False
            )
        ]
        
        for test in asset_tests:
            self._run_asset_test(test)
    
    def test_api_proxy(self) -> None:
        """Test API proxy configuration"""
        print("\n🔌 Testing API Proxy...")
        
        api_tests = [
            SPAValidationTest(
                name="Health Endpoint",
                description="Test API health check",
                path="/api/health",
                expected_behavior="Should return 200 or 401 (API response)"
            ),
            SPAValidationTest(
                name="API Root",
                description="Test API root path",
                path="/api/",
                expected_behavior="Should proxy to backend API"
            ),
            SPAValidationTest(
                name="API Nested Route",
                description="Test nested API route",
                path="/api/v1/clients",
                expected_behavior="Should proxy to backend API"
            )
        ]
        
        for test in api_tests:
            self._run_api_test(test)
    
    def test_deep_linking(self) -> None:
        """Test deep linking functionality"""
        print("\n🔗 Testing Deep Linking...")
        
        # Test that direct navigation to deep routes works
        deep_links = [
            "/campaigns/edit/12345",
            "/settings/integrations/klaviyo",
            "/reports/revenue/2024"
        ]
        
        for link in deep_links:
            test = SPAValidationTest(
                name=f"Deep Link: {link}",
                description="Test direct navigation to deep route",
                path=link,
                expected_behavior="Should load index.html and let React Router handle"
            )
            self._run_routing_test(test)
    
    def test_error_handling(self) -> None:
        """Test error handling and recovery"""
        print("\n⚠️ Testing Error Handling...")
        
        error_tests = [
            SPAValidationTest(
                name="404 API Route",
                description="Test non-existent API route",
                path="/api/non-existent-endpoint",
                expected_behavior="Should return 404 from API",
                critical=False
            ),
            SPAValidationTest(
                name="Malformed Path",
                description="Test malformed URL path",
                path="//double//slashes///path",
                expected_behavior="Should normalize and handle correctly",
                critical=False
            )
        ]
        
        for test in error_tests:
            self._run_error_test(test)
    
    def test_performance(self) -> None:
        """Test performance characteristics"""
        print("\n⚡ Testing Performance...")
        
        # Test response times
        perf_test = SPAValidationTest(
            name="Initial Load Time",
            description="Test root page load time",
            path="/",
            expected_behavior="Should load in < 3 seconds"
        )
        
        import time
        start = time.time()
        response = self._make_request(perf_test.path)
        load_time = time.time() - start
        
        if load_time < 1:
            self._record_result(perf_test, TestStatus.PASSED, f"Loaded in {load_time:.2f}s")
        elif load_time < 3:
            self._record_result(perf_test, TestStatus.WARNING, f"Loaded in {load_time:.2f}s (slow)")
        else:
            self._record_result(perf_test, TestStatus.FAILED, f"Loaded in {load_time:.2f}s (too slow)")
    
    def test_security_headers(self) -> None:
        """Test security headers for SPA"""
        print("\n🔒 Testing Security Headers...")
        
        response = self._make_request("/")
        if response:
            headers = response.headers
            
            security_headers = {
                "X-Frame-Options": "SAMEORIGIN",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block"
            }
            
            for header, expected in security_headers.items():
                test = SPAValidationTest(
                    name=f"Security Header: {header}",
                    description=f"Check {header} header",
                    path="/",
                    expected_behavior=f"Should have {header}: {expected}",
                    critical=False
                )
                
                if header in headers:
                    if expected in headers[header]:
                        self._record_result(test, TestStatus.PASSED, f"Header present: {headers[header]}")
                    else:
                        self._record_result(test, TestStatus.WARNING, f"Header value mismatch: {headers[header]}")
                else:
                    self._record_result(test, TestStatus.WARNING, "Header missing")
    
    def _run_routing_test(self, test: SPAValidationTest) -> None:
        """Run a routing test"""
        response = self._make_request(test.path)
        
        if response and response.status_code == 200:
            # Check if response contains index.html markers
            content = response.text[:1000]  # Check first 1000 chars
            if "<html" in content.lower() and ("react" in content.lower() or "root" in content):
                self._record_result(test, TestStatus.PASSED, "Returns index.html for SPA routing")
            else:
                self._record_result(test, TestStatus.WARNING, "Returns 200 but content unclear")
        elif response and response.status_code == 404:
            self._record_result(test, TestStatus.FAILED, "Returns 404 - SPA routing not configured")
        else:
            self._record_result(test, TestStatus.FAILED, f"Unexpected response: {response.status_code if response else 'No response'}")
    
    def _run_asset_test(self, test: SPAValidationTest) -> None:
        """Run a static asset test"""
        response = self._make_request(test.path)
        
        if response and response.status_code == 200:
            # Check cache headers
            cache_control = response.headers.get('Cache-Control', '')
            if 'max-age' in cache_control or 'immutable' in cache_control:
                self._record_result(test, TestStatus.PASSED, "Asset served with caching")
            else:
                self._record_result(test, TestStatus.WARNING, "Asset served but no cache headers")
        elif response and response.status_code == 404:
            if test.critical:
                self._record_result(test, TestStatus.FAILED, "Critical asset not found")
            else:
                self._record_result(test, TestStatus.WARNING, "Optional asset not found")
        else:
            self._record_result(test, TestStatus.FAILED, f"Unexpected response: {response.status_code if response else 'No response'}")
    
    def _run_api_test(self, test: SPAValidationTest) -> None:
        """Run an API proxy test"""
        response = self._make_request(test.path)
        
        if response:
            if response.status_code in [200, 401, 403]:
                # These are valid API responses
                self._record_result(test, TestStatus.PASSED, f"API proxy working (HTTP {response.status_code})")
            elif response.status_code == 404:
                # Could be valid if endpoint doesn't exist
                self._record_result(test, TestStatus.WARNING, "API returned 404")
            else:
                self._record_result(test, TestStatus.FAILED, f"Unexpected API response: {response.status_code}")
        else:
            self._record_result(test, TestStatus.FAILED, "No response from API")
    
    def _run_error_test(self, test: SPAValidationTest) -> None:
        """Run an error handling test"""
        response = self._make_request(test.path)
        
        if response:
            self._record_result(test, TestStatus.PASSED, f"Handled with HTTP {response.status_code}")
        else:
            self._record_result(test, TestStatus.FAILED, "Failed to handle error gracefully")
    
    def _make_request(self, path: str) -> Optional[requests.Response]:
        """Make HTTP request to the SPA"""
        try:
            url = f"{self.base_url}{path}"
            response = requests.get(url, timeout=10, allow_redirects=True)
            return response
        except requests.RequestException as e:
            print(f"  ❌ Request failed: {e}")
            return None
    
    def _record_result(self, test: SPAValidationTest, status: TestStatus, details: str) -> None:
        """Record test result"""
        result = {
            "test": test.name,
            "description": test.description,
            "path": test.path,
            "status": status,
            "details": details,
            "critical": test.critical
        }
        
        self.results.append(result)
        
        # Update counters
        if status == TestStatus.PASSED:
            self.passed_count += 1
            print(f"  {status.value} {test.name}: {details}")
        elif status == TestStatus.FAILED:
            self.failed_count += 1
            print(f"  {status.value} {test.name}: {details}")
        elif status == TestStatus.WARNING:
            self.warning_count += 1
            print(f"  {status.value} {test.name}: {details}")
    
    def generate_report(self) -> Dict[str, any]:
        """Generate validation report"""
        print("\n" + "=" * 50)
        print("📊 VALIDATION REPORT")
        print("=" * 50)
        
        total_tests = len(self.results)
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {self.passed_count}")
        print(f"❌ Failed: {self.failed_count}")
        print(f"⚠️ Warnings: {self.warning_count}")
        
        # Check critical failures
        critical_failures = [r for r in self.results if r["critical"] and r["status"] == TestStatus.FAILED]
        
        if critical_failures:
            print("\n🚨 CRITICAL FAILURES:")
            for failure in critical_failures:
                print(f"  - {failure['test']}: {failure['details']}")
            print("\n❌ SPA DEPLOYMENT VALIDATION FAILED")
            validation_passed = False
        elif self.failed_count > 0:
            print("\n⚠️ Non-critical failures detected")
            print("✅ SPA DEPLOYMENT VALIDATION PASSED WITH WARNINGS")
            validation_passed = True
        else:
            print("\n✅ SPA DEPLOYMENT VALIDATION PASSED")
            validation_passed = True
        
        return {
            "passed": validation_passed,
            "url": self.base_url,
            "total_tests": total_tests,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "warning_count": self.warning_count,
            "critical_failures": len(critical_failures),
            "results": self.results
        }

def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python spa-deployment-validator.py <base_url>")
        print("Example: python spa-deployment-validator.py https://emailpilot-api-935786836546.us-central1.run.app")
        sys.exit(1)
    
    base_url = sys.argv[1]
    validator = SPADeploymentValidator(base_url)
    report = validator.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if report["passed"] else 1)

if __name__ == "__main__":
    main()