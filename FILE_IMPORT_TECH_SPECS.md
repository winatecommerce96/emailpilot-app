# EmailPilot Calendar File Import - Technical Specifications

## Overview
Complete technical specifications for the file import functionality in EmailPilot's Calendar Master interface. This feature allows users to import campaign calendars from external systems supporting JSON, CSV, Excel, and iCalendar formats.

## System Requirements

### Prerequisites
- EmailPilot Calendar Master page loaded (`calendar_master.html`)
- Client selected in calendar interface
- Modern web browser with FileReader API support
- JavaScript enabled

### Dependencies
- Existing calendar manager instance (`calendarManager`)
- Toast notification system (`showToast()`)
- Firestore integration for cloud save functionality

## File Format Specifications

### 1. JSON Format (.json)

#### Supported Structures

**Array Format (Preferred)**
```json
[
  {
    "title": "Summer Sale Launch",
    "date": "2024-06-15",
    "event_type": "promotional",
    "content": "50% off summer collection",
    "segment": "vip_customers",
    "color": "bg-red-300 text-red-800"
  },
  {
    "title": "Newsletter #45",
    "date": "2024-06-20", 
    "event_type": "email",
    "content": "Monthly product updates and tips"
  }
]
```

**Object Format**
```json
{
  "events": [
    // Events array as above
  ],
  "metadata": {
    "client_name": "Fashion Brand",
    "month": "2024-06",
    "total_campaigns": 2
  }
}
```

**Alternative Object Format**
```json
{
  "calendar": [
    // Events array as above
  ]
}
```

#### Required Fields
- `title` (string): Campaign name
- `date` (string): ISO date format YYYY-MM-DD

#### Optional Fields
- `event_type` (string): Campaign type (email, sms, promotional, etc.)
- `content` (string): Campaign description
- `segment` (string): Target audience segment
- `color` (string): TailwindCSS color class
- `send_time` (string): Preferred send time
- `subject_a` (string): A/B test subject line A
- `subject_b` (string): A/B test subject line B
- `offer` (string): Promotional offer details

### 2. CSV Format (.csv)

#### Structure Requirements
```csv
Campaign Name,Launch Date,Type,Description,Target Segment,Send Time
Summer Sale Launch,2024-06-15,promotional,50% off summer collection,vip_customers,10:00 AM
Newsletter #45,2024-06-20,email,Monthly product updates and tips,all_subscribers,2:00 PM
Flash Sale Alert,2024-06-22,sms,24-hour flash sale notification,engaged_users,11:00 AM
```

#### Column Mapping
System auto-detects common column names:
- **Title**: "Campaign Name", "Title", "Name", "Campaign"
- **Date**: "Launch Date", "Date", "Start Date", "Schedule Date", "Time"
- **Type**: "Type", "Campaign Type", "Category", "Kind"
- **Content**: "Description", "Content", "Notes", "Details"

#### Manual Column Mapping
Interface provides dropdowns to manually map columns:
- Title Column (required)
- Date Column (required) 
- Campaign Type Column (optional)
- Description Column (optional)

### 3. Excel Format (.xlsx, .xls)

#### Processing Method
- Reads as text and processes like CSV
- First row treated as headers
- Same column mapping logic as CSV
- Supports both .xlsx and .xls extensions

#### Limitations
- Only processes first worksheet
- Complex formatting ignored
- Formulas converted to values

### 4. iCalendar Format (.ics)

#### Supported Properties
```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp//CalDAV Client//EN
BEGIN:VEVENT
UID:campaign-001@example.com
DTSTART:20240615T140000Z
SUMMARY:Summer Sale Launch
DESCRIPTION:50% off summer collection targeting VIP customers
END:VEVENT
END:VCALENDAR
```

#### Mapped Fields
- `SUMMARY` → title
- `DTSTART` → date (converts from iCal format)
- `DESCRIPTION` → content
- All events default to `event_type: "email"`

## User Interface Specifications

### Import Button
- **Location**: Main header navigation bar
- **HTML**: `<button onclick="openFileImportModal()" class="glow-button">`
- **Icon**: 📄 document emoji
- **Text**: "Import File"
- **Requirement**: Client must be selected

### File Import Modal

