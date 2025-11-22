"""
Asana Calendar Integration Service

Handles creating Asana tasks when calendar approvals are created.
Multi-homes tasks in both client project and Account Management project.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
import logging
import os
from datetime import datetime
from google.cloud import firestore, secretmanager

from app.services.asana_client import AsanaClient

logger = logging.getLogger(__name__)

# Configuration constants
# TODO: Set this to your actual Account Management project GID
# You can find it in the Asana URL: https://app.asana.com/0/{PROJECT_GID}/list
ACCOUNT_MANAGEMENT_PROJECT_GID = os.getenv(
    "ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID",
    None  # Will need to be configured
)

# Custom field name for storing approval URL
FIGMA_URL_FIELD_NAME = "Figma URL"


async def get_asana_token() -> Optional[str]:
    """Get Asana API token from environment variable or Secret Manager

    Following the pattern from asana-brief-creation app:
    1. Check ASANA_ACCESS_TOKEN environment variable first
    2. Fall back to Secret Manager if not found
    """
    # Check environment variable first (same as asana-brief-creation)
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if token:
        logger.info("Using ASANA_ACCESS_TOKEN from environment variable")
        return token.strip()

    # Fall back to Secret Manager
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        secret_name = f"projects/{project_id}/secrets/asana-access-token/versions/latest"

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": secret_name})
        token = response.payload.data.decode("UTF-8").strip()
        logger.info("Using Asana token from Secret Manager")
        return token
    except Exception as e:
        logger.warning(f"Could not retrieve Asana token from Secret Manager: {e}")
        return None


async def create_calendar_approval_task(
    client_id: str,
    client_name: str,
    approval_id: str,
    approval_url: str,
    month: str,
    year: int,
    db: firestore.Client
) -> Dict[str, Any]:
    """
    Create an Asana task when a calendar approval is created.

    Args:
        client_id: Firestore client document ID
        client_name: Client display name
        approval_id: Approval page ID
        approval_url: Public URL for client to review approval
        month: Month name (e.g., "January")
        year: Year (e.g., 2025)
        db: Firestore client instance

    Returns:
        Dict with success status, task_gid, task_url, and any warnings

    The task will be:
    - Created in the client's Asana project (from asana_project_link)
    - Multi-homed in the Account Management project (if configured)
    - Have the approval URL set in the "Figma URL" custom field (if it exists)
    """
    result = {
        "success": False,
        "task_gid": None,
        "task_url": None,
        "warnings": [],
        "error": None
    }

    try:
        # 1. Get client data from Firestore
        client_ref = db.collection("clients").document(client_id)
        client_doc = client_ref.get()

        if not client_doc.exists:
            result["error"] = f"Client {client_id} not found in Firestore"
            logger.error(result["error"])
            return result

        client_data = client_doc.to_dict()
        asana_project_link = client_data.get("asana_project_link")

        if not asana_project_link:
            result["error"] = f"Client {client_name} does not have an Asana project link configured"
            result["warnings"].append("Skipping Asana task creation - no project link")
            logger.warning(result["error"])
            return result

        # 2. Get Asana token
        asana_token = await get_asana_token()
        if not asana_token:
            result["error"] = "Asana API token not configured in Secret Manager"
            result["warnings"].append("Cannot create Asana task - missing token")
            logger.error(result["error"])
            return result

        # 3. Initialize Asana client and parse project GID
        asana_client = AsanaClient(asana_token)
        client_project_gid = asana_client.parse_project_gid_from_url(asana_project_link)

        if not client_project_gid:
            result["error"] = f"Could not parse Asana project GID from URL: {asana_project_link}"
            logger.error(result["error"])
            return result

        logger.info(f"Creating Asana task for {client_name} in project {client_project_gid}")

        # 4. Build project list (client project + Account Management if configured)
        project_list = [client_project_gid]
        if ACCOUNT_MANAGEMENT_PROJECT_GID:
            project_list.append(ACCOUNT_MANAGEMENT_PROJECT_GID)
            logger.info(f"Multi-homing task in Account Management project: {ACCOUNT_MANAGEMENT_PROJECT_GID}")
        else:
            result["warnings"].append("Account Management project GID not configured - task not multi-homed")
            logger.warning("ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID not set - task will only be in client project")

        # 5. Prepare task details
        task_name = f"Review {client_name} Campaign Calendar for {month} {year}"
        task_notes = f"""Please review and approve the campaign calendar for {month} {year}.

**Client**: {client_name}
**Approval Page**: {approval_url}

Click the link above to:
✓ View all scheduled campaigns
✓ Approve the calendar
✓ Request any changes

Once approved, we'll move forward with campaign execution.

---
**Approval ID**: {approval_id}
**Created**: {datetime.utcnow().isoformat()}Z
"""

        # 6. Try to find "Figma URL" custom field in client's project
        custom_fields_dict = None
        try:
            figma_field = await asana_client.find_custom_field_by_name(
                client_project_gid,
                FIGMA_URL_FIELD_NAME
            )

            if figma_field:
                field_gid = figma_field.get("gid")
                field_type = figma_field.get("resource_type", "text")

                # Asana custom field format: {field_gid: value}
                custom_fields_dict = {field_gid: approval_url}
                logger.info(f"Found '{FIGMA_URL_FIELD_NAME}' custom field (GID: {field_gid}), setting to: {approval_url}")
            else:
                result["warnings"].append(f"Custom field '{FIGMA_URL_FIELD_NAME}' not found in client project")
                logger.warning(f"Custom field '{FIGMA_URL_FIELD_NAME}' not found in project {client_project_gid}")

        except Exception as custom_field_error:
            result["warnings"].append(f"Could not set custom field: {str(custom_field_error)}")
            logger.warning(f"Error looking up custom field: {custom_field_error}")

        # 7. Create the task
        task_result = await asana_client.create_task(
            name=task_name,
            project_gid=client_project_gid,  # Primary project (required for backwards compat)
            projects=project_list,  # All projects for multi-homing
            notes=task_notes,
            custom_fields=custom_fields_dict
        )

        task_data = task_result.get("data", {})
        task_gid = task_data.get("gid")
        task_permalink = task_data.get("permalink_url")

        if not task_gid:
            result["error"] = "Task created but no GID returned"
            logger.error(f"Asana API response missing task GID: {task_result}")
            return result

        # 8. Build task URL
        task_url = task_permalink or f"https://app.asana.com/0/{client_project_gid}/{task_gid}"

        result["success"] = True
        result["task_gid"] = task_gid
        result["task_url"] = task_url

        logger.info(f"✅ Created Asana task for {client_name}: {task_url}")
        logger.info(f"   Task GID: {task_gid}")
        logger.info(f"   Projects: {', '.join(project_list)}")

        return result

    except Exception as e:
        error_msg = f"Unexpected error creating Asana task: {str(e)}"
        result["error"] = error_msg
        logger.error(error_msg, exc_info=True)
        return result
