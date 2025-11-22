#!/usr/bin/env python3
"""
Get Asana custom field GIDs for a project.
This will show you all custom fields and their GIDs.
"""
import os
import httpx
import asyncio
import json

ASANA_TOKEN = os.getenv("ASANA_ACCESS_TOKEN")
BASE_URL = "https://app.asana.com/api/1.0"

async def get_custom_fields(project_gid: str):
    """Get all custom fields for a project"""
    headers = {
        "Authorization": f"Bearer {ASANA_TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        # Get project details including custom fields
        response = await client.get(
            f"{BASE_URL}/projects/{project_gid}",
            headers=headers
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        project_data = response.json()["data"]
        custom_fields = project_data.get("custom_field_settings", [])

        print(f"\nProject: {project_data.get('name')}")
        print(f"Project GID: {project_gid}")
        print(f"\nCustom Fields ({len(custom_fields)} found):\n")
        print("="*80)

        for field_setting in custom_fields:
            field = field_setting.get("custom_field", {})
            field_name = field.get("name", "Unknown")
            field_gid = field.get("gid", "Unknown")
            field_type = field.get("resource_subtype", "Unknown")

            print(f"\nField Name: {field_name}")
            print(f"Field GID: {field_gid}")
            print(f"Field Type: {field_type}")

            # If it has enum options, show them
            if "enum_options" in field:
                print("Options:")
                for option in field["enum_options"]:
                    print(f"  - {option.get('name')} (GID: {option.get('gid')})")

        print("\n" + "="*80)
        print("\nTo use in code:")
        print("  Find the field named 'Figma URL' or similar")
        print("  Copy its GID and use it when creating tasks")

if __name__ == "__main__":
    # Buca di Beppo project GID
    project_gid = "1210130934536470"

    print("Fetching custom fields from Asana project...")
    asyncio.run(get_custom_fields(project_gid))
