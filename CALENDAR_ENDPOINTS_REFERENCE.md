# Calendar API Endpoints Reference

## Complete Endpoint Documentation for Frontend Team

### Base URL
```
http://localhost:8000
```

---

## 1. Build Calendar (Orchestrator)
**Endpoint:** `POST /api/calendar/build`

**Purpose:** Triggers LangChain orchestrator to generate a calendar using AI and historical data

**Request Body:**
```json
{
  "client_display_name": "Demo Cheese Shop",
  "client_firestore_id": "demo_cheese_123",
  "klaviyo_account_id": "test_klav_456",
  "target_month": 12,
  "target_year": 2025,
  "dry_run": false
}
```

**Response:**
```json
{
  "correlation_id": "91733b5d-d9d3-4902-b1e0-310a24ee40a7",
  "status": "started",
  "message": "Calendar build initiated"
}
```

**Frontend Usage:**
```javascript
const response = await fetch('/api/calendar/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        client_display_name: selectedClient.name,
        client_firestore_id: selectedClient.id,
        klaviyo_account_id: selectedClient.klaviyo_account_id,
        target_month: 12,
        target_year: 2025,
        dry_run: false
    })
});
const { correlation_id } = await response.json();
```

---

## 2. Check Build Status
**Endpoint:** `GET /api/calendar/build/status/{correlation_id}`

**Purpose:** Check the progress of a calendar build operation

**Response:**
```json
{
  "correlation_id": "91733b5d-d9d3-4902-b1e0-310a24ee40a7",
  "status": "in_progress",
  "progress": 75.0,
  "current_step": "calendar_building",
  "message": "Generating calendar events using AI strategy",
  "started_at": "2025-08-21T10:00:00Z",
  "updated_at": "2025-08-21T10:01:30Z"
}
```

**Status Values:**
- `started` - Build initiated
- `in_progress` - Build running
- `completed` - Build successful
- `failed` - Build failed

**Frontend Usage:**
```javascript
const pollStatus = async (correlationId) => {
    const response = await fetch(`/api/calendar/build/status/${correlationId}`);
    const status = await response.json();
    
    if (status.status === 'completed') {
        // Refresh calendar events
        await fetchEvents();
    } else if (status.status === 'failed') {
        // Show error
        console.error('Build failed:', status.message);
    } else {
        // Update progress bar
        updateProgressBar(status.progress);
        // Continue polling
        setTimeout(() => pollStatus(correlationId), 1000);
    }
};
```

---

## 3. Stream Build Progress (Server-Sent Events)
**Endpoint:** `GET /api/calendar/build/stream/{correlation_id}`

**Purpose:** Real-time progress updates via Server-Sent Events

**Response:** SSE Stream
```
data: {"status":"in_progress","progress":10,"current_step":"mcp_selection","message":"Selecting MCP service"}
data: {"status":"in_progress","progress":40,"current_step":"feature_engineering","message":"Analyzing campaign features"}
data: {"status":"completed","progress":100,"message":"Calendar automation complete. Generated 25 events."}
```

**Frontend Usage:**
```javascript
const eventSource = new EventSource(`/api/calendar/build/stream/${correlationId}`);

eventSource.onmessage = (event) => {
    const update = JSON.parse(event.data);
    updateProgressBar(update.progress);
    
    if (update.status === 'completed') {
        eventSource.close();
        await fetchEvents(); // Refresh calendar
    }
};

eventSource.onerror = () => {
    eventSource.close();
};
```

---

## 4. Get Orchestrator Events (NEW - Preferred)
**Endpoint:** `GET /api/calendar/events/{client_id}?year={year}&month={month}`

**Purpose:** Fetch orchestrator-generated calendar events

**Parameters:**
- `client_id` - Firestore client ID (e.g., "demo_cheese_123")
- `year` - Target year (e.g., 2025)
- `month` - Target month (1-12)
- `version` (optional) - Specific version number

**Response:**
```json
{
  "events": [
    {
      "event_id": "demo_cheese_123_202512_event_001",
      "campaign_name": "Cheese Club Welcome Series",
      "planned_send_datetime": "2025-12-01T10:00:00",
      "channel": "email",
      "theme": "nurturing",
      "content_brief": "Welcome new cheese club members with exclusive offers",
      "expected_kpi_band": "medium",
      "client_firestore_id": "demo_cheese_123",
      "calendar_id": "demo_cheese_123_202512",
      "version": 1,
      "latest": true
    }
  ],
  "calendar_id": "demo_cheese_123_202512",
  "version": 1,
  "correlation_id": "91733b5d-d9d3-4902-b1e0-310a24ee40a7",
  "import_log": {
    "completed_at": "2025-08-21T10:02:00Z",
    "stats_summary": {
      "total_historical_campaigns": 45,
      "generated_events": 25
    }
  },
  "total_events": 25
}
```

**Field Mappings for UI:**
```javascript
// Transform orchestrator fields to UI fields
const transformEvent = (orchestratorEvent) => ({
    id: orchestratorEvent.event_id,
    title: orchestratorEvent.campaign_name,
    date: orchestratorEvent.planned_send_datetime,
    channel: orchestratorEvent.channel,
    color: orchestratorEvent.channel === 'sms' ? 'bg-orange-200' : 'bg-blue-200',
    theme: orchestratorEvent.theme,
    kpiBand: orchestratorEvent.expected_kpi_band,
    content: orchestratorEvent.content_brief
});
```

---

