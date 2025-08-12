#!/usr/bin/env python3

"""
EmailPilot Health Check System
Comprehensive health monitoring and verification for deployed services
Version: 1.0.0
"""

import asyncio
import aiohttp
import json
import argparse
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, base_url: str = "https://emailpilot.ai", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = None
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'EmailPilot-HealthChecker/1.0'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def check_endpoint(self, endpoint: str, method: str = "GET", 
                           expected_status: int = 200, 
                           headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Check a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, headers=headers) as response:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Read response content
                content = await response.text()
                
                # Try to parse JSON if possible
                try:
                    json_data = json.loads(content)
                except json.JSONDecodeError:
                    json_data = None
                
                result = {
                    "url": url,
                    "method": method,
                    "status_code": response.status,
                    "expected_status": expected_status,
                    "success": response.status == expected_status,
                    "response_time_ms": round(response_time, 2),
                    "content_length": len(content),
                    "content_type": response.headers.get('content-type', ''),
                    "json_data": json_data,
                    "error": None
                }
                
                logger.info(f"✓ {method} {endpoint} - {response.status} ({response_time:.0f}ms)")
                return result
                
        except asyncio.TimeoutError:
            result = {
                "url": url,
                "method": method,
                "status_code": None,
                "expected_status": expected_status,
                "success": False,
                "response_time_ms": self.timeout * 1000,
                "error": "Request timeout"
            }
            logger.error(f"✗ {method} {endpoint} - TIMEOUT")
            return result
            
        except Exception as e:
            result = {
                "url": url,
                "method": method,
                "status_code": None,
                "expected_status": expected_status,
                "success": False,
                "response_time_ms": None,
                "error": str(e)
            }
            logger.error(f"✗ {method} {endpoint} - ERROR: {e}")
            return result
            
    async def check_basic_health(self) -> Dict[str, Any]:
        """Check basic application health"""
        logger.info("Checking basic application health...")
        
        checks = [
            {"endpoint": "/", "name": "Root endpoint"},
            {"endpoint": "/health", "name": "Health endpoint"},
            {"endpoint": "/app", "name": "Frontend app"}
        ]
        
        results = []
        for check in checks:
            result = await self.check_endpoint(check["endpoint"])
            result["name"] = check["name"]
            results.append(result)
            
        return {
            "category": "basic_health",
            "timestamp": datetime.now().isoformat(),
            "checks": results,
            "success": all(r["success"] for r in results)
        }
        
    async def check_api_endpoints(self, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Check API endpoints"""
        logger.info("Checking API endpoints...")
        
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            
        # Public endpoints (no auth required)
        public_checks = [
            {"endpoint": "/api/auth/login", "method": "POST", "expected": 422},  # No body, validation error expected
            {"endpoint": "/api/reports", "method": "GET", "expected": 401},  # Auth required
        ]
        
        # Protected endpoints (require auth)
        protected_checks = []
        if auth_token:
            protected_checks = [
                {"endpoint": "/api/clients", "name": "Clients API"},
                {"endpoint": "/api/goals", "name": "Goals API"},
                {"endpoint": "/api/mcp/clients", "name": "MCP Clients API"},
                {"endpoint": "/api/admin/users", "name": "Admin Users API"},
            ]
        
        results = []
        
        # Check public endpoints
        for check in public_checks:
            result = await self.check_endpoint(
                check["endpoint"], 
                check["method"], 
                check["expected"]
            )
            result["name"] = f"Public API: {check['endpoint']}"
            results.append(result)
            
        # Check protected endpoints if auth token provided
        for check in protected_checks:
            result = await self.check_endpoint(check["endpoint"], headers=headers)
            result["name"] = check["name"]
            results.append(result)
            
        return {
            "category": "api_endpoints",
            "timestamp": datetime.now().isoformat(),
            "checks": results,
            "success": all(r["success"] for r in results),
            "authenticated": bool(auth_token)
        }
        
    async def check_frontend_assets(self) -> Dict[str, Any]:
        """Check frontend static assets"""
        logger.info("Checking frontend assets...")
        
        assets = [
            {"endpoint": "/static/app.js", "name": "Main app JavaScript"},
            {"endpoint": "/static/index.html", "name": "Main HTML file"},
            {"endpoint": "/static/components/MCPManagement.js", "name": "MCP Management component"},
            {"endpoint": "/static/logo.png", "name": "Logo image"},
        ]
        
        results = []
        for asset in assets:
            result = await self.check_endpoint(asset["endpoint"])
            result["name"] = asset["name"]
            results.append(result)
            
        return {
            "category": "frontend_assets",
            "timestamp": datetime.now().isoformat(),
            "checks": results,
            "success": all(r["success"] for r in results)
        }
        
    async def check_mcp_integration(self, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Check MCP-specific functionality"""
        logger.info("Checking MCP integration...")
        
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            
        checks = [
            {"endpoint": "/api/mcp/clients", "name": "MCP Clients endpoint"},
            {"endpoint": "/api/mcp/models", "name": "MCP Models endpoint"},
            {"endpoint": "/api/mcp-firestore/sync", "name": "MCP Firestore sync"},
        ]
        
        results = []
        for check in checks:
            # Most MCP endpoints require auth, expect 401 if no token
            expected_status = 200 if auth_token else 401
            result = await self.check_endpoint(
                check["endpoint"], 
                expected_status=expected_status,
                headers=headers
            )
            result["name"] = check["name"]
            results.append(result)
            
        return {
            "category": "mcp_integration",
            "timestamp": datetime.now().isoformat(),
            "checks": results,
            "success": all(r["success"] for r in results),
            "requires_auth": not bool(auth_token)
        }
        
    async def check_performance(self) -> Dict[str, Any]:
        """Check application performance metrics"""
        logger.info("Checking performance metrics...")
        
        # Run multiple requests to get average response times
        performance_checks = []
        
        for i in range(5):  # 5 samples
            result = await self.check_endpoint("/health")
            if result["response_time_ms"]:
                performance_checks.append(result["response_time_ms"])
                
        if performance_checks:
            avg_response_time = sum(performance_checks) / len(performance_checks)
            max_response_time = max(performance_checks)
            min_response_time = min(performance_checks)
        else:
            avg_response_time = max_response_time = min_response_time = None
            
        return {
            "category": "performance",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "average_response_time_ms": round(avg_response_time, 2) if avg_response_time else None,
                "max_response_time_ms": max_response_time,
                "min_response_time_ms": min_response_time,
                "samples": len(performance_checks)
            },
            "success": avg_response_time < 1000 if avg_response_time else False  # Under 1 second
        }
        
    async def run_comprehensive_check(self, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Run all health checks"""
        logger.info("Starting comprehensive health check...")
        start_time = datetime.now()
        
        # Run all checks concurrently
        results = await asyncio.gather(
            self.check_basic_health(),
            self.check_api_endpoints(auth_token),
            self.check_frontend_assets(),
            self.check_mcp_integration(auth_token),
            self.check_performance(),
            return_exceptions=True
        )
        
        # Process results
        health_report = {
            "timestamp": start_time.isoformat(),
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "base_url": self.base_url,
            "overall_success": True,
            "categories": {}
        }
        
        category_names = [
            "basic_health", "api_endpoints", "frontend_assets", 
            "mcp_integration", "performance"
        ]
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Health check category failed: {result}")
                health_report["overall_success"] = False
                health_report["categories"][category_names[i]] = {
                    "success": False,
                    "error": str(result)
                }
            else:
                category_name = result["category"]
                health_report["categories"][category_name] = result
                if not result["success"]:
                    health_report["overall_success"] = False
                    
        # Generate summary
        total_checks = sum(
            len(cat.get("checks", [])) 
            for cat in health_report["categories"].values() 
            if "checks" in cat
        )
        
        successful_checks = sum(
            len([c for c in cat.get("checks", []) if c.get("success", False)])
            for cat in health_report["categories"].values() 
            if "checks" in cat
        )
        
        health_report["summary"] = {
            "total_categories": len(health_report["categories"]),
            "successful_categories": len([
                cat for cat in health_report["categories"].values() 
                if cat.get("success", False)
            ]),
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "success_rate": (successful_checks / total_checks * 100) if total_checks > 0 else 0
        }
        
        end_time = datetime.now()
        logger.info(f"Health check completed in {(end_time - start_time).total_seconds():.2f}s")
        logger.info(f"Overall success: {health_report['overall_success']}")
        logger.info(f"Success rate: {health_report['summary']['success_rate']:.1f}%")
        
        return health_report
        
    async def monitor_health(self, interval_seconds: int = 60, 
                           duration_minutes: Optional[int] = None,
                           auth_token: Optional[str] = None):
        """Monitor health over time"""
        logger.info(f"Starting health monitoring (interval: {interval_seconds}s)")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes) if duration_minutes else None
        
        monitoring_results = []
        
        try:
            while True:
                # Check if we should stop monitoring
                if end_time and datetime.now() > end_time:
                    break
                    
                # Run health check
                result = await self.run_comprehensive_check(auth_token)
                monitoring_results.append(result)
                
                # Print summary
                print(f"[{result['timestamp']}] "
                      f"Health: {'✓' if result['overall_success'] else '✗'} "
                      f"Success Rate: {result['summary']['success_rate']:.1f}%")
                
                # Wait for next check
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            
        return monitoring_results


async def main():
    parser = argparse.ArgumentParser(description="EmailPilot Health Check System")
    parser.add_argument("--base-url", default="https://emailpilot.ai", 
                       help="Base URL to check")
    parser.add_argument("--timeout", type=int, default=30, 
                       help="Request timeout in seconds")
    parser.add_argument("--auth-token", help="Authentication token for protected endpoints")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--monitor", action="store_true", 
                       help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=60, 
                       help="Monitoring interval in seconds")
    parser.add_argument("--duration", type=int, 
                       help="Monitoring duration in minutes")
    parser.add_argument("--category", 
                       choices=["basic", "api", "frontend", "mcp", "performance", "all"],
                       default="all", help="Specific category to check")
    
    args = parser.parse_args()
    
    async with HealthChecker(args.base_url, args.timeout) as checker:
        if args.monitor:
            results = await checker.monitor_health(
                args.interval, args.duration, args.auth_token
            )
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Monitoring results saved to {args.output}")
        else:
            # Single health check
            if args.category == "all":
                result = await checker.run_comprehensive_check(args.auth_token)
            else:
                # Run specific category
                if args.category == "basic":
                    result = await checker.check_basic_health()
                elif args.category == "api":
                    result = await checker.check_api_endpoints(args.auth_token)
                elif args.category == "frontend":
                    result = await checker.check_frontend_assets()
                elif args.category == "mcp":
                    result = await checker.check_mcp_integration(args.auth_token)
                elif args.category == "performance":
                    result = await checker.check_performance()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"Results saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())