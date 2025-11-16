# Client Approvals - Testing & Deployment Guide
**Date**: November 14, 2025
**Status**: Ready for Implementation & Testing
**Target Deployment**: Google Cloud Run (Same Day)

---

## Overview

The Client Approvals feature allows clients to review and approve calendar campaigns through:
- **Approval Status Tracking**: Real-time status badges (Approved, Pending, Changes Requested)
- **Change Requests**: Client can request specific changes to campaigns
- **Asana Integration**: Auto-creates approval tasks in Asana
- **Celebration UI**: Shows confetti celebration when approved
- **Desktop Notifications**: Browser notifications on status changes

---

## Current Implementation Status

### ✅ Frontend Complete (Lines in calendar_master.html)
- **Line 4423-4428**: Approval status bar with unapprove button
- **Line 4505-4518**: Changes panel with "Approve All Changes" button
- **Line 4520-4527**: Celebration overlay with confetti animation
- **Line 9044-9143**: `checkApprovalStatus()` - Fetches and displays approval status
- **Line 7733-7741**: `approveAllChanges()` - Handles approval confirmation
- **Line 8964-9037**: Asana task creation integration

### ⏳ Backend Needs Implementation (app/api/calendar.py)
- **Line 981-988**: `GET /api/calendar/approval/{approval_id}` - **STUB** (returns not_found)
- **Line 990-997**: `GET /api/calendar/change-requests/{request_id}` - **STUB** (returns empty)
- **Missing**: `POST /api/calendar/approval/{approval_id}` - Update approval status
- **Missing**: `DELETE /api/calendar/approval/{approval_id}` - Remove approval (unapprove)
- **Missing**: `POST /api/calendar/change-requests` - Create change request

---

## Implementation Plan

### Step 1: Implement Backend Endpoints (30 minutes)

#### Firestore Collections Structure
```python
# Collection: calendar_approvals
{
    "approval_id": "client-slug-2025-11",  # Format: {client_slug}-{year}-{month}
    "client_id": "client_abc",
    "client_name": "ACME Corp",
    "year": 2025,
    "month": 11,
    "status": "pending",  # pending | approved | changes_requested | rejected
    "approved_by": null,  # Email or name of approver
    "approved_at": null,  # Timestamp
    "created_at": "2025-11-14T10:00:00Z",
    "updated_at": "2025-11-14T10:00:00Z",
    "approval_url": "https://approval-page.com/...",
    "asana_task_url": "https://app.asana.com/...",
    "notes": ""
}

# Collection: calendar_change_requests
{
    "request_id": "auto-generated-id",
    "approval_id": "client-slug-2025-11",
    "client_id": "client_abc",
    "campaign_id": "campaign_123",
    "campaign_name": "Black Friday Sale",
    "request_type": "modification",  # modification | deletion | addition
    "requested_change": "Move to November 20th instead",
    "status": "pending",  # pending | completed | rejected
    "created_at": "2025-11-14T10:00:00Z",
    "resolved_at": null
}
```

#### Backend Code Implementation

**File**: `app/api/calendar.py`