#### Modal Structure
```html
<div id="fileImportModal" class="modal-backdrop">
  <div class="modal-content">
    <!-- File type selector -->
    <!-- File upload area -->
    <!-- Column mapping (CSV/Excel) -->
    <!-- File preview -->
    <!-- Action buttons -->
  </div>
</div>
```

#### File Type Selector
```html
<select id="fileType" onchange="updateFileInputAccept()">
  <option value="json">JSON (EmailPilot Format)</option>
  <option value="csv">CSV (Spreadsheet)</option>
  <option value="xlsx">Excel (.xlsx)</option>
  <option value="ics">iCalendar (.ics)</option>
</select>
```

#### File Upload Area
- **Drag-and-Drop**: Visual feedback with hover states
- **Click to Browse**: Opens native file picker
- **Visual States**:
  - Default: Dashed border, upload icon
  - Hover: Highlighted border, subtle scale
  - Dragover: Bright border, background color change

#### Column Mapping (CSV/Excel only)
```html
<div id="csvPreview" class="hidden">
  <select id="titleColumn"><!-- Auto-populated --></select>
  <select id="dateColumn"><!-- Auto-populated --></select>
  <select id="typeColumn"><!-- Auto-populated --></select>
  <select id="contentColumn"><!-- Auto-populated --></select>
</div>
```

## JavaScript API Specifications

### Core Functions

#### `openFileImportModal()`
```javascript
function openFileImportModal() {
  // Validates client selection
  // Shows modal with fade-in animation
  // Resets form state
}
```

#### `handleFileSelect(event)`
```javascript
function handleFileSelect(event) {
  // Processes file selection
  // Updates UI with file info
  // Triggers file preview
  // Enables import button
}
```

#### `processFileImport()`
```javascript
async function processFileImport() {
  // Main import orchestrator
  // Handles all file types
  // Shows loading states
  // Processes events and adds to calendar
  // Shows success/error notifications
}
```

### File Parsing Functions

#### `parseJsonFile(content)`
```javascript
async function parseJsonFile(content) {
  // Parses JSON string
  // Handles multiple structure formats
  // Returns normalized event array
  // Throws descriptive errors
}
```

#### `parseCsvFile(content)`
```javascript
async function parseCsvFile(content) {
  // Splits CSV into lines and cells
  // Uses column mapping selections
  // Validates required fields
  // Returns normalized event array
}
```

#### `parseIcsFile(content)`
```javascript
async function parseIcsFile(content) {
  // Parses iCalendar format
  // Extracts VEVENT blocks
  // Converts date formats
  // Returns normalized event array
}
```

#### `normalizeEventData(event)`
```javascript
function normalizeEventData(event) {
  // Standardizes event object structure
  // Handles date format conversion
  // Assigns default values
  // Generates unique IDs
  // Returns calendar-compatible event
}
```

## Data Flow Specifications

### Import Process Flow
1. **User Action**: Click "Import File" button
2. **Validation**: Check if client selected
3. **Modal Display**: Show file import interface
4. **File Selection**: User selects file (drag/drop or click)
5. **File Preview**: Parse and display file content
6. **Column Mapping**: For CSV/Excel, show mapping interface
7. **Import Processing**: Parse file and normalize data
8. **Calendar Integration**: Add events to calendar manager
9. **Cloud Sync**: Save to Firestore
10. **UI Update**: Refresh calendar display and stats
11. **User Feedback**: Show success notification

### Error Handling Flow
1. **File Validation**: Check file type and size
2. **Parse Errors**: Catch JSON/CSV parsing errors
3. **Data Validation**: Validate required fields
4. **User Notification**: Show specific error messages
5. **State Restoration**: Reset UI to allow retry

## Event Data Normalization

### Input Event Object (Various Formats)
```javascript
// JSON input
{ title: "Campaign", date: "2024-06-15", event_type: "email" }

// CSV input  
{ title: "Campaign", date: "06/15/2024", type: "Newsletter" }

// iCal input
{ summary: "Campaign", dtstart: "20240615T140000Z", description: "..." }
```

### Normalized Calendar Event
```javascript
{
  id: "imported-1707123456789-abc123def",
  name: "Campaign Name",
  type: "email",
  date: new Date("2024-06-15T00:00:00.000Z"),
  description: "Campaign description",
  color: "bg-blue-200 text-blue-800",
  segment: "",
  imported: true
}
```