## 5. Get Legacy Events (Backward Compatibility)
**Endpoint:** `GET /api/calendar/events/{client_id}?start_date={start}&end_date={end}`

**Purpose:** Fetch events using date range (legacy format)

**Parameters:**
- `client_id` - Client ID
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)

**Response:**
```json
[
  {
    "id": "abc123",
    "title": "Campaign Name",
    "date": "2025-12-01T10:00:00",
    "client_id": "demo_cheese_123",
    "color": "bg-blue-200 text-blue-800",
    "content": "Campaign content"
  }
]
```

---

## 6. Get Calendar Clients
**Endpoint:** `GET /api/calendar/clients?active_only=true`

**Purpose:** Fetch list of available clients

**Response:**
```json
[
  {
    "id": "demo_cheese_123",
    "name": "Demo Cheese Shop",
    "email": "demo@cheese.com",
    "klaviyo_account_id": "test_klav_456",
    "active": true,
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

---

## 7. Get Specific Client
**Endpoint:** `GET /api/calendar/clients/{client_id}`

**Purpose:** Fetch details for a specific client

**Response:**
```json
{
  "id": "demo_cheese_123",
  "name": "Demo Cheese Shop",
  "email": "demo@cheese.com",
  "klaviyo_account_id": "test_klav_456",
  "settings": {
    "send_cap_per_day": 2,
    "preferred_send_times": [10, 14, 16]
  }
}
```

---

## Complete Frontend Integration Example

```javascript
// Complete flow for calendar automation
class CalendarAutomation {
    constructor() {
        this.correlationId = null;
        this.clientId = 'demo_cheese_123';
    }

    async buildCalendar() {
        // Step 1: Trigger build
        const buildResponse = await fetch('/api/calendar/build', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                client_display_name: 'Demo Cheese Shop',
                client_firestore_id: this.clientId,
                klaviyo_account_id: 'test_klav_456',
                target_month: 12,
                target_year: 2025,
                dry_run: false
            })
        });

        const { correlation_id } = await buildResponse.json();
        this.correlationId = correlation_id;

        // Step 2: Stream progress
        await this.streamProgress();

        // Step 3: Fetch events after completion
        await this.fetchEvents();
    }

    async streamProgress() {
        return new Promise((resolve, reject) => {
            const eventSource = new EventSource(
                `/api/calendar/build/stream/${this.correlationId}`
            );

            eventSource.onmessage = (event) => {
                const update = JSON.parse(event.data);
                console.log(`Progress: ${update.progress}% - ${update.message}`);

                if (update.status === 'completed') {
                    eventSource.close();
                    resolve();
                } else if (update.status === 'failed') {
                    eventSource.close();
                    reject(new Error(update.message));
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                reject(new Error('Stream connection failed'));
            };
        });
    }

    async fetchEvents() {
        const response = await fetch(
            `/api/calendar/events/${this.clientId}?year=2025&month=12`
        );

        const data = await response.json();

        if (data.events) {
            // Orchestrator format
            console.log(`Retrieved ${data.events.length} events`);
            console.log(`Version: ${data.version}`);
            console.log(`Correlation ID: ${data.correlation_id}`);

            // Transform for UI
            const uiEvents = data.events.map(event => ({
                id: event.event_id,
                title: event.campaign_name,
                date: event.planned_send_datetime,
                channel: event.channel,
                color: event.channel === 'sms' ? 'orange' : 'blue'
            }));

            return uiEvents;
        }

        return [];
    }
}

// Usage
const automation = new CalendarAutomation();
await automation.buildCalendar();
```

---

## Testing Instructions

1. **Open the static reference page:**
   ```
   http://localhost:8000/static/calendar_static_reference.html
   ```

2. **Test each endpoint in order:**
   - Build Calendar → Get correlation_id
   - Check Status or Stream Progress
   - Get Orchestrator Events
   - Verify events are displayed

3. **Check browser console for:**
   - Request/response details
   - Field mapping examples
   - Timing information

---

## Important Notes for Frontend Team

### ⚠️ Critical Field Differences

**Orchestrator Fields (NEW):**
- `client_firestore_id` (not `client_id`)
- `planned_send_datetime` (not `date`)
- `campaign_name` (not `title`)
- `latest: true` (filter for current version)

**Transform Function:**
```javascript
function transformOrchestratorEvent(event) {
    return {
        id: event.event_id || event.id,
        title: event.campaign_name || event.title,
        date: event.planned_send_datetime || event.date,
        channel: event.channel,
        color: event.channel === 'sms' ? 'bg-orange-200' : 'bg-blue-200',
        clientId: event.client_firestore_id || event.client_id,
        theme: event.theme,
        kpiBand: event.expected_kpi_band,
        content: event.content_brief || event.content
    };
}
```

### 📝 Console Logging

Add these logs for debugging:
```javascript
console.log('calendar: fetching events for client=X, year=Y, month=Z');
console.log('calendar: render: N orchestrator events');
console.log('calendar: build completed, refreshing events...');
```

### 🔄 Auto-Refresh Pattern

```javascript
// After build completion
if (statusUpdate.status === 'completed') {
    console.log('calendar: build completed, refreshing events...');
    await fetchEvents(); // MUST refresh immediately
    showSuccessMessage();
}
```

---

## Support

If endpoints are not working as expected:
1. Check the static reference page - all endpoints are tested there
2. Open browser DevTools Network tab
3. Compare your requests with the reference implementation
4. Check for field name differences (orchestrator vs legacy)
5. Ensure you're filtering by `latest=true` for orchestrator events