```python
from google.cloud import firestore
from datetime import datetime
from fastapi import HTTPException

# Initialize Firestore (ensure this exists at top of file)
db = firestore.Client()

@router.get("/approval/{approval_id}")
async def get_approval(approval_id: str):
    """
    Get approval status for a specific calendar month.

    Args:
        approval_id: Format "{client_slug}-{year}-{month}" e.g. "acme-corp-2025-11"

    Returns:
        {
            "status": "success",
            "data": {
                "approval_id": "...",
                "status": "approved|pending|changes_requested|rejected",
                "approved_by": "user@example.com",
                "approved_at": "2025-11-14T10:00:00Z",
                "notes": "Looks great!",
                "asana_task_url": "https://..."
            }
        }
    """
    try:
        doc_ref = db.collection('calendar_approvals').document(approval_id)
        doc = doc_ref.get()

        if not doc.exists:
            return {
                "status": "not_found",
                "approved": False,
                "approval_id": approval_id,
                "data": {"status": "pending"}  # Frontend expects this structure
            }

        data = doc.to_dict()
        return {
            "status": "success",
            "approved": data.get("status") == "approved",
            "approval_id": approval_id,
            "data": data
        }
    except Exception as e:
        print(f"Error fetching approval: {e}")
        return {
            "status": "error",
            "approved": False,
            "approval_id": approval_id,
            "data": {"status": "pending"},
            "error": str(e)
        }

@router.post("/approval/{approval_id}")
async def update_approval(
    approval_id: str,
    status: str = Body(...),  # approved | changes_requested | rejected
    approved_by: str = Body(None),
    notes: str = Body(None)
):
    """
    Update approval status.

    Request Body:
        {
            "status": "approved",
            "approved_by": "user@example.com",
            "notes": "Optional feedback"
        }
    """
    if status not in ["approved", "changes_requested", "rejected", "pending"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        doc_ref = db.collection('calendar_approvals').document(approval_id)
        doc = doc_ref.get()

        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }

        if status == "approved":
            update_data["approved_by"] = approved_by
            update_data["approved_at"] = datetime.utcnow().isoformat()

        if notes:
            update_data["notes"] = notes

        if doc.exists:
            doc_ref.update(update_data)
        else:
            # Create if doesn't exist
            parts = approval_id.split('-')
            if len(parts) >= 3:
                month = parts[-1]
                year = parts[-2]
                client_slug = '-'.join(parts[:-2])
            else:
                client_slug = approval_id
                year = datetime.now().year
                month = datetime.now().month

            update_data.update({
                "approval_id": approval_id,
                "client_slug": client_slug,
                "year": int(year),
                "month": int(month),
                "created_at": datetime.utcnow().isoformat()
            })
            doc_ref.set(update_data)

        return {
            "status": "success",
            "approval_id": approval_id,
            "data": update_data
        }
    except Exception as e:
        print(f"Error updating approval: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update approval: {str(e)}")

@router.delete("/approval/{approval_id}")
async def delete_approval(approval_id: str):
    """
    Remove approval status (unapprove calendar).
    """
    try:
        doc_ref = db.collection('calendar_approvals').document(approval_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Approval not found")

        doc_ref.delete()

        return {
            "status": "success",
            "message": "Approval removed",
            "approval_id": approval_id
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting approval: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete approval: {str(e)}")

@router.get("/change-requests/{request_id}")
async def get_change_requests(request_id: str):
    """
    Get change requests for a specific calendar approval.

    Args:
        request_id: Same as approval_id "{client_slug}-{year}-{month}"

    Returns:
        {
            "status": "success",
            "requests": [
                {
                    "request_id": "...",
                    "campaign_id": "...",
                    "campaign_name": "Black Friday",
                    "requested_change": "Move to Nov 20",
                    "status": "pending"
                }
            ]
        }
    """
    try:
        # Query all change requests for this approval
        query = db.collection('calendar_change_requests').where('approval_id', '==', request_id)
        docs = query.stream()

        requests = []
        for doc in docs:
            data = doc.to_dict()
            data['request_id'] = doc.id
            requests.append(data)

        return {
            "status": "success",
            "requests": requests,
            "request_id": request_id
        }
    except Exception as e:
        print(f"Error fetching change requests: {e}")
        return {
            "status": "error",
            "requests": [],
            "request_id": request_id,
            "error": str(e)
        }

@router.post("/change-requests")
async def create_change_request(
    approval_id: str = Body(...),
    client_id: str = Body(...),
    campaign_id: str = Body(None),
    campaign_name: str = Body(None),
    request_type: str = Body(...),  # modification | deletion | addition
    requested_change: str = Body(...)
):
    """
    Create a new change request from client.

    Request Body:
        {
            "approval_id": "acme-corp-2025-11",
            "client_id": "client_abc",
            "campaign_id": "campaign_123",
            "campaign_name": "Black Friday Sale",
            "request_type": "modification",
            "requested_change": "Move to November 20th"
        }
    """
    if request_type not in ["modification", "deletion", "addition"]:
        raise HTTPException(status_code=400, detail="Invalid request_type")

    try:
        request_data = {
            "approval_id": approval_id,
            "client_id": client_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "request_type": request_type,
            "requested_change": requested_change,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "resolved_at": None
        }

        doc_ref = db.collection('calendar_change_requests').document()
        doc_ref.set(request_data)

        request_data['request_id'] = doc_ref.id

        return {
            "status": "success",
            "message": "Change request created",
            "data": request_data
        }
    except Exception as e:
        print(f"Error creating change request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create change request: {str(e)}")
```

### Step 2: Implement Missing Frontend Function

**File**: `frontend/public/calendar_master.html`

Add this function around line 9140 (after `checkApprovalStatus()`):

