#!/usr/bin/env python3
"""
Test script to verify MCP system compatibility fixes
"""
import sys
import importlib.util
from pathlib import Path
import subprocess
import json

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing module imports...")
    
    tests = [
        ("app.core.auth", "get_current_user"),
        ("app.api.mcp", "router"),
        ("app.services.mcp_service", "get_mcp_service"),
        ("app.services.secret_manager", "get_secret_manager"),
        ("app.models.mcp_client", "MCPClient"),
        ("app.schemas.mcp_client", "MCPClientCreate"),
    ]
    
    results = []
    for module_name, item_name in tests:
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Check if the item exists
            if hasattr(module, item_name):
                print(f"  ✅ {module_name}.{item_name}")
                results.append(True)
            else:
                print(f"  ❌ {module_name}.{item_name} - item not found")
                results.append(False)
                
        except ImportError as e:
            print(f"  ❌ {module_name}.{item_name} - import error: {e}")
            results.append(False)
        except Exception as e:
            print(f"  ❌ {module_name}.{item_name} - error: {e}")
            results.append(False)
    
    return all(results)

def test_dependencies():
    """Test that required dependencies are available"""
    print("\n🔍 Testing dependencies...")
    
    required_deps = [
        "openai",
        "anthropic", 
        "google.generativeai",
        "httpx",
        "jwt",
        "fastapi",
        "google.cloud.secretmanager"
    ]
    
    results = []
    for dep in required_deps:
        try:
            importlib.import_module(dep)
            print(f"  ✅ {dep}")
            results.append(True)
        except ImportError:
            print(f"  ❌ {dep} - not installed")
            results.append(False)
    
    return all(results)

def test_database_models():
    """Test database model creation"""
    print("\n🗄️ Testing database models...")
    
    try:
        from app.core.database import engine, Base
        from app.models.mcp_client import MCPClient, MCPUsage, MCPModelConfig
        
        # Try to create tables (in memory for testing)
        from sqlalchemy import create_engine
        test_engine = create_engine("sqlite:///:memory:")
        
        Base.metadata.create_all(bind=test_engine)
        print("  ✅ Database models can be created")
        return True
    except Exception as e:
        print(f"  ❌ Database models failed: {e}")
        return False

def test_api_compatibility():
    """Test API endpoint compatibility"""
    print("\n🌐 Testing API compatibility...")
    
    try:
        # Just check that the app can be imported and routes are registered
        from main import app
        
        # Test if MCP routes are registered
        routes = [route.path for route in app.routes]
        mcp_routes = [r for r in routes if r.startswith("/api/mcp")]
        
        if mcp_routes:
            print(f"  ✅ MCP routes registered: {len(mcp_routes)} endpoints")
            print(f"    Routes: {mcp_routes}")
        else:
            print("  ❌ No MCP routes found")
            return False
        
        # Check that app starts without errors
        print("  ✅ FastAPI app initializes successfully")
        return True
    except Exception as e:
        print(f"  ❌ API compatibility test failed: {e}")
        return False

def test_mcp_service():
    """Test MCP service functionality"""
    print("\n🤖 Testing MCP service...")
    
    try:
        from app.services.mcp_service import MCPServiceManager
        
        # Create service instance
        service = MCPServiceManager()
        
        # Test model configurations
        if service.model_configs and len(service.model_configs) > 0:
            print(f"  ✅ Model configurations loaded: {list(service.model_configs.keys())}")
        else:
            print("  ❌ No model configurations found")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ MCP service test failed: {e}")
        return False

def test_auth_system():
    """Test authentication system"""
    print("\n🔐 Testing authentication system...")
    
    try:
        from app.core.auth import create_access_token, verify_token, DEMO_USERS
        
        # Test token creation
        token = create_access_token({"sub": "admin"})
        if token:
            print("  ✅ Token creation working")
        else:
            print("  ❌ Token creation failed")
            return False
        
        # Test token verification
        payload = verify_token(token)
        if payload.get("sub") == "admin":
            print("  ✅ Token verification working")
        else:
            print("  ❌ Token verification failed")
            return False
        
        # Test demo users
        if "admin" in DEMO_USERS:
            print("  ✅ Demo users configured")
        else:
            print("  ❌ Demo users missing")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Auth system test failed: {e}")
        return False

def main():
    """Run all compatibility tests"""
    print("🔍 MCP System Compatibility Test")
    print("=" * 40)
    
    tests = [
        ("Module Imports", test_imports),
        ("Dependencies", test_dependencies), 
        ("Database Models", test_database_models),
        ("API Compatibility", test_api_compatibility),
        ("MCP Service", test_mcp_service),
        ("Authentication", test_auth_system),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  💥 {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All compatibility tests passed! MCP system is ready to deploy.")
        return 0
    else:
        print(f"⚠️ {total-passed} tests failed. Please fix issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())