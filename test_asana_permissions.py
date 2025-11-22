#!/usr/bin/env python3
"""
Test Asana API permissions to diagnose 403 errors.
This script tests if we can create tasks in different contexts.
"""
import os
import httpx
import asyncio
from datetime import datetime

# Use environment variable
ASANA_TOKEN = os.getenv("ASANA_ACCESS_TOKEN")
if not ASANA_TOKEN:
    print("ERROR: ASANA_ACCESS_TOKEN environment variable not set")
    exit(1)

BASE_URL = "https://app.asana.com/api/1.0"
HEADERS = {
    "Authorization": f"Bearer {ASANA_TOKEN}",
    "Content-Type": "application/json"
}

async def test_permissions():
    async with httpx.AsyncClient() as client:
        print("\n" + "="*80)
        print("ASANA PERMISSIONS DIAGNOSTIC TEST")
        print("="*80 + "\n")

        # Test 1: Get current user info
        print("Test 1: Get Current User Info")
        print("-" * 80)
        try:
            response = await client.get(f"{BASE_URL}/users/me", headers=HEADERS)
            if response.status_code == 200:
                user = response.json()["data"]
                print(f"✅ Successfully authenticated as: {user.get('name')} ({user.get('email')})")
                print(f"   User GID: {user.get('gid')}")
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 2: List workspaces
        print("Test 2: List Workspaces")
        print("-" * 80)
        try:
            response = await client.get(f"{BASE_URL}/workspaces", headers=HEADERS)
            if response.status_code == 200:
                workspaces = response.json()["data"]
                print(f"✅ Found {len(workspaces)} workspace(s):")
                for ws in workspaces:
                    print(f"   - {ws.get('name')} (GID: {ws.get('gid')})")

                # Use first workspace for testing
                if workspaces:
                    workspace_gid = workspaces[0]["gid"]
                    workspace_name = workspaces[0]["name"]
                else:
                    print("❌ No workspaces found")
                    return
            else:
                print(f"❌ Failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"❌ Error: {e}")
            return
        print()

        # Test 3: Try creating a task WITHOUT a project (should work if user has permissions)
        print("Test 3: Create Task in Workspace (No Project)")
        print("-" * 80)
        print(f"Attempting to create test task in workspace: {workspace_name}")
        try:
            task_data = {
                "data": {
                    "workspace": workspace_gid,
                    "name": f"[TEST] Permission Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "notes": "This is a test task created by EmailPilot to verify API permissions. You can delete this task."
                }
            }
            response = await client.post(f"{BASE_URL}/tasks", headers=HEADERS, json=task_data)

            if response.status_code == 201:
                task = response.json()["data"]
                task_gid = task.get("gid")
                print(f"✅ SUCCESS! Task created: {task.get('name')}")
                print(f"   Task GID: {task_gid}")
                print(f"   Task URL: https://app.asana.com/0/0/{task_gid}")
                print("\n   🎉 Your API token HAS write permissions!")
                print("   The 403 error is likely a PROJECT-SPECIFIC permission issue.")

                # Clean up - delete the test task
                print("\n   Cleaning up test task...")
                delete_response = await client.delete(f"{BASE_URL}/tasks/{task_gid}", headers=HEADERS)
                if delete_response.status_code == 200:
                    print("   ✅ Test task deleted")
                else:
                    print(f"   ⚠️  Could not delete test task (GID: {task_gid}). Please delete manually.")

            elif response.status_code == 403:
                print(f"❌ 403 FORBIDDEN - Your API token lacks write permissions")
                print(f"   Response: {response.text}")
                print("\n   SOLUTION: You need to:")
                print("   1. Check if you're a full workspace member (not a guest)")
                print("   2. Verify your Asana account has task creation rights")
                print("   3. Contact your workspace admin to upgrade your permissions")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        # Test 4: Try creating task in the specific project
        print("Test 4: Create Task in Specific Project")
        print("-" * 80)
        project_gid = "1207930299088661"  # WIN Marketing Materials
        project_name = "WIN Marketing Materials"
        print(f"Attempting to create task in project: {project_name}")
        try:
            task_data = {
                "data": {
                    "projects": [project_gid],
                    "name": f"[TEST] Permission Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "notes": "This is a test task created by EmailPilot. You can delete this task."
                }
            }
            response = await client.post(f"{BASE_URL}/tasks", headers=HEADERS, json=task_data)

            if response.status_code == 201:
                task = response.json()["data"]
                task_gid = task.get("gid")
                print(f"✅ SUCCESS! Task created in project")
                print(f"   Task GID: {task_gid}")
                print(f"   Task URL: https://app.asana.com/0/{project_gid}/{task_gid}")

                # Clean up
                print("\n   Cleaning up test task...")
                delete_response = await client.delete(f"{BASE_URL}/tasks/{task_gid}", headers=HEADERS)
                if delete_response.status_code == 200:
                    print("   ✅ Test task deleted")
                else:
                    print(f"   ⚠️  Could not delete test task. Please delete manually.")

            elif response.status_code == 403:
                print(f"❌ 403 FORBIDDEN - You lack permission to create tasks in this project")
                print(f"   Response: {response.text}")
                print("\n   SOLUTION:")
                print(f"   1. Go to: https://app.asana.com/0/{project_gid}")
                print("   2. Check your role - you need 'Can edit' permissions (not just 'Can view')")
                print("   3. Ask the project owner to upgrade your permissions")
                print("   4. OR choose a different project where you have edit access")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        print("="*80)
        print("DIAGNOSTIC TEST COMPLETE")
        print("="*80)

if __name__ == "__main__":
    asyncio.run(test_permissions())
