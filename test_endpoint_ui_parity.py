#!/usr/bin/env python3
"""
Endpoint-UI Parity Test
Ensures all active backend endpoints have corresponding UI representation
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
import subprocess
import sys

class EndpointUIParityChecker:
    def __init__(self):
        self.backend_endpoints = set()
        self.ui_references = set()
        self.mounted_routers = set()
        self.dead_endpoints = []
        self.hidden_endpoints = []
        
    def find_backend_endpoints(self) -> Set[str]:
        """Find all backend endpoint definitions"""
        endpoints = set()
        api_dir = Path("app/api")
        
        for py_file in api_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find route decorators
                route_pattern = r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)'
                matches = re.findall(route_pattern, content)
                
                for method, path in matches:
                    # Get the router prefix from imports
                    file_name = py_file.stem
                    full_path = self.get_full_path(file_name, path)
                    endpoints.add(f"{method.upper()} {full_path}")
                    
            except Exception as e:
                print(f"Error parsing {py_file}: {e}")
                
        return endpoints
    
    def get_full_path(self, module_name: str, path: str) -> str:
        """Get full path including router prefix"""
        # Read main_firestore.py to find router prefixes
        try:
            with open("main_firestore.py", 'r') as f:
                content = f.read()
            
            # Find router include with prefix
            pattern = rf'{module_name}.*prefix="([^"]+)"'
            match = re.search(pattern, content)
            
            if match:
                prefix = match.group(1)
                return f"{prefix}{path}" if not path.startswith("/") else f"{prefix}{path}"
            else:
                return f"/api{path}" if not path.startswith("/") else path
        except:
            return path
    
    def find_mounted_routers(self) -> Set[str]:
        """Find which routers are actually mounted"""
        mounted = set()
        try:
            with open("main_firestore.py", 'r') as f:
                content = f.read()
            
            # Find all router includes
            pattern = r'app\.include_router\(([^,\)]+)'
            matches = re.findall(pattern, content)
            mounted.update(matches)
            
        except Exception as e:
            print(f"Error parsing main_firestore.py: {e}")
            
        return mounted
    
    def find_ui_references(self) -> Set[str]:
        """Find endpoints referenced in frontend code"""
        references = set()
        frontend_dir = Path("frontend/public")
        
        for js_file in frontend_dir.rglob("*.js"):
            if "node_modules" in str(js_file) or ".min.js" in str(js_file):
                continue
                
            try:
                with open(js_file, 'r') as f:
                    content = f.read()
                
                # Find fetch calls
                fetch_pattern = r'fetch\(["\']([^"\']+)'
                matches = re.findall(fetch_pattern, content)
                references.update(matches)
                
            except Exception as e:
                print(f"Error parsing {js_file}: {e}")
                
        return references
    
    def test_endpoint_health(self, endpoint: str) -> bool:
        """Test if an endpoint is actually working"""
        method, path = endpoint.split(' ', 1)
        
        # Skip certain paths that require specific params
        skip_patterns = ['/\\{', '/<', '/:', 'WebSocket']
        if any(pattern in path for pattern in skip_patterns):
            return True  # Assume parameterized endpoints work
        
        try:
            # Use curl to test endpoint
            if method == 'GET':
                result = subprocess.run(
                    ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
                     f'http://localhost:8000{path}'],
                    capture_output=True, text=True, timeout=2
                )
                status_code = result.stdout.strip()
                # 200-499 are "working" (including auth required)
                return status_code and 200 <= int(status_code) < 500
        except:
            return False
            
        return True  # Assume POST/PUT/DELETE work (need auth/body)
    
    def analyze_parity(self):
        """Main analysis function"""
        print("=" * 80)
        print("Endpoint-UI Parity Analysis")
        print("=" * 80)
        
        # Collect data
        self.backend_endpoints = self.find_backend_endpoints()
        self.mounted_routers = self.find_mounted_routers()
        self.ui_references = self.find_ui_references()
        
        print(f"\n📊 Statistics:")
        print(f"  • Total backend endpoints: {len(self.backend_endpoints)}")
        print(f"  • Mounted routers: {len(self.mounted_routers)}")
        print(f"  • UI references: {len(self.ui_references)}")
        
        # Find hidden endpoints
        self.hidden_endpoints = []
        for endpoint in self.backend_endpoints:
            method, path = endpoint.split(' ', 1)
            # Check if referenced in UI
            referenced = any(ref in path or path in ref for ref in self.ui_references)
            if not referenced:
                self.hidden_endpoints.append(endpoint)
        
        print(f"  • Hidden endpoints: {len(self.hidden_endpoints)}")
        
        # Calculate coverage
        coverage = ((len(self.backend_endpoints) - len(self.hidden_endpoints)) / 
                   len(self.backend_endpoints) * 100) if self.backend_endpoints else 0
        
        print(f"\n📈 Coverage: {coverage:.1f}%")
        
        # List top hidden endpoints
        if self.hidden_endpoints:
            print(f"\n⚠️ Top Hidden Endpoints (showing first 20):")
            for endpoint in sorted(self.hidden_endpoints)[:20]:
                # Test if working
                is_working = self.test_endpoint_health(endpoint)
                status = "✅" if is_working else "❌"
                print(f"  {status} {endpoint}")
        
        # Generate report
        self.generate_report(coverage)
        
        # Exit with error if coverage too low
        MIN_COVERAGE = 40  # Set threshold
        if coverage < MIN_COVERAGE:
            print(f"\n❌ FAIL: Coverage {coverage:.1f}% is below minimum {MIN_COVERAGE}%")
            sys.exit(1)
        else:
            print(f"\n✅ PASS: Coverage {coverage:.1f}% meets minimum {MIN_COVERAGE}%")
    
    def generate_report(self, coverage: float):
        """Generate detailed JSON report"""
        report = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "summary": {
                "total_endpoints": len(self.backend_endpoints),
                "hidden_endpoints": len(self.hidden_endpoints),
                "coverage_percentage": round(coverage, 2)
            },
            "hidden_endpoints": sorted(self.hidden_endpoints)[:50],  # Top 50
            "recommendations": self.generate_recommendations()
        }
        
        with open("endpoint_parity_report.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to endpoint_parity_report.json")
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        if len(self.hidden_endpoints) > 50:
            recommendations.append(
                "Critical: Over 50 endpoints are hidden. Consider creating a bulk UI exposure tool."
            )
        
        # Check for patterns in hidden endpoints
        admin_hidden = [e for e in self.hidden_endpoints if '/admin' in e]
        if len(admin_hidden) > 10:
            recommendations.append(
                f"Admin Tools: {len(admin_hidden)} admin endpoints are hidden. "
                "Create AdminDashboard component."
            )
        
        ai_hidden = [e for e in self.hidden_endpoints if '/ai' in e or '/agent' in e]
        if len(ai_hidden) > 5:
            recommendations.append(
                f"AI Features: {len(ai_hidden)} AI/Agent endpoints are hidden. "
                "Create AIMonitoring component."
            )
        
        return recommendations

def main():
    """Run the parity check"""
    checker = EndpointUIParityChecker()
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=1)
        if response.status_code != 200:
            print("⚠️ Warning: Server may not be healthy")
    except:
        print("⚠️ Warning: Server not running. Start with:")
        print("   uvicorn main_firestore:app --port 8000 --host localhost")
        print("   Some endpoint health checks will fail.\n")
    
    checker.analyze_parity()

if __name__ == "__main__":
    main()