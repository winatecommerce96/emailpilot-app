#!/usr/bin/env python3
"""
Test Human Gate Visibility APIs
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_human_gate_apis():
    """Test the human gate visibility APIs"""
    
    print("=" * 60)
    print("TESTING HUMAN GATE VISIBILITY APIs")
    print("=" * 60)
    
    # 1. Run a workflow
    print("\n1. Starting workflow...")
    response = requests.post(
        f"{API_BASE}/api/workflow/schemas/default/run",
        json={"brand": "TestBrand", "month": "2025-06"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to start workflow: {response.status_code}")
        return
    
    run_data = response.json()
    run_id = run_data["run_id"]
    print(f"✅ Workflow started: {run_id}")
    
    # 2. List runs
    print("\n2. Listing runs...")
    response = requests.get(f"{API_BASE}/api/workflow/runs")
    
    if response.status_code == 200:
        runs = response.json()
        print(f"✅ Found {len(runs)} run(s)")
        for run in runs:
            print(f"   - {run['run_id']}: {run['status']}")
    else:
        print(f"❌ Failed to list runs: {response.status_code}")
    
    # 3. Get run status
    print(f"\n3. Getting status for {run_id}...")
    response = requests.get(f"{API_BASE}/api/workflow/runs/{run_id}")
    
    if response.status_code == 200:
        status = response.json()
        print(f"✅ Run status: {status['status']}")
        print(f"   Current node: {status.get('current_node', 'unknown')}")
    else:
        print(f"❌ Failed to get status: {response.status_code}")
    
    # 4. Simulate human gate
    print(f"\n4. Simulating human gate for {run_id}...")
    response = requests.post(f"{API_BASE}/api/workflow/runs/{run_id}/simulate-human-gate")
    
    if response.status_code == 200:
        print(f"✅ Human gate simulation activated")
    else:
        print(f"❌ Failed to simulate: {response.status_code}")
    
    # 5. Check pending approvals
    print(f"\n5. Checking pending approvals...")
    response = requests.get(f"{API_BASE}/api/workflow/runs/{run_id}/pending-approvals")
    
    if response.status_code == 200:
        approvals = response.json()
        if approvals["pending"]:
            print(f"✅ Approval pending at node: {approvals['node']}")
            print(f"   Preview data: {json.dumps(approvals.get('data_preview', {}), indent=2)}")
        else:
            print(f"✅ No pending approvals")
    else:
        print(f"❌ Failed to check approvals: {response.status_code}")
    
    # 6. Approve the gate
    print(f"\n6. Approving human gate...")
    response = requests.post(
        f"{API_BASE}/api/workflow/runs/{run_id}/approve",
        json={"approved": True, "notes": "Looks good!"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Gate approved: {result['status']}")
    else:
        print(f"❌ Failed to approve: {response.status_code}")
    
    # 7. Test pause/resume
    print(f"\n7. Testing pause/resume...")
    
    # Create new run for pause test
    response = requests.post(
        f"{API_BASE}/api/workflow/schemas/default/run",
        json={"brand": "TestBrand2", "month": "2025-07"}
    )
    
    if response.status_code == 200:
        pause_run_id = response.json()["run_id"]
        
        # Pause
        response = requests.post(f"{API_BASE}/api/workflow/runs/{pause_run_id}/pause")
        if response.status_code == 200:
            print(f"✅ Run paused: {pause_run_id}")
        else:
            print(f"❌ Failed to pause: {response.status_code}")
        
        # Resume
        response = requests.post(f"{API_BASE}/api/workflow/runs/{pause_run_id}/resume")
        if response.status_code == 200:
            print(f"✅ Run resumed: {pause_run_id}")
        else:
            print(f"❌ Failed to resume: {response.status_code}")
        
        # Cancel
        response = requests.post(f"{API_BASE}/api/workflow/runs/{pause_run_id}/cancel")
        if response.status_code == 200:
            print(f"✅ Run cancelled: {pause_run_id}")
        else:
            print(f"❌ Failed to cancel: {response.status_code}")
    
    # 8. Final status check
    print(f"\n8. Final status check...")
    response = requests.get(f"{API_BASE}/api/workflow/runs")
    
    if response.status_code == 200:
        runs = response.json()
        print(f"✅ Total runs: {len(runs)}")
        for run in runs:
            print(f"   - {run['run_id']}: {run['status']}")
    
    print("\n" + "=" * 60)
    print("✅ HUMAN GATE API TESTS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_human_gate_apis()