### Color Assignment Logic
```javascript
const colorMap = {
  'email': 'bg-blue-200 text-blue-800',
  'sms': 'bg-orange-200 text-orange-800',
  'flash sale': 'bg-red-300 text-red-800',
  'promotional': 'bg-red-300 text-red-800',
  'nurturing': 'bg-green-100 text-green-800',
  'cheese club': 'bg-green-200 text-green-800',
  'rrb': 'bg-red-300 text-red-800',
  'seasonal': 'bg-purple-200 text-purple-800'
};
```

## Channel Filtering Specifications

### Overview
The calendar interface provides Email and SMS channel filter pills that allow users to view campaigns by communication channel. These filters work alongside affinity segment filters to provide flexible campaign visibility.

### Channel Field in Imported Events

#### Field Specification
- **Field Name**: `channel` (optional)
- **Valid Values**: `"email"`, `"sms"`
- **Default Behavior**: If no channel is specified, the system uses the `type` or `event_type` field to infer the channel

#### Channel Detection Logic
```javascript
// Priority order for determining channel:
1. Explicit channel field: event.channel
2. Type field inference: event.type or event.event_type
   - "email" → email channel
   - "sms" → sms channel
   - Other types → defaults to email channel
```

#### Import Examples

**JSON with Explicit Channel**
```json
[
  {
    "title": "Summer Sale Email",
    "date": "2024-06-15",
    "channel": "email",
    "content": "Email campaign for summer sale"
  },
  {
    "title": "Flash Sale Alert",
    "date": "2024-06-16",
    "channel": "sms",
    "content": "SMS notification for 24hr flash sale"
  }
]
```

**CSV with Channel Column**
```csv
Campaign Name,Launch Date,Channel,Description
Summer Sale Email,2024-06-15,email,Email campaign for summer sale
Flash Sale Alert,2024-06-16,sms,SMS notification for 24hr flash sale
```

**Inferred from Type Field**
```json
[
  {
    "title": "Newsletter #45",
    "date": "2024-06-20",
    "type": "email",
    "content": "Monthly updates"
  },
  {
    "title": "Urgent Alert",
    "date": "2024-06-21",
    "type": "sms",
    "content": "Limited time offer"
  }
]
```

### Filter Pills UI

#### Email Filter Pill
```html
<div class="glass-card p-3 flex-1 min-w-[140px] cursor-pointer hover:ring-2 hover:ring-purple-500 transition-all"
     onclick="calendarManager.toggleChannelFilter('email')"
     title="Filter by Email campaigns">
    <div class="flex items-center justify-center gap-2">
        <span class="text-xs font-semibold">📧 Email</span>
    </div>
</div>
```

**Active State**: `ring-2 ring-purple-500 bg-purple-500/20`

#### SMS Filter Pill
```html
<div class="glass-card p-3 flex-1 min-w-[140px] cursor-pointer hover:ring-2 hover:ring-purple-500 transition-all"
     onclick="calendarManager.toggleChannelFilter('sms')"
     title="Filter by SMS campaigns">
    <div class="flex items-center justify-center gap-2">
        <span class="text-xs font-semibold">📱 SMS</span>
    </div>
</div>
```

**Active State**: `ring-2 ring-purple-500 bg-purple-500/20`

#### Visual Location
- Displayed in the segments display area
- Positioned before affinity segment pills
- Always visible when a client is selected

### Filter Toggle Behavior

#### JavaScript API
```javascript
toggleChannelFilter(channel) {
    const idx = this.activeFilters.channels.indexOf(channel);
    if (idx === -1) {
        // Clear segment filters when filtering by channel
        this.activeFilters.segments = [];
        this.activeFilters.channels = [channel]; // Only one channel at a time
    } else {
        this.activeFilters.channels.splice(idx, 1);
    }
    this.renderCalendar();
    this.updateSegmentDisplay();
    const channelName = channel === 'email' ? 'Email' : 'SMS';
    showToast(`${idx === -1 ? 'Showing only' : 'Showing all'} ${channelName} campaigns`, 'info');
}
```

#### Filter Rules
1. **Mutual Exclusivity**: Only one channel can be filtered at a time
   - Clicking "Email" when "SMS" is active switches to Email filter
   - Clicking "SMS" when "Email" is active switches to SMS filter

