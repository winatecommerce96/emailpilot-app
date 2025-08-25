# Frontend Team Handoff - Calendar Integration

## 🚨 IMPORTANT: Working Reference Available

Due to frontend issues, we've created a **fully functional static HTML page** that demonstrates ALL calendar endpoints working correctly.

### Access the Reference Implementation:
```
http://localhost:8000/static/calendar_static_reference.html
```

This page:
- ✅ Uses the EXACT SAME endpoints your React code should use
- ✅ Shows request/response formats
- ✅ Includes console logging for debugging
- ✅ Has working examples of all 6 calendar endpoints
- ✅ Is tested and verified working

---

## Quick Start for Frontend Team

### 1. Open the Static Reference Page
```bash
# Make sure server is running
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Open in browser
open http://localhost:8000/static/calendar_static_reference.html
```

### 2. Test Each Endpoint
Click the buttons in order:
1. **Build Calendar** - Creates a new calendar
2. **Check Status** - Shows build progress
3. **Start Stream** - Real-time updates via SSE
4. **Get Orchestrator Events** - Fetches generated events
5. **Get Legacy Events** - Alternative endpoint format
6. **Get Clients** - Lists available clients

### 3. Check Browser Console
Open DevTools to see:
- Exact request URLs
- Request/response payloads
- Field mappings
- Timing information

---

## Key Endpoints You Need

### Primary Flow:
```javascript
// 1. Build Calendar
POST /api/calendar/build
Body: {
    client_display_name: "Shop Name",
    client_firestore_id: "shop_123",
    klaviyo_account_id: "klav_456",
    target_month: 12,
    target_year: 2025,
    dry_run: false
}

// 2. Stream Progress (SSE)
GET /api/calendar/build/stream/{correlation_id}

// 3. Fetch Events (NEW FORMAT)
GET /api/calendar/events/{client_id}?year=2025&month=12
```

---

## Critical Field Mappings

The orchestrator uses DIFFERENT field names than legacy:

```javascript
// Orchestrator Event → UI Event
{
    event_id        → id
    campaign_name   → title
    planned_send_datetime → date
    channel        → channel (determines color)
    content_brief  → content
    client_firestore_id → clientId
}
```

---

## Working Code Example

Copy this directly from the static page (it's tested and working):

```javascript
async function buildAndFetchCalendar() {
    // Step 1: Build
    const buildRes = await fetch('/api/calendar/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_display_name: 'Demo Shop',
            client_firestore_id: 'demo_123',
            klaviyo_account_id: 'klav_456',
            target_month: 12,
            target_year: 2025,
            dry_run: false
        })
    });
    
    const { correlation_id } = await buildRes.json();
    
    // Step 2: Stream Progress
    const eventSource = new EventSource(`/api/calendar/build/stream/${correlation_id}`);
    
    await new Promise((resolve) => {
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(`Progress: ${data.progress}%`);
            
            if (data.status === 'completed') {
                eventSource.close();
                resolve();
            }
        };
    });
    
    // Step 3: Fetch Events
    const eventsRes = await fetch('/api/calendar/events/demo_123?year=2025&month=12');
    const eventsData = await eventsRes.json();
    
    if (eventsData.events) {
        // Transform for UI
        return eventsData.events.map(e => ({
            id: e.event_id,
            title: e.campaign_name,
            date: e.planned_send_datetime,
            color: e.channel === 'sms' ? 'orange' : 'blue'
        }));
    }
}
```

---

## Debugging Checklist

If your React code isn't working:

1. **Compare with static page requests:**
   - Open static page
   - Open your React app
   - Compare Network tab requests
   - Check URL differences
   - Check payload differences

2. **Common issues:**
   - Wrong endpoint URL (missing /api prefix?)
   - Wrong field names (client_id vs client_firestore_id)
   - Not waiting for completion before fetching
   - Not transforming orchestrator fields to UI fields
   - Missing auto-refresh after build

3. **Required transformations:**
   ```javascript
   // You MUST transform orchestrator events
   orchestratorEvent.campaign_name → uiEvent.title
   orchestratorEvent.planned_send_datetime → uiEvent.date
   orchestratorEvent.event_id → uiEvent.id
   ```

---

## Files to Reference

1. **Static Test Page** (WORKING):
   ```
   frontend/public/calendar_static_reference.html
   ```

2. **React Component** (needs fixes):
   ```
   frontend/public/components/CalendarAutomated.js
   ```

3. **API Documentation**:
   ```
   CALENDAR_ENDPOINTS_REFERENCE.md
   ```

---

## Support

The static page is your source of truth. If something doesn't work in React but works in the static page, the issue is in the React implementation, not the backend.

**To verify backend is working:**
```bash
python test_static_endpoints.py
# Should show all endpoints ✅
```

**Static page shows:**
- ✅ All 6 endpoints working
- ✅ Correct request/response formats
- ✅ Field mappings
- ✅ Console logging patterns

Use this reference to fix the React implementation. The backend is ready and tested.