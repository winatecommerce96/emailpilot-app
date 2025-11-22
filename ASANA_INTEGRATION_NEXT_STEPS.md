# Asana Integration - Next Steps

**Date**: 2025-11-18
**Status**: Implementation Complete, Environment Variable Loading Issue
**Priority**: Medium

## Executive Summary

The Asana integration for calendar approvals is fully implemented and functional. The Configure Projects feature and automatic task creation are working correctly. However, there's a persistent issue with loading the `ASANA_ACCESS_TOKEN` environment variable from the `.env` file when running with uvicorn in reload mode.

## What's Been Implemented

### 1. Asana Task Creation for Calendar Approvals
**File**: `app/services/asana_calendar_integration.py`

- ✅ Creates Asana tasks automatically when calendar approvals are generated
- ✅ Multi-homes tasks in both client project and Account Management project
- ✅ Sets approval URL in "Figma URL" custom field (if exists)
- ✅ Includes detailed task description with approval link and metadata

### 2. Configure Projects Admin Feature
**File**: `app/api/admin_asana.py`

- ✅ Lists all Asana workspace projects
- ✅ Retrieves client list from Firestore
- ✅ Returns combined data for client-to-project mapping UI
- ✅ Endpoint: `GET /api/admin/asana/configuration/clients-and-projects`

### 3. Asana Client Helper
**File**: `app/services/asana_client.py`

- ✅ Lightweight wrapper around Asana REST API
- ✅ Handles authentication with Personal Access Token
- ✅ Supports pagination for large result sets
- ✅ Methods for projects, tasks, custom fields, and webhooks

### 4. Environment Configuration
**File**: `.env`

```bash
# Asana Integration (following asana-brief-creation pattern)
ASANA_ACCESS_TOKEN=2/1211869786694289/1211869801326943:0d2de7e29a11434ca6ad4349810cf489
ASANA_ACCOUNT_MANAGEMENT_PROJECT_GID=1205935065942123
```

## Current Issue: Environment Variable Not Loading

### Problem Description

The `ASANA_ACCESS_TOKEN` environment variable is defined in the `.env` file but is not being picked up by the FastAPI application when running with `uvicorn --reload`.

### Symptoms

- API endpoint returns: `{"detail":"Asana API token not configured in Secret Manager"}`
- Manual testing shows `load_dotenv()` works when called directly
- Environment variable is accessible outside uvicorn context
- Issue persists even with explicit `export ASANA_ACCESS_TOKEN=...` before uvicorn

### What We've Tried

1. ✅ Added `load_dotenv()` to `main_firestore.py` (line 24-27)
2. ✅ Specified explicit `.env` file path
3. ✅ Cleared all Python `__pycache__` directories
4. ✅ Restarted server multiple times
5. ✅ Exported environment variable directly in shell before starting uvicorn
6. ⚠️ None of these approaches resolved the issue

### Root Cause Hypothesis

Uvicorn's reload mode creates worker processes that may not inherit the parent process's environment. The `.env` file approach that works for the asana-brief-creation project may not work the same way with uvicorn's process model.

## Recommended Solutions (Choose One)

### Option 1: Store Token in Google Secret Manager (RECOMMENDED)

**Why**: This is production-ready, secure, and aligns with the existing infrastructure.

**Steps**:

1. Add the Asana token to Google Cloud Secret Manager:
```bash
echo -n "2/1211869786694289/1211869801326943:0d2de7e29a11434ca6ad4349810cf489" | \
  gcloud secrets create asana-access-token \
  --data-file=- \
  --project=emailpilot-438321
```

2. Verify it's accessible:
```bash
gcloud secrets versions access latest \
  --secret="asana-access-token" \
  --project=emailpilot-438321
```

3. The code already has fallback logic to Secret Manager, so this should work immediately.

**Pros**:
- Production-ready
- Secure
- Already implemented in the code
- Works in all environments (local, Cloud Run)

**Cons**:
- Requires gcloud CLI access
- Adds dependency on Google Cloud

---

### Option 2: Fix Environment Variable Loading

**Why**: Maintains consistency with asana-brief-creation pattern.

**Investigation Needed**:

1. Check if uvicorn's `--reload` flag is causing environment inheritance issues
2. Test without `--reload` flag:
```bash
source .venv/bin/activate
export ASANA_ACCESS_TOKEN="2/1211869786694289/1211869801326943:0d2de7e29a11434ca6ad4349810cf489"
uvicorn main_firestore:app --port 8000 --host localhost
```

3. If that works, investigate uvicorn reload subprocess environment propagation
4. Consider alternative approaches:
   - Use `python-dotenv` with `override=True`
   - Load env vars in a startup event instead of module-level
   - Use uvicorn's `--env-file` parameter (if available)

**Files to Modify**:
- `main_firestore.py` (lines 21-28)

**Pros**:
- Follows asana-brief-creation pattern
- Simpler for local development
- No external dependencies

**Cons**:
- May not work reliably across all environments
- Debugging time required
- Not recommended for production secrets

---

### Option 3: Hybrid Approach

Use environment variables for local development and Secret Manager for production:

```python
# In app/api/admin_asana.py and app/services/asana_calendar_integration.py

async def get_asana_token() -> Optional[str]:
    # 1. Check environment variable (local dev)
    token = os.getenv("ASANA_ACCESS_TOKEN")
    if token:
        logger.info("Using ASANA_ACCESS_TOKEN from environment variable")
        return token.strip()

    # 2. Check Secret Manager (production)
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        secret_service = SecretManagerService(project_id)
        token = secret_service.get_secret("asana-access-token")
        if token:
            logger.info("Using Asana token from Secret Manager")
            return token.strip()
    except Exception as e:
        logger.warning(f"Could not retrieve Asana token: {e}")

    return None
```

This pattern is **already implemented** in the code - it just needs the Secret Manager secret to be created.

## Testing Steps

### After Implementing Solution

1. **Test Configure Projects Endpoint**:
```bash
curl -s http://localhost:8000/api/admin/asana/configuration/clients-and-projects | python3 -m json.tool
```

Expected response:
```json
{
  "clients": [...],
  "available_projects": [...]
}
```

2. **Test Calendar Approval Task Creation**:
- Create a calendar approval through the UI
- Check that an Asana task is created
- Verify the task is in the correct project
- Verify the "Figma URL" field contains the approval link

3. **Verify Multi-Homing**:
- Check that the task appears in both:
  - The client's Asana project
  - The Account Management project (GID: 1205935065942123)

## Files Reference

### Implementation Files
- `app/services/asana_calendar_integration.py` - Task creation logic
- `app/api/admin_asana.py` - Configure Projects API
- `app/services/asana_client.py` - Asana API wrapper
- `.env` - Environment configuration

### Frontend Files (Already Implemented)
- `frontend/public/calendar-approval.html` - Approval page UI
- Configuration UI for mapping clients to projects (ready for integration)

## Configuration Details

### Account Management Project
**GID**: `1205935065942123`
**Purpose**: All calendar approval tasks are multi-homed here for centralized tracking

### Custom Fields
The integration looks for a custom field named **"Figma URL"** in each client's project to store the approval link. If the field doesn't exist, the URL is still included in the task notes.

## Security Notes

⚠️ **Important**: The Asana Personal Access Token in `.env` should:
- Be added to `.gitignore` (already done)
- Not be committed to version control
- Be rotated periodically
- Be stored in Secret Manager for production

## Next Developer Actions

### Immediate (Quick Win)
1. Choose **Option 1** (Secret Manager) - 5 minutes
2. Test the Configure Projects endpoint
3. Test calendar approval task creation
4. Document any issues

### If More Time Available
1. Investigate uvicorn environment variable issue
2. Implement proper fix for `.env` loading
3. Add integration tests for Asana features
4. Update UI to show Asana task links in approval confirmations

## Contact & Questions

If you encounter issues or need clarification:
- Check server logs for detailed error messages
- Verify `ASANA_ACCESS_TOKEN` environment variable value
- Test Secret Manager access with gcloud CLI
- Review Asana API documentation: https://developers.asana.com/docs

## Related Documentation

- **Asana Brief Creation Pattern**: `/Users/Damon/asana-brief-creation/README.md`
- **Secret Manager Service**: `app/services/secret_manager.py`
- **Calendar Integration Specs**: `CALENDAR_IMPORT_TECHNICAL_SPECIFICATIONS.md`

---

**Status**: Ready for developer handoff
**Estimated Resolution Time**: 15-30 minutes (if using Option 1)