2. **Segment Filter Clearing**: Activating a channel filter clears all active segment filters
   - Channel filters and segment filters cannot be active simultaneously
   - This prevents confusion and provides clear filtering state

3. **Toggle Behavior**: Clicking an active channel filter removes it
   - Shows all campaigns regardless of channel
   - Re-enables segment filtering capability

4. **Visual Feedback**: Toast notifications confirm filter state changes
   - "Showing only Email campaigns" when Email filter activated
   - "Showing only SMS campaigns" when SMS filter activated
   - "Showing all Email campaigns" / "Showing all SMS campaigns" when filter removed

### Filter State Management

#### Active Filter Structure
```javascript
this.activeFilters = {
    channels: [],   // Array with 0 or 1 channel: ['email'] or ['sms'] or []
    segments: []    // Array with segment names, empty when channel filter active
};
```

#### State Combinations
```javascript
// No filters active
{ channels: [], segments: [] }
// Shows: All campaigns

// Email filter active
{ channels: ['email'], segments: [] }
// Shows: Only email campaigns

// SMS filter active
{ channels: ['sms'], segments: [] }
// Shows: Only SMS campaigns

// Segment filter active (channel must be empty)
{ channels: [], segments: ['VIP Customers'] }
// Shows: Only campaigns targeting VIP Customers segment

// Invalid state (prevented by toggle logic)
{ channels: ['email'], segments: ['VIP Customers'] }
// System prevents this - activating channel clears segments
```

### Integration with Import Process

#### Automatic Channel Assignment
During import, if no explicit `channel` field is provided:

1. **Check event type**: Look for `type` or `event_type` field
2. **Match patterns**:
   - Contains "email" → assign `channel: "email"`
   - Contains "sms" → assign `channel: "sms"`
   - Matches color map keys → assign channel based on type
3. **Default fallback**: If no match found, default to `channel: "email"`

#### Post-Import Filtering
After events are imported:
- Channel filter pills remain available
- Users can immediately filter imported campaigns by channel
- Filter state persists during navigation within same client
- Filter state resets when switching clients

### User Workflow Examples

#### Example 1: Email-Only Review
1. User imports mixed Email and SMS campaigns
2. User clicks "📧 Email" pill
3. Calendar shows only email campaigns
4. User reviews email campaign schedule
5. User clicks "📧 Email" pill again to see all campaigns

#### Example 2: SMS Campaign Planning
1. User clicks "📱 SMS" pill
2. Calendar shows only SMS campaigns
3. User identifies gaps in SMS schedule
4. User creates new SMS campaign on empty date
5. User clicks "📱 SMS" pill to deactivate and view full calendar

#### Example 3: Switching Between Filters
1. User has "VIP Customers" segment filter active
2. User clicks "📧 Email" pill
3. Segment filter automatically clears
4. Calendar shows all email campaigns (not just VIP)
5. User clicks "📧 Email" pill to deactivate
6. User can now reactivate segment filter if desired

### Testing Specifications

#### Channel Filter Tests
1. **Single Channel Activation**: Verify only matching campaigns display
2. **Channel Toggle**: Verify clicking active filter removes it
3. **Mutual Exclusivity**: Verify only one channel active at a time
4. **Segment Clearing**: Verify channel activation clears segment filters
5. **Visual State**: Verify active state styling applies correctly
6. **Toast Notifications**: Verify appropriate messages display

#### Import Integration Tests
1. **Explicit Channel Field**: Import with `channel` field, verify filtering works
2. **Inferred Channel**: Import with `type` field, verify channel inference
3. **Mixed Channels**: Import both email/sms, verify both filters work
4. **Default Channel**: Import without channel info, verify defaults to email
5. **Post-Import Filtering**: Verify filters work immediately after import

## CSS Specifications

### File Upload Area Styles
```css
.file-upload-area {
  position: relative;
  border: 2px dashed rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  padding: 40px 20px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.02);
}

.file-upload-area:hover {
  border-color: rgba(197, 255, 117, 0.5);
  background: rgba(197, 255, 117, 0.05);
}

.file-upload-area.dragover {
  border-color: rgba(197, 255, 117, 0.8);
  background: rgba(197, 255, 117, 0.1);
  transform: scale(1.02);
}
```

