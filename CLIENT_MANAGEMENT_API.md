# Client Management API Documentation

Complete guide to managing clients in EmailPilot for the Campaign Co-Pilot calendar.

## Overview

The EmailPilot system has **two client API endpoints**:
1. **Public API** (`/api/clients/`) - Used by the calendar, no authentication required
2. **Admin API** (`/api/admin/clients`) - Full CRUD operations, requires authentication

---

## Public API (Calendar)

### GET /api/clients/

**Purpose**: Load all clients for calendar selection

**Authentication**: None required

**Response**:
```json
[
  {
    "id": "client-id-123",
    "name": "Buca di Beppo",
    "client_slug": "buca-di-beppo",
    "description": "Italian restaurant chain",
    "status": "active",
    "is_active": true
  }
]
```

**Usage in Calendar**:
```javascript
// calendar_master.html:5162
const response = await fetch('/api/clients/');
const clients = await response.json();
this.clients = clients;
```

**Status**: ✅ NOW REGISTERED (as of this fix)

---

## Admin API (Full Management)

Base URL: `/api/admin/clients`

All admin endpoints require authentication (session-based or dev mode bypass).

### 1. List All Clients

**Endpoint**: `GET /api/admin/clients`

**Query Parameters**:
- `active_only` (boolean, default: true) - Filter active clients only

**Response**:
```json
[
  {
    "id": "client-id-123",
    "name": "Buca di Beppo",
    "client_slug": "buca-di-beppo",
    "is_active": true,
    "created_at": "2025-01-15T10:00:00",
    "updated_at": "2025-01-15T10:00:00"
  }
]
```

### 2. Get Client Details

**Endpoint**: `GET /api/admin/clients/{client_id}`

**Response**:
```json
{
  "id": "client-id-123",
  "name": "Buca di Beppo",
  "client_slug": "buca-di-beppo",
  "description": "Italian restaurant chain",
  "contact_email": "marketing@bucadibeppo.com",
  "contact_name": "John Doe",
  "website": "https://bucadibeppo.com",
  "is_active": true,

  "metric_id": "revenue-metric-id",
  "klaviyo_account_id": "ABC123",
  "has_klaviyo_key": true,
  "klaviyo_key_preview": "pk_***",

  "client_voice": "Friendly, family-oriented Italian style",
  "client_background": "Established 1993...",

  "asana_project_link": "https://app.asana.com/0/123456789",

  "affinity_segment_1_name": "VIP Customers",
  "affinity_segment_1_definition": "Customers who have spent > $500",
  "affinity_segment_2_name": "Recent Visitors",
  "affinity_segment_2_definition": "Visited in last 30 days",
  "affinity_segment_3_name": "Email Subscribers",
  "affinity_segment_3_definition": "Subscribed to email list",

  "key_growth_objective": "subscriptions",
  "timezone": "America/Los_Angeles",

  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T10:00:00",
  "created_by": "admin@emailpilot.ai",
  "updated_by": "admin@emailpilot.ai",

  "goals_count": 5,
  "performance_records": 12
}
```

### 3. Create New Client

**Endpoint**: `POST /api/admin/clients`

**Request Body**:
```json
{
  "name": "New Restaurant",
  "description": "Fine dining establishment",
  "contact_email": "marketing@newrestaurant.com",
  "contact_name": "Jane Smith",
  "website": "https://newrestaurant.com",
  "is_active": true,

  "klaviyo_api_key": "pk_1234567890abcdef",
  "metric_id": "metric-id-here",
  "klaviyo_account_id": "XYZ789",

  "client_voice": "Upscale, sophisticated tone",
  "client_background": "Founded in 2020...",

  "asana_project_link": "https://app.asana.com/0/987654321",

  "affinity_segment_1_name": "Premium Members",
  "affinity_segment_1_definition": "Membership tier: Gold or Platinum",

  "key_growth_objective": "subscriptions",
  "timezone": "America/New_York"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Client created successfully",
  "client_id": "new-client-id",
  "client_name": "New Restaurant",
  "client_slug": "new-restaurant"
}
```