```javascript
// Remove approval status (unapprove calendar)
async function unapproveCalendar() {
    if (!calendarManager.selectedClient) return;

    if (!confirm('Remove approval status? This will reset the calendar to pending state.')) {
        return;
    }

    const client = calendarManager.selectedClient;
    const date = calendarManager.selectedDate;
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const approvalId = `${client.client_slug || client.id}-${year}-${month}`;

    try {
        const response = await authenticatedFetch(`/api/calendar/approval/${approvalId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('✅ Approval status removed', 'success');

            // Hide the approval status bar
            const statusBar = document.getElementById('approvalStatusBar');
            if (statusBar) {
                statusBar.classList.add('hidden');
            }

            // Reset previous status to prevent false notifications
            previousApprovalStatus = null;

        } else {
            const error = await response.json().catch(() => ({detail: 'Unknown error'}));
            showToast(`Failed to remove approval: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error removing approval:', error);
        showToast('Failed to remove approval status', 'error');
    }
}
```

---

## Local Testing Plan

### Prerequisites
```bash
# 1. Ensure Firestore emulator is running (or use production Firestore)
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
source .venv/bin/activate

# 2. Start server on localhost (REQUIRED - not 127.0.0.1)
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

### Test Suite: Client Approvals End-to-End

#### Test 1: Create Approval (Simulate Client Approval Page)
**Objective**: Verify approval can be created and retrieved

```bash
# Method 1: Manual API Test with curl
curl -X POST http://localhost:8000/api/calendar/approval/test-client-2025-11 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "approved_by": "client@example.com",
    "notes": "Calendar looks great!"
  }'

# Expected Response:
# {"status": "success", "approval_id": "test-client-2025-11", "data": {...}}
```

**Method 2: Browser Console Test**
```javascript
// In browser console at http://localhost:8000/static/calendar_master.html
// (Requires client selected)

// Manually approve current month
const client = calendarManager.selectedClient;
const date = calendarManager.selectedDate;
const year = date.getFullYear();
const month = String(date.getMonth() + 1).padStart(2, '0');
const approvalId = `${client.client_slug || client.id}-${year}-${month}`;

await fetch(`http://localhost:8000/api/calendar/approval/${approvalId}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        status: 'approved',
        approved_by: 'test@example.com',
        notes: 'Testing approval'
    })
});

// Should see success response
```

#### Test 2: View Approval Status
**Objective**: Verify approval status displays in UI

```javascript
// In browser console:
await checkApprovalStatus();

// Expected:
// - Green badge appears under month name
// - Shows "✅ Approved by test@example.com"
// - X button to unapprove visible
```

**Visual Check**:
- ✅ Green approval badge visible below month name
- ✅ "Approved by..." text shows correct approver
- ✅ X button (unapprove) visible

#### Test 3: Status Change Notifications
**Objective**: Verify real-time notifications work

```bash
# 1. Leave calendar open in browser
# 2. Change status via API:
curl -X POST http://localhost:8000/api/calendar/approval/test-client-2025-11 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "changes_requested",
    "approved_by": "client@example.com",
    "notes": "Please move Black Friday to the 20th"
  }'

# 3. Wait 10-15 seconds (polling interval)
# Expected: Toast notification "📝 Changes requested"
```

#### Test 4: Remove Approval (Unapprove)
**Objective**: Verify unapprove functionality

```javascript
// In browser with approved calendar:
unapproveCalendar();

// Expected:
// - Confirmation dialog appears
// - On confirm: "✅ Approval status removed" toast
// - Approval badge disappears
```

#### Test 5: Change Requests
**Objective**: Verify change request creation and retrieval

```bash
# Create change request
curl -X POST http://localhost:8000/api/calendar/change-requests \
  -H "Content-Type: application/json" \
  -d '{
    "approval_id": "test-client-2025-11",
    "client_id": "test-client",
    "campaign_id": "campaign_123",
    "campaign_name": "Black Friday Sale",
    "request_type": "modification",
    "requested_change": "Move campaign to November 20th"
  }'

# Get change requests
curl http://localhost:8000/api/calendar/change-requests/test-client-2025-11

# Expected:
# {"status": "success", "requests": [{...}]}
```

#### Test 6: Approval Celebration
**Objective**: Verify celebration overlay triggers

```javascript
// In browser console:
showCelebration();

// Expected:
// - Full-screen overlay appears
// - 🎉 emoji bounces
// - "APPROVED!" text displays
// - Confetti animation (if implemented)
// - Auto-closes after 3 seconds
```

#### Test 7: Firestore Data Verification

```bash
# If using Firestore emulator:
# Visit: http://localhost:4000/firestore

# Check collections:
# 1. calendar_approvals
#    - Should contain test-client-2025-11 document
#    - Verify status, approved_by, approved_at fields

# 2. calendar_change_requests
#    - Should contain change request documents
#    - Verify approval_id links correctly
```

---

## Production Deployment to Google Cloud Run

### Pre-Deployment Checklist

#### Code Verification
- [ ] Backend endpoints implemented in `app/api/calendar.py`
- [ ] `unapproveCalendar()` function added to `calendar_master.html`
- [ ] Firestore client initialized (`db = firestore.Client()`)
- [ ] Import statements added (`from google.cloud import firestore`, `from datetime import datetime`)
- [ ] All local tests passing

#### Firestore Configuration
- [ ] Firestore database enabled in Google Cloud Console
- [ ] Collections created: `calendar_approvals`, `calendar_change_requests`
- [ ] Firestore security rules configured (see below)
- [ ] Service account has Firestore permissions

#### Environment Variables
```bash
# Verify in .env or Google Cloud Run environment:
GOOGLE_CLOUD_PROJECT=emailpilot-app
FIRESTORE_DATABASE=(default)
```

### Firestore Security Rules

**Go to**: Firebase Console → Firestore Database → Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Calendar approvals - authenticated users can read/write
    match /calendar_approvals/{approvalId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
      allow delete: if request.auth != null;
    }

    // Change requests - authenticated users can read/write
    match /calendar_change_requests/{requestId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
  }
}
```

### Deployment Steps

#### Step 1: Build and Test Locally (Final Check)
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
source .venv/bin/activate

# Run all tests from Test Suite above
# Ensure all 7 tests pass

# Check logs for errors
tail -f logs/app.log  # If logging to file
```

#### Step 2: Commit Changes
```bash
git add app/api/calendar.py
git add frontend/public/calendar_master.html
git add CLIENT_APPROVALS_TESTING_DEPLOYMENT.md

git commit -m "$(cat <<'EOF'
Implement Client Approvals with Firestore backend

## Features
- ✅ GET /api/calendar/approval/{id} - Retrieve approval status
- ✅ POST /api/calendar/approval/{id} - Update approval status
- ✅ DELETE /api/calendar/approval/{id} - Remove approval
- ✅ GET /api/calendar/change-requests/{id} - Get change requests
- ✅ POST /api/calendar/change-requests - Create change request
- ✅ unapproveCalendar() frontend function
- ✅ Firestore integration with real-time sync
- ✅ Desktop notifications on status changes
- ✅ Celebration overlay on approval

## Testing
- Tested locally with Firestore emulator
- All 7 test scenarios passing
- No breaking changes to existing features

## Deployment
- Ready for Google Cloud Run
- Firestore security rules configured
- Service account permissions verified

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

git push origin main
```

#### Step 3: Deploy to Google Cloud Run
```bash
# Option 1: Using gcloud CLI
gcloud run deploy emailpilot-app \
  --source . \
  --project emailpilot-app \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=emailpilot-app

# Option 2: Using make command (if configured)
make deploy

# Option 3: Automatic deployment (if CI/CD configured)
# Push to main branch triggers automatic deployment
```

#### Step 4: Verify Production Deployment

```bash
# 1. Check deployment status
gcloud run services describe emailpilot-app --region us-central1

# 2. Get production URL
PROD_URL=$(gcloud run services describe emailpilot-app --region us-central1 --format 'value(status.url)')
echo "Production URL: $PROD_URL"

# 3. Test health endpoint
curl $PROD_URL/health

# Expected: {"status": "ok"}

# 4. Test approval endpoint (stub response)
curl $PROD_URL/api/calendar/approval/test-client-2025-11

# Expected: {"status": "not_found", ...} if no data exists
```

#### Step 5: Production Smoke Tests

**Test 1: Create Approval in Production**
```bash
curl -X POST $PROD_URL/api/calendar/approval/prod-test-2025-11 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "approved_by": "production-test@example.com",
    "notes": "Production smoke test"
  }'
```

**Test 2: Retrieve Approval**
```bash
curl $PROD_URL/api/calendar/approval/prod-test-2025-11
```

**Test 3: Frontend Test**
1. Navigate to: `$PROD_URL/static/calendar_master.html`
2. Select a client
3. Open browser console
4. Run: `await checkApprovalStatus();`
5. Verify no errors in console

#### Step 6: Monitor Logs
```bash
# Stream production logs
gcloud run logs tail emailpilot-app --region us-central1

# Watch for:
# - "Error fetching approval" (should be minimal)
# - "Error updating approval" (should not appear)
# - Any Python exceptions
```

---

## Production Monitoring

### Key Metrics to Watch

**1. API Response Times**
- `/api/calendar/approval/{id}` - Target: <500ms
- `/api/calendar/change-requests/{id}` - Target: <500ms

**2. Error Rates**
- Monitor for 500 errors
- Watch Firestore connection errors
- Check authentication failures

**3. Firestore Usage**
- Document reads: Should increase with approval checks
- Document writes: Should match approval updates
- Watch for quota limits

### Logging & Debugging

**Enable detailed logging in production:**

```python
# Add to app/api/calendar.py at top
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add in each endpoint:
logger.info(f"Fetching approval: {approval_id}")
logger.error(f"Error updating approval: {e}")
```

---

## Rollback Plan

If issues arise in production:

```bash
# 1. Check last successful deployment
gcloud run revisions list --service emailpilot-app --region us-central1

# 2. Rollback to previous revision
gcloud run services update-traffic emailpilot-app \
  --to-revisions=emailpilot-app-00001-xyz=100 \
  --region us-central1

# 3. Verify rollback
curl $PROD_URL/health
```

---

## Post-Deployment Tasks

### Day 1 After Deployment
- [ ] Monitor error logs for first 24 hours
- [ ] Check Firestore usage metrics
- [ ] Test approval flow with real client
- [ ] Verify Asana integration still working
- [ ] Confirm desktop notifications work

### Week 1 After Deployment
- [ ] Collect user feedback on approval flow
- [ ] Review Firestore costs
- [ ] Optimize any slow queries
- [ ] Add analytics tracking for approval events
- [ ] Document any discovered edge cases

---

## Troubleshooting Guide

### Issue: Approval status not displaying
**Symptoms**: No green badge appears after approval
**Causes**:
1. Frontend polling not running
2. Firestore document doesn't exist
3. approval_id format mismatch

**Fix**:
```javascript
// Debug in console:
console.log('Checking approval for:', approvalId);
await checkApprovalStatus();  // Manually trigger
```

### Issue: 403 Firestore Permission Denied
**Symptoms**: "Permission denied" errors in logs
**Causes**:
1. Firestore security rules too restrictive
2. Service account missing permissions

**Fix**:
```bash
# Grant Firestore permissions to service account
gcloud projects add-iam-policy-binding emailpilot-app \
  --member="serviceAccount:YOUR-SERVICE-ACCOUNT@emailpilot-app.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### Issue: Change requests not loading
**Symptoms**: Change requests panel empty
**Causes**:
1. No change requests created yet
2. Query filtering by wrong approval_id
3. Firestore collection doesn't exist

**Fix**:
```javascript
// Debug in console:
const approvalId = `${client.client_slug}-${year}-${month}`;
console.log('Fetching change requests for:', approvalId);
const response = await authenticatedFetch(`/api/calendar/change-requests/${approvalId}`);
console.log('Response:', await response.json());
```

---

## Success Criteria

### Deployment Successful When:
✅ All 7 local tests passing
✅ Production smoke tests passing
✅ No 500 errors in logs
✅ Approval status displays correctly in UI
✅ Unapprove button works
✅ Change requests can be created
✅ Desktop notifications trigger on status change
✅ Celebration overlay shows on approval
✅ Asana integration still functional

### Performance Targets:
- API latency < 500ms (p95)
- Firestore read/write success rate > 99.5%
- Zero data loss
- No authentication errors

---

## Estimated Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Implementation** | 30-45 min | Add backend endpoints + frontend function |
| **Local Testing** | 15-20 min | Run all 7 test scenarios |
| **Deployment** | 10-15 min | Commit, push, deploy to Cloud Run |
| **Verification** | 10-15 min | Production smoke tests + monitoring |
| **Total** | **65-95 min** | **Complete end-to-end same-day deployment** |

---

**Status**: 📋 Ready for Implementation
**Next Action**: Implement backend endpoints in `app/api/calendar.py`
**Goal**: Production deployment today (November 14, 2025)
