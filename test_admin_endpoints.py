#!/usr/bin/env python3
"""
Test script for admin endpoints
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_admin_endpoints():
    """Test the admin endpoints"""
    base_url = "http://localhost:8080"
    
    print(f"🧪 Testing Admin Endpoints at {base_url}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        {
            "name": "Admin Health Check",
            "method": "GET",
            "url": f"{base_url}/api/admin/health",
            "expected_keys": ["status", "service", "endpoints_available"]
        },
        {
            "name": "System Status",
            "method": "GET", 
            "url": f"{base_url}/api/admin/system/status",
            "expected_keys": ["status", "components", "environment"]
        },
        {
            "name": "Environment Variables",
            "method": "GET",
            "url": f"{base_url}/api/admin/environment", 
            "expected_keys": ["variables"]
        },
        {
            "name": "Slack Test (will fail without webhook)",
            "method": "POST",
            "url": f"{base_url}/api/admin/slack/test",
            "expected_status": [200, 400, 500],  # May fail if no webhook configured
            "optional": True
        }
    ]
    
    results = []
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing: {endpoint['name']}")
        print(f"   {endpoint['method']} {endpoint['url']}")
        
        try:
            if endpoint['method'] == 'GET':
                response = requests.get(endpoint['url'], timeout=10)
            elif endpoint['method'] == 'POST':
                response = requests.post(endpoint['url'], json={}, timeout=10)
            
            # Check status code
            expected_status = endpoint.get('expected_status', [200])
            if response.status_code in expected_status:
                print(f"   ✅ Status: {response.status_code}")
                
                try:
                    data = response.json()
                    
                    # Check expected keys if provided
                    if 'expected_keys' in endpoint:
                        missing_keys = [key for key in endpoint['expected_keys'] if key not in data]
                        if missing_keys:
                            print(f"   ⚠️  Missing keys: {missing_keys}")
                        else:
                            print(f"   ✅ All expected keys present")
                    
                    # Print some sample data
                    if 'status' in data:
                        print(f"   📊 Status: {data['status']}")
                    
                    if 'service' in data:
                        print(f"   🏷️  Service: {data['service']}")
                        
                    if endpoint['name'] == "Environment Variables" and 'variables' in data:
                        var_count = len(data['variables'])
                        print(f"   📝 Environment variables found: {var_count}")
                        
                        # Show first few variables (without values for security)
                        for i, (key, config) in enumerate(list(data['variables'].items())[:3]):
                            status = "✅ Set" if config.get('is_set') else "❌ Not set"
                            sensitive = "🔒 Sensitive" if config.get('is_sensitive') else "🔓 Public"
                            print(f"      - {key}: {status} {sensitive}")
                        
                        if var_count > 3:
                            print(f"      ... and {var_count - 3} more")
                    
                    results.append({
                        'endpoint': endpoint['name'],
                        'status': 'SUCCESS',
                        'status_code': response.status_code,
                        'response_keys': list(data.keys()) if isinstance(data, dict) else []
                    })
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️  Response is not valid JSON")
                    print(f"   📄 Response: {response.text[:100]}...")
                    results.append({
                        'endpoint': endpoint['name'],
                        'status': 'SUCCESS_NO_JSON',
                        'status_code': response.status_code
                    })
            else:
                print(f"   ❌ Status: {response.status_code} (expected {expected_status})")
                print(f"   📄 Error: {response.text[:200]}...")
                
                if not endpoint.get('optional', False):
                    results.append({
                        'endpoint': endpoint['name'],
                        'status': 'FAILED',
                        'status_code': response.status_code,
                        'error': response.text[:100]
                    })
                else:
                    print(f"   ℹ️  This endpoint is optional and may fail in some configurations")
                    results.append({
                        'endpoint': endpoint['name'],
                        'status': 'OPTIONAL_FAILED',
                        'status_code': response.status_code
                    })
        
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - is the server running?")
            results.append({
                'endpoint': endpoint['name'],
                'status': 'CONNECTION_ERROR'
            })
        except requests.exceptions.Timeout:
            print(f"   ❌ Request timed out")
            results.append({
                'endpoint': endpoint['name'],
                'status': 'TIMEOUT'
            })
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            results.append({
                'endpoint': endpoint['name'],
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    success_count = len([r for r in results if r['status'] == 'SUCCESS'])
    total_required = len([e for e in endpoints if not e.get('optional', False)])
    
    print(f"✅ Successful endpoints: {success_count}")
    print(f"📝 Total required endpoints: {total_required}")
    print(f"📊 Success rate: {success_count/total_required*100:.1f}%" if total_required > 0 else "N/A")
    
    # Detailed results
    for result in results:
        status_icon = {
            'SUCCESS': '✅',
            'SUCCESS_NO_JSON': '⚠️',
            'FAILED': '❌',
            'CONNECTION_ERROR': '🔌',
            'TIMEOUT': '⏰',
            'ERROR': '💥',
            'OPTIONAL_FAILED': 'ℹ️'
        }.get(result['status'], '❓')
        
        print(f"{status_icon} {result['endpoint']}: {result['status']}")
    
    if success_count == total_required:
        print(f"\n🎉 All required admin endpoints are working correctly!")
        return True
    else:
        print(f"\n⚠️  Some endpoints may need attention.")
        return False

if __name__ == "__main__":
    print("📱 EmailPilot Admin Endpoint Tester")
    print("=" * 50)
    
    # Check if server should be started
    import subprocess
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        print("✅ Server is already running")
    except:
        print("❌ Server is not running")
        print("ℹ️  To start the server, run: python main.py")
        print("ℹ️  Or: uvicorn main:app --reload --host 0.0.0.0 --port 8080")
        sys.exit(1)
    
    success = test_admin_endpoints()
    sys.exit(0 if success else 1)