### Light Mode Overrides
```css
body.light-mode .file-upload-area {
  border-color: rgba(0, 0, 0, 0.2);
  background: rgba(0, 0, 0, 0.02);
}

body.light-mode .file-upload-area:hover {
  border-color: rgba(51, 105, 220, 0.5);
  background: rgba(51, 105, 220, 0.05);
}
```

## Integration Specifications

### Calendar Manager Integration
```javascript
// Add events to existing calendar
events.forEach(event => {
  calendarManager.campaigns.push(event);
});

// Trigger calendar refresh
calendarManager.renderCalendar();
calendarManager.updateStats();

// Enable undo functionality
calendarManager.saveState();
```

### Firestore Integration
```javascript
// Auto-save imported events
await calendarManager.saveToCloud();
```

### Toast Notification Integration
```javascript
// Success notification
showToast(`Successfully imported ${events.length} events`, 'success');

// Error notification  
showToast('Error importing file: ' + error.message, 'error');

// Warning notification
showToast('Please select a client first', 'warning');
```

## Testing Specifications

### Unit Test Cases

#### File Parsing Tests
1. **JSON Array Format**: Valid event array
2. **JSON Object Format**: Events nested in object
3. **CSV Parsing**: Standard comma-separated format
4. **iCalendar Parsing**: Standard VEVENT format
5. **Invalid JSON**: Malformed JSON structure
6. **Empty Files**: No content or whitespace only
7. **Missing Required Fields**: Events without title/date

#### Date Parsing Tests
1. **ISO Format**: YYYY-MM-DD
2. **US Format**: MM/DD/YYYY
3. **European Format**: DD/MM/YYYY
4. **iCal Format**: YYYYMMDDTHHMMSS
5. **Invalid Dates**: Unparseable date strings

#### UI Interaction Tests
1. **Modal Opening**: Client selection validation
2. **File Type Selection**: Accept attribute updates
3. **Drag and Drop**: Visual feedback states
4. **Column Mapping**: Auto-detection accuracy
5. **Import Button**: Disabled/enabled states

### Integration Test Cases

#### End-to-End Import Flow
1. **Complete JSON Import**: From file selection to calendar display
2. **Complete CSV Import**: Including column mapping
3. **Complete iCal Import**: From calendar export to import
4. **Error Recovery**: Failed import with user retry
5. **Multiple File Types**: Sequential imports of different formats

### Performance Test Cases

#### File Size Limits
1. **Small Files**: < 1KB (1-5 events)
2. **Medium Files**: 1-100KB (50-500 events)  
3. **Large Files**: 100KB-1MB (500+ events)
4. **Memory Usage**: Monitor during large file processing
5. **UI Responsiveness**: No blocking during import

## Browser Compatibility

### Required APIs
- FileReader API (IE10+)
- JSON.parse() (All modern browsers)
- Date parsing (All browsers)
- ES6 Promises (IE11+ or polyfill)

### Tested Browsers
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security Considerations

### File Validation
- File size limits (recommend 5MB max)
- File type validation via extension and MIME type
- Content validation before parsing
- No code execution from file content

### Data Sanitization
- HTML entity encoding for user content
- SQL injection prevention (server-side)
- XSS prevention in displayed content
- Input length limits

## Deployment Specifications

### File Location
- Main implementation: `frontend/public/calendar_master.html`
- No additional server-side components required
- Client-side processing only

### Configuration
- No additional configuration files
- Uses existing calendar manager settings
- Integrates with existing Firestore configuration

### Rollback Plan
- Feature contained within modal interface
- Can be disabled by removing import button
- No database schema changes required
- Existing calendar functionality unaffected

## Future Enhancement Specifications

### Potential Improvements
1. **Excel Formula Support**: Process calculated fields
2. **Bulk Edit**: Modify imported events before adding
3. **Import Templates**: Predefined column mappings
4. **Import History**: Track and reverse previous imports
5. **File Format Detection**: Auto-detect without user selection
6. **Progress Indicators**: For large file processing
7. **Partial Import**: Select specific events from file
8. **Import Scheduling**: Schedule imports for later execution

### API Extensions
1. **Server-Side Processing**: Handle larger files server-side
2. **Webhook Integration**: Auto-import from external systems
3. **Cloud File Import**: Direct import from Google Drive/Dropbox
4. **Real-time Sync**: Live updates from external calendars

This specification provides complete technical requirements for implementing or extending the EmailPilot calendar file import functionality.