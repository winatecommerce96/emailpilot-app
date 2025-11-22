# Asana Calendar Integration Setup Guide

This guide explains how to configure and use the Asana integration for calendar approvals.

## Overview

When you create a calendar approval page in EmailPilot, the system automatically creates an Asana task to notify the client. The task is:

- **Multi-homed** in both the client's Asana project AND the Account Management project
- **Contains** a direct link to the approval page
- **Sets** the approval URL in the "Figma URL" custom field (if it exists)

## Prerequisites

1. **Asana API Token** stored in Google Secret Manager
   - Secret name: `asana-api-token`
   - Must have write permissions to Asana projects

2. **Client Configuration** in Firestore
   - Each client document must have `asana_project_link` field
   - Format: `https://app.asana.com/0/{PROJECT_GID}/list`

3. **Account Management Project** (optional but recommended)
   - Create or identify your Account Management project in Asana
   - Note the project GID from the URL

## Configuration Steps

### 1. Set Account Management Project GID

Add this environment variable to your `.env` file or Cloud Run configuration:

```bash
ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID=1234567890123456
```

**How to find your Account Management project GID:**
1. Open the project in Asana
2. Look at the URL: `https://app.asana.com/0/{PROJECT_GID}/list`
3. Copy the long number (15-16 digits) after `/0/`

### 2. Set Public Base URL

Add this environment variable for production:

```bash
PUBLIC_BASE_URL=https://app.emailpilot.ai
```

For local development, it defaults to `http://localhost:8000`.

### 3. Configure Client Asana Project Links

In Firestore, for each client document in the `clients` collection, add:

```json
{
  "name": "Client Name",
  "client_slug": "client-slug",
  "asana_project_link": "https://app.asana.com/0/1234567890123456/list"
}
```

### 4. (Optional) Add "Figma URL" Custom Field

To have the approval URL automatically populated in a custom field:

1. Go to your client's Asana project
2. Click "Customize" in the top right
3. Add a new custom field:
   - **Name**: `Figma URL` (exact match required)
   - **Type**: Text or URL
4. Save the custom field

The integration will automatically find and populate this field with the approval URL.

## How It Works

### Workflow

1. User creates a calendar approval in EmailPilot
2. System saves approval to Firestore
3. Background task triggers Asana integration:
   - Looks up client's `asana_project_link`
   - Extracts project GID from URL
   - Creates task with title: "Review {Client} Campaign Calendar for {Month} {Year}"
   - Multi-homes task in client project + Account Management project
   - Sets "Figma URL" custom field (if exists)
   - Logs success/warnings

### Task Details

**Task Name:**
```
Review ClientName Campaign Calendar for January 2025
```

**Task Description:**
```
Please review and approve the campaign calendar for January 2025.

**Client**: ClientName
**Approval Page**: https://app.emailpilot.ai/calendar-approval/abc-123

Click the link above to:
✓ View all scheduled campaigns
✓ Approve the calendar
✓ Request any changes

Once approved, we'll move forward with campaign execution.

---
**Approval ID**: abc-123
**Created**: 2025-01-18T10:30:00Z
```

**Projects:**
- Client's project (from `asana_project_link`)
- Account Management project (if `ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID` is set)

**Custom Fields:**
- `Figma URL`: Set to approval page URL (if field exists in project)

## Error Handling

The integration is designed to be **resilient** and never block approval creation:

### Graceful Degradation

| Issue | Behavior |
|-------|----------|
| No Asana token | Warning logged, no task created |
| No client `asana_project_link` | Warning logged, no task created |
| Invalid project URL | Error logged, no task created |
| Account Management GID not set | Warning logged, task created only in client project |
| "Figma URL" field not found | Warning logged, task created without custom field |
| Asana API error | Error logged, approval creation still succeeds |

### Logging

All operations are logged with appropriate levels:

- **INFO**: Successful task creation with URLs
- **WARNING**: Missing configuration, degraded functionality
- **ERROR**: API errors, unexpected failures

Check logs for Asana integration status:

```bash
grep "Asana task" logs/emailpilot_app.log
```

## Testing

### Manual Test

1. Ensure environment variables are set
2. Create a test client with `asana_project_link`
3. Create a calendar approval via API or UI
4. Check logs for Asana task creation
5. Verify task appears in both projects (if multi-homed)
6. Check "Figma URL" field is populated

### Test API Endpoint

You can test the integration directly:

```bash
curl -X POST http://localhost:8000/api/calendar/approval/create \
  -H "Content-Type: application/json" \
  -d '{
    "approval_id": "test-123",
    "client_id": "client-doc-id",
    "client_name": "Test Client",
    "client_slug": "test-client",
    "year": 2025,
    "month": 1,
    "month_name": "January",
    "campaigns": [],
    "created_at": "2025-01-18T10:30:00Z",
    "status": "pending",
    "editable": true
  }'
```

Expected response:

```json
{
  "success": true,
  "approval_id": "test-123",
  "approval_url": "http://localhost:8000/calendar-approval/test-123",
  "message": "Approval page created successfully. Asana task will be created in background."
}
```

## Monitoring

### Approval Document Fields

After successful Asana task creation, the approval document is updated with:

```json
{
  "approval_id": "abc-123",
  "status": "pending",
  "asana_task_gid": "1234567890123456",
  "asana_task_url": "https://app.asana.com/0/...",
  "asana_created_at": "2025-01-18T10:30:00Z"
}
```

### Query Recent Tasks

Check Firestore for approvals with Asana tasks:

```python
from google.cloud import firestore

db = firestore.Client()
approvals = db.collection("approval_pages")\
    .where("asana_task_gid", "!=", None)\
    .order_by("asana_created_at", direction=firestore.Query.DESCENDING)\
    .limit(10)\
    .stream()

for approval in approvals:
    data = approval.to_dict()
    print(f"{data['client_name']}: {data['asana_task_url']}")
```

## Troubleshooting

### Issue: Tasks not being created

**Check:**
1. Is `asana-api-token` in Secret Manager?
2. Does client have `asana_project_link` field?
3. Is the project URL valid?
4. Check logs for error messages

### Issue: Task created only in client project, not Account Management

**Solution:**
Set the `ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID` environment variable.

### Issue: "Figma URL" field not populated

**Possible Causes:**
1. Field doesn't exist in the project
2. Field name is not exactly "Figma URL" (case-sensitive)
3. API permission issues

**Solution:**
Check logs for custom field warnings. Ensure field exists and is named exactly "Figma URL".

### Issue: Background task timing out

**Solution:**
Increase timeout in Cloud Run configuration or reduce Asana API calls.

## Code Reference

### Main Integration File
`/app/services/asana_calendar_integration.py`

### Enhanced AsanaClient
`/app/services/asana_client.py`

### Calendar Router Integration
`/app/api/calendar.py` - Line ~1216 (`create_approval_page` endpoint)

## Future Enhancements

Potential improvements:

1. **Task Assignment**: Auto-assign to client account manager
2. **Due Dates**: Set task due date based on campaign start date
3. **Subtasks**: Create subtasks for each campaign
4. **Tags**: Add tags for month, year, client tier
5. **Webhooks**: Listen for task completion in Asana to auto-approve calendar
6. **Notifications**: Send Slack/email when task is created

## Support

For issues or questions:
- Check logs: `logs/emailpilot_app.log`
- Review Firestore: `approval_pages` collection
- Test Asana API token: Use `/api/admin/asana/ping` endpoint (if available)
- Check Asana project permissions

---

**Last Updated**: 2025-01-18
**Version**: 1.0.0
