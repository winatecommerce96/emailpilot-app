#!/usr/bin/env python3
"""
Test script to verify parity between unified agents API and copywriting tool
"""

import requests
import json
import sys

def test_agent_parity():
    """Test that copywriting tool shows exact parity with unified agents API"""
    
    print("🔍 Testing Agent API Parity...")
    print("-" * 50)
    
    # Fetch from unified agents API (SSOT)
    try:
        unified_response = requests.get("http://localhost:8000/api/agents/")
        unified_response.raise_for_status()
        unified_data = unified_response.json()
        unified_agents = unified_data.get("agents", [])
        print(f"✅ Unified API: Found {len(unified_agents)} agents")
    except Exception as e:
        print(f"❌ Failed to fetch from unified API: {e}")
        return False
    
    # Fetch from copywriting tool
    try:
        copywriting_response = requests.get("http://localhost:8002/api/agents")
        copywriting_response.raise_for_status()
        copywriting_data = copywriting_response.json()
        copywriting_agents = copywriting_data.get("agents", [])
        print(f"✅ Copywriting Tool: Found {len(copywriting_agents)} agents")
    except Exception as e:
        print(f"❌ Failed to fetch from copywriting tool: {e}")
        return False
    
    # Compare counts
    print("\n📊 Comparison Results:")
    print("-" * 50)
    
    if len(unified_agents) != len(copywriting_agents):
        print(f"❌ Count mismatch: Unified has {len(unified_agents)}, Copywriting has {len(copywriting_agents)}")
        success = False
    else:
        print(f"✅ Count matches: Both have {len(unified_agents)} agents")
        success = True
    
    # Compare agent IDs
    unified_ids = {agent.get("agent_id", agent.get("id")) for agent in unified_agents}
    copywriting_ids = {agent.get("id") for agent in copywriting_agents}
    
    missing_in_copywriting = unified_ids - copywriting_ids
    extra_in_copywriting = copywriting_ids - unified_ids
    
    if missing_in_copywriting:
        print(f"❌ Missing in copywriting tool: {missing_in_copywriting}")
        success = False
    
    if extra_in_copywriting:
        print(f"❌ Extra in copywriting tool (not in unified): {extra_in_copywriting}")
        success = False
    
    if not missing_in_copywriting and not extra_in_copywriting:
        print(f"✅ All agent IDs match perfectly")
    
    # Show detailed agent list from unified API
    print("\n📋 Unified Agents (SSOT):")
    print("-" * 50)
    for agent in unified_agents:
        agent_id = agent.get("agent_id", "unknown")
        name = agent.get("display_name", "Unknown")
        role = agent.get("role", "unknown")
        active = "✅" if agent.get("active", True) else "❌"
        print(f"  {active} {agent_id:30} | {name:30} | Role: {role}")
    
    # Show detailed agent list from copywriting tool
    print("\n📋 Copywriting Tool Agents:")
    print("-" * 50)
    for agent in copywriting_agents:
        agent_id = agent.get("id", "unknown")
        name = agent.get("name", "Unknown")
        role = agent.get("role", "unknown")
        print(f"  ✅ {agent_id:30} | {name:30} | Role: {role}")
    
    print("\n" + "=" * 50)
    if success:
        print("✅ PARITY TEST PASSED: Copywriting tool mirrors unified agents perfectly!")
    else:
        print("❌ PARITY TEST FAILED: Discrepancies found between endpoints")
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = test_agent_parity()
    sys.exit(0 if success else 1)