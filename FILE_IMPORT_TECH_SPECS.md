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