**Notes**:
- `client_slug` is auto-generated from the name
- Klaviyo API key is stored securely in Google Secret Manager
- API key is NEVER returned in responses (only `has_klaviyo_key` boolean and masked preview)

### 4. Update Client

**Endpoint**: `PUT /api/admin/clients/{client_id}`

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "contact_email": "newemail@example.com",
  "is_active": false,
  "klaviyo_api_key": "pk_new_key_here",
  "client_voice": "Updated voice",
  "timezone": "America/Chicago"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Client updated successfully",
  "client_id": "client-id-123",
  "updated_fields": ["name", "description", "timezone"]
}
```

**Notes**:
- Only provide fields you want to update
- If `name` is updated, `client_slug` is automatically regenerated
- To remove Klaviyo API key, set `klaviyo_api_key: ""`

### 5. Delete/Deactivate Client

**Endpoint**: `DELETE /api/admin/clients/{client_id}`

**Response**:
```json
{
  "status": "success",
  "message": "Client 'Buca di Beppo' has been deactivated",
  "client_id": "client-id-123"
}
```

**Notes**:
- This is a soft delete (sets `is_active: false`)
- Client data is preserved in Firestore
- Deactivated clients won't appear in calendar client list (if `active_only=true`)

---

## Additional Admin Endpoints

### Test Klaviyo Connection

**Endpoint**: `POST /api/admin/clients/{client_id}/test-klaviyo`

**Purpose**: Verify that the client's Klaviyo API key works

**Response (Success)**:
```json
{
  "status": "success",
  "message": "Klaviyo connection successful",
  "client_id": "client-id-123",
  "accounts": 1
}
```

**Response (Error)**:
```json
{
  "status": "error",
  "message": "No Klaviyo API key configured for this client",
  "client_id": "client-id-123"
}
```

### Migrate Legacy API Keys

**Endpoint**: `POST /api/admin/clients/migrate-keys`

**Purpose**: Migrate old plaintext Klaviyo keys to Secret Manager

**Response**:
```json
{
  "status": "success",
  "message": "Migration completed. 3 clients migrated, 0 errors",
  "migrated": [
    {"client_id": "client-1", "client_name": "Client A"},
    {"client_id": "client-2", "client_name": "Client B"}
  ],
  "errors": []
}
```

---

## Client Data Structure

### Firestore Collection

**Collection**: `clients`
**Document ID**: Auto-generated Firebase ID

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Client name |
| `client_slug` | string | Auto | URL-safe slug (auto-generated from name) |
| `description` | string | | Client description |
| `contact_email` | string | | Primary contact email |
| `contact_name` | string | | Primary contact name |
| `website` | string | | Client website URL |
| `is_active` | boolean | ✅ | Active status (default: true) |
| `metric_id` | string | | Klaviyo metric ID for tracking |
| `klaviyo_account_id` | string | | Klaviyo account identifier |
| `has_klaviyo_key` | boolean | | Whether API key is stored |
| `client_voice` | string | | Brand voice description |
| `client_background` | string | | Client background/history |
| `asana_project_link` | string | | Asana project URL |
| `affinity_segment_N_name` | string | | Segment name (N = 1, 2, 3) |
| `affinity_segment_N_definition` | string | | Segment definition (N = 1, 2, 3) |
| `key_growth_objective` | string | | Growth objective (default: "subscriptions") |
| `timezone` | string | | Client timezone (default: "UTC") |
| `created_at` | string | Auto | ISO timestamp |
| `updated_at` | string | Auto | ISO timestamp |
| `created_by` | string | Auto | User email |
| `updated_by` | string | Auto | User email |

### Secret Manager

**Klaviyo API Keys** are stored in Google Cloud Secret Manager with naming convention:
- `klaviyo-api-{client_slug}` (new convention)
- `klaviyo-api-key-{client_id}` (legacy)

---

## Example: Adding a Client via Calendar UI

The calendar's `addNewClient()` function currently shows a "coming soon" toast. To implement it:

```javascript
async function addNewClient() {
    const name = prompt('Enter client name:');
    if (!name) return;

    try {
        const response = await fetch('/api/admin/clients', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                is_active: true
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            showToast(`✅ Client "${result.client_name}" created!`);
            // Reload clients list
            await calendarManager.loadClients();
        } else {
            showToast(`❌ Error: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Failed to create client:', error);
        showToast('❌ Failed to create client', 'error');
    }
}
```

---

## Example: Editing a Client

To add edit functionality to the calendar:

```javascript
async function editClient(clientId) {
    // Get current client data
    const response = await fetch(`/api/admin/clients/${clientId}`);
    const client = await response.json();

    // Show edit form (implement your UI)
    const newName = prompt('Edit client name:', client.name);
    if (!newName || newName === client.name) return;

    try {
        const updateResponse = await fetch(`/api/admin/clients/${clientId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });

        const result = await updateResponse.json();

        if (result.status === 'success') {
            showToast(`✅ Client updated!`);
            await calendarManager.loadClients();
        } else {
            showToast(`❌ Error: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('Failed to update client:', error);
        showToast('❌ Failed to update client', 'error');
    }
}
```

---

## Testing the Endpoints

### Using curl

```bash
# List all clients (public)
curl http://localhost:8000/api/clients/

# Get client details (admin)
curl http://localhost:8000/api/admin/clients/{client-id}

# Create client (admin)
curl -X POST http://localhost:8000/api/admin/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "description": "Test description"
  }'

# Update client (admin)
curl -X PUT http://localhost:8000/api/admin/clients/{client-id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name"
  }'

# Delete client (admin)
curl -X DELETE http://localhost:8000/api/admin/clients/{client-id}
```

### Using the browser console

```javascript
// Test public endpoint
fetch('/api/clients/').then(r => r.json()).then(console.log)

// Test admin endpoint
fetch('/api/admin/clients').then(r => r.json()).then(console.log)
```

---

## Status & Changes

### What was fixed (2025-11-15):

1. ✅ **Registered public clients endpoint**
   - File: `main_firestore.py:142` - Added import
   - File: `main_firestore.py:883` - Registered router at `/api/clients`
   - Calendar can now load clients via `/api/clients/`

2. ✅ **Admin endpoints already existed**
   - File: `app/api/admin_clients.py` - Full CRUD operations
   - Properly registered at `/api/admin/clients`

### What still needs work:

1. ⏳ **Calendar Add Client UI** - Replace toast with actual form
   - File: `calendar_master.html` - Implement `addNewClient()` function
   - Currently shows: `showToast('Add client feature coming soon!', 'info');`

2. ⏳ **Calendar Edit Client UI** - Create edit functionality
   - No edit function exists yet
   - Could add to client selection modal or Quick Actions menu

---

## Next Steps

To complete client management in the calendar:

1. **Add Client Form**:
   - Create a modal similar to `clientModal`
   - Form fields: name, description, contact email
   - Submit to `POST /api/admin/clients`
   - Reload client list on success

2. **Edit Client Button**:
   - Add "Edit Client" to Quick Actions (when client selected)
   - Fetch current data from `GET /api/admin/clients/{id}`
   - Show pre-filled form
   - Submit to `PUT /api/admin/clients/{id}`

3. **Delete Client**:
   - Add confirmation dialog
   - Call `DELETE /api/admin/clients/{id}`
   - Redirect to client selection if current client deleted

---

## File References

- **Public API**: `/app/api/clients_public.py`
- **Admin API**: `/app/api/admin_clients.py`
- **Router Registration**: `/main_firestore.py:142, 883`
- **Calendar Client Loading**: `/frontend/public/calendar_master.html:5138-5188`
- **Calendar Add Client Stub**: `/frontend/public/calendar_master.html` (search for `addNewClient`)

---

## Security Notes

- Klaviyo API keys are NEVER stored in Firestore documents
- Keys are stored in Google Cloud Secret Manager
- Admin endpoints should require authentication in production
- Public `/api/clients/` endpoint has no auth (needed for calendar loading)
- Always use HTTPS in production
- Validate and sanitize all input data

---

**Last Updated**: November 15, 2025
**Status**: Public endpoint registered ✅ | Add/Edit UI pending ⏳
