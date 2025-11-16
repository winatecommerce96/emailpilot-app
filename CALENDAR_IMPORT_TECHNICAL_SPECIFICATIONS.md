# Calendar Master Import Feature - Technical Specifications

## Table of Contents
1. [Overview](#overview)
2. [Import Feature Architecture](#import-feature-architecture)
3. [JSON Import Format Specification](#json-import-format-specification)
4. [Supported File Formats](#supported-file-formats)
5. [API Endpoints](#api-endpoints)
6. [UI Import Workflow](#ui-import-workflow)
7. [Data Mapping & Transformation](#data-mapping--transformation)
8. [Integration Points](#integration-points)
9. [Code Examples](#code-examples)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [Version History](#version-history)

---

## Overview

### What Can Be Imported
The Calendar Master import feature allows bulk uploading of campaign events from external sources into the EmailPilot calendar system. Supported data includes:

- **Email campaigns** with complete metadata (subject lines, preview text, CTAs, etc.)
- **SMS campaigns** with message variants
- **Push notifications** with targeting information
- **Multi-day campaigns** spanning multiple dates
- **A/B testing configurations** for campaign optimization
- **Segment targeting** information
- **Send time optimization** data

### Supported File Formats
- **JSON** (.json) - Primary format with full field support
- **CSV** (.csv) - Tabular data with column mapping
- **Excel** (.xlsx, .xls) - Spreadsheet import with field mapping
- **iCalendar** (.ics) - Calendar file format for basic events

### Use Cases
1. **Bulk Campaign Planning** - Import an entire month's campaign calendar
2. **Migration** - Transfer campaigns from other planning tools
3. **Template Loading** - Import pre-built campaign templates
4. **Multi-Client Onboarding** - Rapidly set up new client calendars
5. **Seasonal Campaign Batches** - Load holiday/seasonal campaign series
6. **External Tool Integration** - Import from Google Sheets, Excel, project management tools

---

## Import Feature Architecture

### System Flow Diagram
```
┌─────────────────┐
│   User Selects  │
│   Client First  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Click Import   │
│     Button      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  File Selection │─────▶│  Format Detected │
│  Modal Opens    │      │  (.json/.csv...)  │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         │◀───────────────────────┘
         ▼
┌─────────────────┐
│  File Preview   │
│   & Validation  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ Parse File Data │─────▶│ Normalize Events │
│                 │      │ Add Emojis/Color │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         │◀───────────────────────┘
         ▼
┌─────────────────┐
│ Add to Calendar │
│   Manager       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Save to Cloud  │─────▶│  Firestore Sync  │
│  (Auto-save)    │      │ calendar_events  │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│ Refresh Calendar│
│  Display & Stats│
└─────────────────┘
```

### Key Components

#### Frontend (JavaScript)
- **Location**: `/frontend/public/calendar_master.js`
- **Functions**:
  - `openFileImportModal()` - Opens import dialog
  - `handleFileSelect()` - Processes file selection
  - `parseJsonFile()` - JSON parsing logic
  - `parseCsvFile()` - CSV parsing with column mapping
  - `parseIcsFile()` - iCalendar format parsing
  - `normalizeEventData()` - Standardizes event format
  - `importEventsToCalendar()` - Adds events to calendar

#### Backend (Python FastAPI)
- **Location**: `/app/api/calendar.py`
- **Endpoints**:
  - `POST /api/calendar/events` - Create single event
  - `POST /api/calendar/create-bulk-events` - Create multiple events
  - `GET /api/calendar/events?client_id={id}` - Retrieve events

#### Database (Firestore)
- **Collection**: `calendar_events`
- **Fields**: See [Data Schema](#firestore-data-schema) section

---

## JSON Import Format Specification

### Basic JSON Structure

The import system accepts three JSON structures:

#### Format 1: Object with `events` property (Recommended)
```json
{
  "events": [
    { "date": "2025-09-01", "title": "Campaign Name", "type": "email" }
  ]
}
```

#### Format 2: Object with `calendar` property
```json
{
  "calendar": [
    { "date": "2025-09-01", "title": "Campaign Name", "type": "email" }
  ]
}
```

#### Format 3: Direct array
```json
[
  { "date": "2025-09-01", "title": "Campaign Name", "type": "email" }
]
```

### Complete Field Specification

| Field Name | Type | Required | Description | Alternatives | Example |
|------------|------|----------|-------------|--------------|---------|
| `date` | string | ✅ Yes | Campaign date (YYYY-MM-DD) | `send_date`, `event_date` | `"2025-09-15"` |
| `title` | string | ✅ Yes | Campaign name/title | `name`, `summary`, `subject_line_a` | `"Fall Sale Launch"` |
| `type` | string | ✅ Yes | Campaign type (see types below) | `event_type`, `category` | `"promotional"` |
| `description` | string | ⬜ No | Campaign description/notes | `content`, `notes` | `"30% off fall collection"` |
| `segment` | string | ⬜ No | Target audience segment | `segments`, `audience` | `"vip_customers"` |
| `week_number` | integer | ⬜ No | Week number in year | - | `36` |
| `send_time` | string | ⬜ No | Send time (HH:MM 24-hour) | - | `"14:30"` |
| `subject_line_a` | string | ⬜ No | Primary subject line | - | `"🎉 Your Fall Sale is Here!"` |
| `subject_line_b` | string | ⬜ No | A/B test subject line | - | `"Exclusive Fall Discount Inside"` |
| `preview_text` | string | ⬜ No | Email preview text | - | `"Shop now for 30% off..."` |
| `hero_h1` | string | ⬜ No | Main headline | - | `"FALL COLLECTION SALE"` |
| `sub_head` | string | ⬜ No | Sub-headline | - | `"Save Big This Season"` |
| `hero_image` | string | ⬜ No | Image filename + notes | - | `"fall-hero.jpg - Autumn theme"` |
| `cta_copy` | string | ⬜ No | Call-to-action text | - | `"Shop Now"` |
| `offer` | string | ⬜ No | Promotional offer details | - | `"30% off + free shipping"` |
| `ab_test_idea` | string | ⬜ No | A/B testing strategy | - | `"Test emoji vs plain text"` |
| `secondary_message` | string | ⬜ No | Secondary message/SMS variant | `sms_variant` | `"Text FALL30 for discount"` |

### Campaign Types

#### Email Campaign Types
- `email` - Standard email (default)
- `promotional` - Sales, discounts, offers
- `content` - Educational, blog, guides
- `engagement` - Surveys, feedback, polls
- `seasonal` - Holiday/seasonal campaigns
- `special` - VIP, exclusive content

#### SMS Campaign Types
- `sms` - Standard SMS
- `sms-promotional` - SMS sales/offers
- `sms-content` - SMS content updates
- `sms-engagement` - SMS surveys
- `sms-seasonal` - SMS seasonal campaigns
- `sms-special` - SMS exclusive offers

#### Push Notification Types
- `push` - Mobile push notification
- `push-promotional` - Push for sales
- `push-reminder` - Push reminders

### Validation Rules

#### Date Validation
```javascript
// Format: YYYY-MM-DD
// Year: 2020-2030
// Month: 01-12
// Day: Valid for given month

// ✅ Valid
"2025-09-15"
"2025-01-01"

// ❌ Invalid
"2025-9-5"     // Missing leading zeros
"25-09-15"     // Two-digit year
"2025/09/15"   // Wrong separator
```

#### Type Validation
- Must exactly match one of the allowed types (case-sensitive, lowercase)
- Unknown types will fall back to `"email"`

#### Title/Name Validation
- Cannot be empty
- Maximum 100 characters recommended
- Special characters and emojis allowed
- Field must be named `title`, `name`, or `subject_line_a`

#### File Size Limits
- Maximum file size: 5MB
- Maximum campaigns per file: 1000
- Recommended: 10-100 campaigns per batch

---

## Supported File Formats

### 1. JSON Format (.json)

**Advantages**:
- Full field support (all 13+ fields)
- Structured data with validation
- Human-readable and editable
- Native JavaScript parsing

**Example**:
```json
{
  "events": [
    {
      "week_number": 36,
      "date": "2025-09-01",
      "send_time": "10:00",
      "type": "email",
      "segments": "all_subscribers",
      "subject_line_a": "🎉 Labor Day Sale - Up to 50% Off!",
      "subject_line_b": "Your Exclusive Labor Day Savings",
      "preview_text": "Shop biggest sale of season - 3 days only!",
      "hero_h1": "LABOR DAY MEGA SALE",
      "sub_head": "Save Big on Everything You Love",
      "hero_image": "labor-day-hero.jpg - Patriotic theme",
      "cta_copy": "Shop Sale Now",
      "offer": "Up to 50% off + Free shipping on $75+",
      "ab_test_idea": "Test emoji in subject vs plain text",
      "secondary_message": "Text LABOR to 12345 for SMS deals"
    }
  ]
}
```

### 2. CSV Format (.csv)

**Advantages**:
- Easy export from Excel/Google Sheets
- Familiar tabular format
- Column mapping UI for flexibility

**Workflow**:
1. Upload CSV file
2. System detects columns automatically
3. Map columns to fields using dropdowns:
   - Title Column → `title`
   - Date Column → `date`
   - Type Column → `type`
   - Content Column → `description`
4. Import mapped data

**Example CSV**:
```csv
date,title,type,description,segment
2025-09-01,Labor Day Sale,promotional,Up to 50% off everything,all_subscribers
2025-09-05,Fall Collection,content,New fall products launch,engaged_subscribers
2025-09-10,Customer Survey,engagement,Quarterly satisfaction survey,vip_customers
```

**Column Mapping Auto-Detection**:
The system automatically detects common column names:
- Title: `title`, `name`, `campaign`
- Date: `date`, `time`
- Type: `type`, `category`
- Content: `description`, `content`, `note`

### 3. Excel Format (.xlsx, .xls)

**Workflow**: Same as CSV with spreadsheet support
**Note**: Automatically converted to CSV format during processing

### 4. iCalendar Format (.ics)

**Advantages**:
- Import from calendar applications (Google Calendar, Outlook)
- Standard calendar format

**Limitations**:
- Basic fields only (title, date, description)
- All events default to `email` type

**Example ICS Structure**:
```ics
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:20250901
SUMMARY:Labor Day Sale
DESCRIPTION:Up to 50% off sitewide
END:VEVENT
END:VCALENDAR
```

---

## API Endpoints

### Create Single Event

```http
POST /api/calendar/events
Content-Type: application/json
```

**Request Body**:
```json
{
  "title": "Labor Day Sale",
  "date": "2025-09-01",
  "client_id": "client_abc123",
  "content": "50% off sitewide promotion",
  "color": "bg-red-200 text-red-800",
  "event_type": "promotional"
}
```

**Response** (201 Created):
```json
{
  "id": "event_xyz789",
  "message": "Event created successfully",
  "title": "Labor Day Sale",
  "date": "2025-09-01",
  "client_id": "client_abc123",
  "created_at": "2025-08-15T10:30:00Z"
}
```

### Create Bulk Events (Recommended for Import)

```http
POST /api/calendar/create-bulk-events
Content-Type: application/json
```

**Request Body**:
```json
{
  "client_id": "client_abc123",
  "events": [
    {
      "title": "Labor Day Sale",
      "date": "2025-09-01",
      "content": "50% off sitewide",
      "color": "bg-red-200 text-red-800",
      "event_type": "promotional",
      "segment": "all_subscribers",
      "send_time": "10:00"
    },
    {
      "title": "Fall Collection Launch",
      "date": "2025-09-05",
      "content": "New fall products",
      "color": "bg-blue-200 text-blue-800",
      "event_type": "content"
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "message": "Successfully created 2 events",
  "created_events": [
    {
      "id": "event_001",
      "title": "Labor Day Sale",
      "date": "2025-09-01"
    },
    {
      "id": "event_002",
      "title": "Fall Collection Launch",
      "date": "2025-09-05"
    }
  ],
  "total_created": 2,
  "total_requested": 2
}
```

### Retrieve Events

```http
GET /api/calendar/events?client_id={id}&start_date={date}&end_date={date}
```

**Query Parameters**:
- `client_id` (required) - Client identifier
- `start_date` (optional) - Filter start date (YYYY-MM-DD)
- `end_date` (optional) - Filter end date (YYYY-MM-DD)

**Response** (200 OK):
```json
[
  {
    "id": "event_001",
    "title": "✉️ Labor Day Sale",
    "date": "2025-09-01",
    "client_id": "client_abc123",
    "content": "50% off sitewide",
    "color": "bg-red-200 text-red-800",
    "event_type": "promotional",
    "created_at": "2025-08-15T10:30:00Z",
    "imported": true
  }
]
```

### Error Responses

**400 Bad Request** - Invalid data:
```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD"
}
```

**404 Not Found** - Client not found:
```json
{
  "detail": "Client with ID client_abc123 not found"
}
```

**500 Internal Server Error** - Server error:
```json
{
  "detail": "Failed to create events: Database connection error"
}
```

---

## UI Import Workflow

### Step-by-Step User Flow

#### Step 1: Client Selection (Prerequisite)
```
┌─────────────────────────────────┐
│  ⚠️ Client Required             │
│                                 │
│  You must select a client       │
│  before importing campaigns.    │
│                                 │
│  [Select Client Dropdown ▼]    │
└─────────────────────────────────┘
```

**Validation**: Import button is disabled until client is selected
**Location**: Top navigation bar, client selector dropdown
**Error Message**: "Please select a client first" (warning toast)

#### Step 2: Open Import Modal
```
┌─────────────────────────────────┐
│  Calendar View                  │
│  ┌──────────┐                   │
│  │ [Import] │ ← Click here      │
│  └──────────┘                   │
└─────────────────────────────────┘
```

**Button Location**: Top toolbar next to Export, Month navigation
**Button Style**: Glow button with "Import" label
**Function**: `openFileImportModal()`

#### Step 3: Import Modal Interface

```
╔═══════════════════════════════════════════════════╗
║        📥 Import Campaign Calendar                ║
╠═══════════════════════════════════════════════════╣
║                                                   ║
║  File Format: [JSON ▼]                           ║
║               (options: JSON, CSV, Excel, iCal)   ║
║                                                   ║
║  ┌─────────────────────────────────────────────┐ ║
║  │  📁 Drag & Drop File Here                   │ ║
║  │          or click to browse                 │ ║
║  │                                             │ ║
║  │  Supported: .json, .csv, .xlsx, .ics       │ ║
║  │  Max size: 5MB                              │ ║
║  └─────────────────────────────────────────────┘ ║
║                                                   ║
║  [File Preview Area - appears after selection]    ║
║                                                   ║
║  [Cancel]                    [📥 Import Events]  ║
║                              (disabled initially) ║
╚═══════════════════════════════════════════════════╝
```

**Modal Features**:
- Drag-and-drop support
- File type selector with automatic accept filter
- Real-time file preview
- File size and format validation
- CSV column mapping UI (when CSV selected)

#### Step 4: File Selection & Preview

**4a. File Selection**
- User drags file or clicks to browse
- File is validated (type, size)
- File name and size displayed

```
Selected File:
┌─────────────────────────────────┐
│ 📄 campaigns_september.json     │
│    2.3 KB                       │
│                            [×]  │
└─────────────────────────────────┘
```

**4b. Preview Display**
```
File Preview:
┌─────────────────────────────────┐
│ {                               │
│   "events": [                   │
│     {                           │
│       "date": "2025-09-01",     │
│       "title": "Labor Day",     │
│       "type": "promotional"     │
│     },                          │
│     ...                         │
│   ]                             │
│ }                               │
└─────────────────────────────────┘
```

**4c. CSV Column Mapping** (CSV/Excel only)
```
Map CSV Columns:
┌─────────────────────────────────┐
│ Title Column:  [campaign_name▼] │
│ Date Column:   [send_date ▼]    │
│ Type Column:   [category ▼]     │
│ Content:       [description ▼]  │
└─────────────────────────────────┘

Preview:
campaign_name,  send_date,   category
Labor Day,      2025-09-01,  promo
Fall Launch,    2025-09-05,  content
```

#### Step 5: Processing & Import

**5a. Click "Import Events" Button**
```
Button State: Processing
┌─────────────────────────────────┐
│  ⏳ Processing...                │
└─────────────────────────────────┘
```

**5b. Validation & Parsing**
- JSON parsed and validated
- Events normalized (dates, types, emojis)
- Invalid events filtered with warnings

**5c. Adding to Calendar**
```
Progress Toast:
┌─────────────────────────────────┐
│  ⏳ Importing 15 campaigns...    │
└─────────────────────────────────┘
```

**5d. Cloud Sync**
- Events added to calendar manager
- Automatic save to Firestore
- Real-time sync to `calendar_events` collection

#### Step 6: Success Confirmation

```
Success Toast:
┌─────────────────────────────────┐
│  ✅ Successfully imported 15     │
│     events to September 2025     │
└─────────────────────────────────┘
```

**Calendar Updates**:
- Modal closes automatically
- Calendar view refreshes with new events
- Statistics updated (campaign count, revenue projections)
- Events visible with appropriate colors and emojis

#### Step 7: Error States

**Invalid JSON**:
```
Error Toast:
┌─────────────────────────────────┐
│  ❌ Error importing file:        │
│     Invalid JSON format at       │
│     line 15                      │
└─────────────────────────────────┘
```

**Missing Required Fields**:
```
Error Toast:
┌─────────────────────────────────┐
│  ❌ Error: Event #3 missing      │
│     required field 'date'        │
└─────────────────────────────────┘
```

**No Valid Events Found**:
```
Warning Toast:
┌─────────────────────────────────┐
│  ⚠️ No valid events found in     │
│     file. Check format.          │
└─────────────────────────────────┘
```

---

## Data Mapping & Transformation

### Field Mapping Logic

The `normalizeEventData()` function transforms imported data into the standard calendar event format.

#### Date Normalization
```javascript
// Accepts multiple field names
let date = event.date || event.event_date || event.send_date || event.dtstart;

// Converts to YYYY-MM-DD format
const dateObj = new Date(date);
date = dateObj.toISOString().split('T')[0]; // "2025-09-15"
```

**Supported Input Formats**:
- ISO 8601: `"2025-09-15T14:30:00Z"` → `"2025-09-15"`
- Date string: `"September 15, 2025"` → `"2025-09-15"`
- Timestamp: `1725552000000` → `"2025-09-15"`
- iCal format: `"20250915"` → `"2025-09-15"`

#### Type & Emoji Assignment
```javascript
let type = event.event_type || event.type || event.category || 'email';
let emoji = '';

if (type.toLowerCase().includes('sms')) {
    emoji = '💬 ';  // SMS campaigns
} else if (type.toLowerCase().includes('push')) {
    emoji = '📱 ';  // Push notifications
} else {
    emoji = '✉️ ';  // Email campaigns (default)
}
```

**Type Mapping Table**:
| Input Type | Normalized Type | Emoji | Color Class |
|------------|----------------|-------|-------------|
| `email`, `promotional`, `content` | `email` | ✉️ | `bg-blue-200 text-blue-800` |
| `sms`, `sms-promotional` | `sms` | 💬 | `bg-orange-200 text-orange-800` |
| `push`, `push-promotional` | `push` | 📱 | `bg-purple-200 text-purple-800` |
| `flash sale`, `rrb` | `promotional` | ✉️ | `bg-red-300 text-red-800` |
| `cheese club`, `nurturing` | `special` | ✉️ | `bg-green-200 text-green-800` |
| `seasonal`, `holiday` | `seasonal` | ✉️ | `bg-purple-200 text-purple-800` |

#### Title Enhancement
```javascript
// Accepts multiple field names for title
let title = event.title || event.name || event.summary ||
            event.subject_line_a || 'Imported Event';

// Add emoji prefix
title = emoji + title;

// Result: "✉️ Labor Day Sale" or "💬 Flash Sale Alert"
```

#### Description Enrichment
```javascript
// Base description
let description = event.description || event.content || '';

// Append additional campaign metadata
const extraFields = [];
if (event.week_number) extraFields.push(`Week #${event.week_number}`);
if (event.send_time) extraFields.push(`Send Time: ${event.send_time}`);
if (event.segments) extraFields.push(`Segment: ${event.segments}`);
if (event.subject_line_a) extraFields.push(`Subject A: ${event.subject_line_a}`);
if (event.subject_line_b) extraFields.push(`Subject B: ${event.subject_line_b}`);
// ... (13 additional fields)

if (extraFields.length > 0) {
    description += '\n\n' + extraFields.join('\n');
}
```

**Example Enriched Description**:
```
Up to 50% off sitewide for Labor Day weekend

Week #36
Send Time: 10:00
Segment: all_subscribers
Subject A: 🎉 Labor Day Sale - Up to 50% Off!
Subject B: Your Exclusive Labor Day Savings Inside
Preview: Shop our biggest sale of the season - 3 days only!
H1: LABOR DAY MEGA SALE
Subhead: Save Big on Everything You Love
Hero Image: labor-day-hero.jpg - Patriotic theme
CTA: Shop Sale Now
Offer: Up to 50% off + Free shipping on orders $75+
A/B Test: Test emoji in subject line vs plain text
Secondary/SMS: Text LABOR to 12345 for exclusive SMS deals
```

### Firestore Data Schema

Imported events are stored in the `calendar_events` collection with this structure:

```javascript
{
  // Core Fields (required)
  id: "imported-1725552000000-abc123",      // Auto-generated unique ID
  name: "✉️ Labor Day Sale",                 // Title with emoji
  type: "promotional",                       // Campaign type
  date: Date("2025-09-01T00:00:00Z"),       // Date object
  client_id: "client_abc123",                // Selected client ID

  // Display Fields
  description: "50% off sitewide...",        // Enriched description
  color: "bg-red-300 text-red-800",         // Tailwind color classes
  emoji: "✉️",                               // Channel emoji

  // Metadata
  segment: "all_subscribers",                // Target segment
  imported: true,                            // Import flag

  // Timestamps
  created_at: Date("2025-08-15T10:30:00Z"),
  updated_at: Date("2025-08-15T10:30:00Z"),

  // Original Data (preserved for reference)
  originalData: {
    week_number: 36,
    send_time: "10:00",
    subject_line_a: "🎉 Labor Day Sale - Up to 50% Off!",
    subject_line_b: "Your Exclusive Labor Day Savings Inside",
    preview_text: "Shop our biggest sale...",
    hero_h1: "LABOR DAY MEGA SALE",
    sub_head: "Save Big on Everything You Love",
    hero_image: "labor-day-hero.jpg - Patriotic theme",
    cta_copy: "Shop Sale Now",
    offer: "Up to 50% off + Free shipping on $75+",
    ab_test_idea: "Test emoji in subject vs plain text",
    secondary_message: "Text LABOR to 12345 for SMS deals",
    sms_variant: null
  }
}
```

### Default Value Assignment

When optional fields are missing:

| Field | Default Value | Logic |
|-------|---------------|-------|
| `type` | `"email"` | If not provided or invalid |
| `description` | `""` | Empty string |
| `segment` | `"all_subscribers"` | If not provided |
| `color` | Calculated from type | See type mapping table |
| `emoji` | Calculated from type | ✉️, 💬, or 📱 |
| `id` | `"imported-{timestamp}-{random}"` | Auto-generated |
| `imported` | `true` | Flag for imported events |
| `date` | Current date | If parsing fails |

---

## Integration Points

### Firestore Collections

#### Primary Collection: `calendar_events`

**Purpose**: Stores all calendar campaign events

**Access Pattern**:
```javascript
// Read events for client and date range
GET /api/calendar/events?client_id={id}&start_date={start}&end_date={end}

// Write single event
POST /api/calendar/events

// Write bulk events (import)
POST /api/calendar/create-bulk-events

// Update event
PUT /api/calendar/events/{event_id}

// Delete event
DELETE /api/calendar/events/{event_id}
```

**Index Requirements**:
- `client_id` (for client filtering)
- `date` (for date range queries)
- Composite index: `client_id + date` (for efficient queries)

#### Supporting Collections

**`clients`** - Client information
```javascript
{
  id: "client_abc123",
  name: "Example Client",
  email: "client@example.com",
  is_active: true
}
```

**`calendar_conversations`** - AI chat history
```javascript
{
  client_id: "client_abc123",
  conversation: [
    { role: "user", content: "Import my Q4 campaigns" },
    { role: "assistant", content: "I'll help you import..." }
  ],
  updated_at: Date,
  message_count: 15
}
```

**`goals`** - Revenue goals for progress tracking
```javascript
{
  client_id: "client_abc123",
  year: 2025,
  month: 9,
  monthly_revenue: 50000
}
```

### Real-time Sync Behavior

#### Import Flow with Auto-save

```javascript
// 1. User imports file → Events added to calendar manager
importEventsToCalendar(events) {
    events.forEach(event => {
        calendarManager.campaigns.push(event);
    });

    // 2. Auto-save to Firestore
    await calendarManager.saveToCloud();

    // 3. Refresh UI
    calendarManager.renderCalendar();
    calendarManager.updateStats();

    // 4. Save undo state
    calendarManager.saveState();
}
```

#### Cloud Save Process

```javascript
async saveToCloud() {
    // 1. Get current month's date range
    const monthStart = "2025-09-01";
    const monthEnd = "2025-09-31";

    // 2. Fetch existing events for this month
    const existingEvents = await fetch(
        `/api/calendar/events?client_id=${clientId}&start_date=${monthStart}&end_date=${monthEnd}`
    );

    // 3. Delete old events (clean slate)
    await Promise.all(
        existingEvents.map(e =>
            fetch(`/api/calendar/events/${e.id}`, { method: 'DELETE' })
        )
    );

    // 4. Save new events (bulk)
    await fetch('/api/calendar/create-bulk-events', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, events: events })
    });

    // 5. Broadcast sync to other tabs/windows
    this.broadcastSync();
}
```

**Sync Strategy**: Replace all events for current month
- **Rationale**: Simpler than merge logic, prevents duplicates
- **Performance**: Bulk operations minimize API calls
- **Consistency**: Ensures UI matches Firestore exactly

### Conflict Resolution

**Scenario 1: Duplicate Imports**
- **Detection**: Events with same `title` and `date`
- **Resolution**: Both are imported (user can manually delete)
- **Best Practice**: Clear calendar before import or use unique IDs

**Scenario 2: Multi-Tab Editing**
- **Detection**: BroadcastChannel API notifications
- **Resolution**: Last write wins (Firestore timestamp)
- **User Warning**: "Calendar updated in another window"

**Scenario 3: Network Failures**
- **Detection**: API call timeout or error
- **Resolution**: Retry logic (3 attempts)
- **Fallback**: Save to localStorage, sync on reconnect
- **User Notification**: "Save failed - changes saved locally"

### API Error Handling

```javascript
try {
    await importEventsToCalendar(events);
    showToast(`Successfully imported ${events.length} events`, 'success');
} catch (error) {
    console.error('Import error:', error);

    if (error.message.includes('401')) {
        showToast('Session expired - please log in', 'error');
        // Redirect to login
    } else if (error.message.includes('404')) {
        showToast('Client not found - please select a client', 'warning');
    } else if (error.message.includes('500')) {
        showToast('Server error - please try again', 'error');
        // Save to localStorage for retry
    } else {
        showToast('Error importing file: ' + error.message, 'error');
    }
}
```

---

## Code Examples

### Example 1: Minimal JSON Import File

```json
{
  "events": [
    {
      "date": "2025-09-01",
      "title": "Labor Day Sale",
      "type": "promotional"
    },
    {
      "date": "2025-09-15",
      "title": "Mid-Month Newsletter",
      "type": "content"
    }
  ]
}
```

**Result**: 2 events imported with default colors, emojis, and "all_subscribers" segment.

### Example 2: Standard JSON with Common Fields

```json
{
  "events": [
    {
      "date": "2025-09-01",
      "title": "Labor Day Flash Sale",
      "type": "promotional",
      "description": "24-hour flash sale with 50% off",
      "segment": "engaged_subscribers",
      "send_time": "10:00"
    },
    {
      "date": "2025-09-05",
      "title": "Fall Collection Launch",
      "type": "content",
      "description": "Introducing our new fall line",
      "segment": "all_subscribers",
      "send_time": "09:00"
    },
    {
      "date": "2025-09-10",
      "title": "Exclusive VIP Preview",
      "type": "special",
      "description": "Early access for VIP customers",
      "segment": "vip_customers",
      "send_time": "15:00"
    }
  ]
}
```

### Example 3: Complete JSON with All Fields

```json
{
  "events": [
    {
      "week_number": 36,
      "date": "2025-09-01",
      "send_time": "10:00",
      "type": "email",
      "segments": "all_subscribers, active_30_days",
      "subject_line_a": "🎉 Labor Day Sale - Up to 50% Off!",
      "subject_line_b": "Your Exclusive Labor Day Savings Inside",
      "preview_text": "Shop our biggest sale of the season - 3 days only!",
      "hero_h1": "LABOR DAY MEGA SALE",
      "sub_head": "Save Big on Everything You Love",
      "hero_image": "labor-day-hero.jpg - Patriotic theme with fireworks",
      "cta_copy": "Shop Sale Now",
      "offer": "Up to 50% off + Free shipping on orders $75+",
      "ab_test_idea": "Test emoji in subject line vs plain text",
      "secondary_message": "Text LABOR to 12345 for exclusive SMS deals"
    },
    {
      "week_number": 37,
      "date": "2025-09-08",
      "send_time": "14:30",
      "type": "sms",
      "segments": "sms_subscribers",
      "title": "Flash Sale Alert",
      "description": "4-hour flash sale reminder",
      "sms_variant": "FLASH SALE: 30% off everything! Use code FLASH30. Shop now: [link] Reply STOP to opt out"
    }
  ]
}
```

### Example 4: Multi-Month Campaign Calendar

```json
{
  "events": [
    {
      "date": "2025-08-28",
      "title": "August End Sale",
      "type": "promotional",
      "description": "Clear summer inventory",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-09-01",
      "title": "Labor Day Sale",
      "type": "promotional",
      "description": "Patriotic weekend sale",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-09-15",
      "title": "Fall Collection Launch",
      "type": "content",
      "description": "New fall products",
      "segment": "engaged_subscribers"
    },
    {
      "date": "2025-10-01",
      "title": "October Fest",
      "type": "seasonal",
      "description": "Autumn celebration sale",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-10-31",
      "title": "Halloween Spooktacular",
      "type": "seasonal",
      "description": "Halloween themed promotion",
      "segment": "all_subscribers"
    }
  ]
}
```

### Example 5: JavaScript - Generate Import File Programmatically

```javascript
/**
 * Generate a campaign calendar JSON file for import
 */
function generateCampaignCalendar(startDate, numberOfWeeks, campaignType) {
    const events = [];
    const start = new Date(startDate);

    for (let week = 0; week < numberOfWeeks; week++) {
        // Calculate Monday and Friday of each week
        const monday = new Date(start);
        monday.setDate(start.getDate() + (week * 7));

        const friday = new Date(monday);
        friday.setDate(monday.getDate() + 4);

        // Monday email campaign
        events.push({
            week_number: week + 1,
            date: monday.toISOString().split('T')[0],
            send_time: "09:00",
            type: "email",
            segments: "all_subscribers",
            subject_line_a: `Week ${week + 1}: New Products Just Arrived`,
            preview_text: "Check out what's new this week",
            cta_copy: "Shop New Arrivals",
            title: `Week ${week + 1} - Monday Email`
        });

        // Friday SMS reminder
        events.push({
            week_number: week + 1,
            date: friday.toISOString().split('T')[0],
            send_time: "15:00",
            type: "sms",
            segments: "sms_subscribers",
            title: `Week ${week + 1} - Friday SMS Reminder`,
            sms_variant: `Weekend sale starts NOW! 20% off with code WEEKEND${week + 1}. Shop: [link]`
        });
    }

    return {
        events: events
    };
}

// Generate 4 weeks of campaigns starting Sept 1
const calendar = generateCampaignCalendar('2025-09-01', 4, 'promotional');

// Save to file
const blob = new Blob([JSON.stringify(calendar, null, 2)], {
    type: 'application/json'
});
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'campaign-calendar-sept-2025.json';
a.click();
```

### Example 6: Python - Generate Import File from Database

```python
import json
from datetime import datetime, timedelta

def generate_calendar_from_db(client_id, start_date, end_date):
    """
    Generate calendar import JSON from database records

    Args:
        client_id: Client identifier
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Dictionary ready for JSON export
    """
    # Example: Fetch from your database
    campaigns = [
        {
            'campaign_name': 'Labor Day Sale',
            'scheduled_date': '2025-09-01',
            'campaign_type': 'promotional',
            'target_segment': 'all_subscribers',
            'subject_line': '🎉 Big Labor Day Savings!',
            'preview_text': 'Shop now for 50% off',
            'send_hour': 10
        },
        {
            'campaign_name': 'Fall Newsletter',
            'scheduled_date': '2025-09-05',
            'campaign_type': 'content',
            'target_segment': 'engaged_subscribers',
            'subject_line': 'Fall Into Savings',
            'preview_text': 'New products for fall',
            'send_hour': 9
        }
    ]

    # Transform to calendar import format
    events = []
    for campaign in campaigns:
        event = {
            'date': campaign['scheduled_date'],
            'title': campaign['campaign_name'],
            'type': campaign['campaign_type'],
            'segment': campaign['target_segment'],
            'send_time': f"{campaign['send_hour']:02d}:00",
            'subject_line_a': campaign['subject_line'],
            'preview_text': campaign['preview_text']
        }
        events.append(event)

    return {'events': events}

# Generate and save
calendar_data = generate_calendar_from_db(
    client_id='client_abc123',
    start_date='2025-09-01',
    end_date='2025-09-30'
)

with open('calendar_import_september.json', 'w') as f:
    json.dump(calendar_data, f, indent=2)

print(f"Generated calendar with {len(calendar_data['events'])} events")
```

### Example 7: Google Sheets to JSON Conversion

```javascript
/**
 * Google Apps Script - Export Sheet as Calendar JSON
 *
 * How to use:
 * 1. Tools → Script Editor in Google Sheets
 * 2. Paste this code
 * 3. Run exportAsCalendarJSON()
 * 4. Download generated JSON file
 */
function exportAsCalendarJSON() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();

  // Assume first row is headers
  const headers = data[0];
  const events = [];

  // Map columns (adjust indices based on your sheet)
  const columnMap = {
    date: 0,        // Column A
    title: 1,       // Column B
    type: 2,        // Column C
    description: 3, // Column D
    segment: 4      // Column E
  };

  // Process each row (skip header)
  for (let i = 1; i < data.length; i++) {
    const row = data[i];

    // Skip empty rows
    if (!row[columnMap.date]) continue;

    const event = {
      date: Utilities.formatDate(new Date(row[columnMap.date]),
                                  Session.getScriptTimeZone(),
                                  'yyyy-MM-dd'),
      title: row[columnMap.title] || 'Campaign',
      type: row[columnMap.type] || 'email',
      description: row[columnMap.description] || '',
      segment: row[columnMap.segment] || 'all_subscribers'
    };

    events.push(event);
  }

  const calendarJSON = {
    events: events
  };

  // Create JSON file in Google Drive
  const fileName = `calendar_import_${new Date().getTime()}.json`;
  const file = DriveApp.createFile(
    fileName,
    JSON.stringify(calendarJSON, null, 2),
    MimeType.PLAIN_TEXT
  );

  Logger.log(`Created file: ${file.getUrl()}`);
  Logger.log(`${events.length} events exported`);

  // Show success message
  SpreadsheetApp.getUi().alert(
    `Successfully exported ${events.length} events to ${fileName}\n\n` +
    `Download from: ${file.getUrl()}`
  );
}

// Add menu item to Sheet
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Calendar Export')
    .addItem('Export as Calendar JSON', 'exportAsCalendarJSON')
    .addToUi();
}
```

### Example 8: cURL - Direct API Import

```bash
#!/bin/bash

# Import campaigns directly via API
# Usage: ./import_campaigns.sh client_abc123 campaigns.json

CLIENT_ID=$1
JSON_FILE=$2
API_URL="http://localhost:8000"

if [ -z "$CLIENT_ID" ] || [ -z "$JSON_FILE" ]; then
    echo "Usage: $0 <client_id> <json_file>"
    exit 1
fi

# Read JSON file
EVENTS=$(cat "$JSON_FILE" | jq '.events')

# Create bulk import payload
PAYLOAD=$(jq -n \
    --arg client_id "$CLIENT_ID" \
    --argjson events "$EVENTS" \
    '{client_id: $client_id, events: $events}')

# Send to API
echo "Importing campaigns for client: $CLIENT_ID"
echo "From file: $JSON_FILE"

RESPONSE=$(curl -s -X POST "$API_URL/api/calendar/create-bulk-events" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

# Parse response
TOTAL_CREATED=$(echo "$RESPONSE" | jq -r '.total_created')
TOTAL_REQUESTED=$(echo "$RESPONSE" | jq -r '.total_requested')

if [ "$TOTAL_CREATED" == "$TOTAL_REQUESTED" ]; then
    echo "✅ Success! Imported $TOTAL_CREATED campaigns"
else
    echo "⚠️  Partial success: $TOTAL_CREATED of $TOTAL_REQUESTED imported"
    echo "Response: $RESPONSE"
fi
```

### Example 9: Batch Import Script

```python
#!/usr/bin/env python3
"""
Batch import campaigns from multiple JSON files
Usage: python batch_import.py client_id /path/to/json/files/
"""

import sys
import json
import requests
from pathlib import Path

def import_campaigns(client_id, json_file, api_url='http://localhost:8000'):
    """Import campaigns from JSON file"""

    # Read JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extract events
    events = data.get('events', [])

    if not events:
        print(f"⚠️  No events found in {json_file}")
        return 0

    # Prepare API payload
    payload = {
        'client_id': client_id,
        'events': events
    }

    # Send to API
    try:
        response = requests.post(
            f'{api_url}/api/calendar/create-bulk-events',
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        created = result.get('total_created', 0)
        print(f"✅ Imported {created} events from {json_file.name}")
        return created

    except requests.exceptions.RequestException as e:
        print(f"❌ Error importing {json_file.name}: {e}")
        return 0

def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_import.py <client_id> <directory>")
        sys.exit(1)

    client_id = sys.argv[1]
    directory = Path(sys.argv[2])

    if not directory.is_dir():
        print(f"Error: {directory} is not a directory")
        sys.exit(1)

    # Find all JSON files
    json_files = list(directory.glob('*.json'))

    if not json_files:
        print(f"No JSON files found in {directory}")
        sys.exit(1)

    print(f"Found {len(json_files)} JSON files")
    print(f"Importing to client: {client_id}\n")

    # Import each file
    total_imported = 0
    for json_file in sorted(json_files):
        imported = import_campaigns(client_id, json_file)
        total_imported += imported

    print(f"\n🎉 Total: {total_imported} campaigns imported from {len(json_files)} files")

if __name__ == '__main__':
    main()
```

---

## Best Practices

### Data Preparation

#### 1. Validate Before Import
```bash
# Use jsonlint or jq to validate JSON
jq empty campaigns.json && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
```

#### 2. Use Consistent Date Format
```json
// ✅ Correct
"date": "2025-09-15"

// ❌ Incorrect
"date": "9/15/2025"
"date": "Sept 15, 2025"
"date": "2025-9-15"  // Missing leading zero
```

#### 3. Standardize Campaign Types
Create a reference sheet of allowed types:
```
email, promotional, content, engagement, seasonal, special
sms, sms-promotional, sms-content, sms-engagement, sms-seasonal
push, push-promotional, push-reminder
```

#### 4. Use Descriptive Titles
```json
// ✅ Good - Specific and actionable
"title": "Labor Day Weekend Flash Sale - 50% Off"

// ❌ Bad - Vague
"title": "Sale"
"title": "Campaign 1"
```

### Workflow Recommendations

#### 1. Phased Import Approach
```
Phase 1: Test with 2-3 events
  → Verify formatting and fields
  → Check calendar display

Phase 2: Import one week (5-7 events)
  → Review on calendar
  → Adjust dates/types as needed

Phase 3: Import full month (15-20 events)
  → Monitor for duplicates
  → Validate all campaigns appear

Phase 4: Import multi-month campaigns
  → Ensure proper date distribution
  → Check revenue projections
```

#### 2. Monthly Import Checklist
- [ ] Select correct client
- [ ] Clear existing campaigns (if replacing)
- [ ] Validate JSON format
- [ ] Check required fields (date, title, type)
- [ ] Verify date range matches intended month
- [ ] Import test batch (2-3 events)
- [ ] Review calendar display
- [ ] Import full month
- [ ] Verify campaign count in stats
- [ ] Check revenue goal progress
- [ ] Save/export calendar backup

#### 3. Template Organization
Create reusable templates by campaign type:

```
templates/
├── promotional-campaign-template.json
├── seasonal-campaign-template.json
├── monthly-newsletter-template.json
├── sms-series-template.json
└── multi-channel-campaign-template.json
```

### Performance Optimization

#### 1. Batch Size Guidelines
- **Optimal**: 10-50 campaigns per import
- **Maximum**: 1000 campaigns (system limit)
- **Large imports**: Split into multiple files by month

#### 2. API Call Optimization
```javascript
// ✅ Use bulk endpoint for imports
POST /api/calendar/create-bulk-events
// Payload: { client_id, events: [...] }

// ❌ Avoid individual calls in loop
events.forEach(e => POST /api/calendar/events) // SLOW!
```

#### 3. Network Efficiency
- Import during off-peak hours for large batches
- Use CDN or local server for file hosting
- Compress large JSON files before upload

### Error Prevention

#### 1. Pre-Import Validation Script
```python
def validate_import_file(json_file):
    """Validate import file before upload"""
    with open(json_file) as f:
        data = json.load(f)

    errors = []

    # Check structure
    if 'events' not in data and not isinstance(data, list):
        errors.append("Missing 'events' property")

    events = data.get('events', data)

    # Check each event
    for i, event in enumerate(events):
        # Required fields
        if 'date' not in event:
            errors.append(f"Event {i}: Missing 'date'")
        if 'title' not in event and 'name' not in event:
            errors.append(f"Event {i}: Missing 'title' or 'name'")
        if 'type' not in event:
            errors.append(f"Event {i}: Missing 'type'")

        # Date format
        if 'date' in event:
            try:
                datetime.strptime(event['date'], '%Y-%m-%d')
            except ValueError:
                errors.append(f"Event {i}: Invalid date format")

    return errors

# Usage
errors = validate_import_file('campaigns.json')
if errors:
    print("❌ Validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ File is valid")
```

#### 2. Backup Before Import
```javascript
// Export current calendar before importing new events
async function exportBeforeImport() {
    const currentEvents = await fetchCalendarEvents(clientId);

    const backup = {
        exported_at: new Date().toISOString(),
        client_id: clientId,
        events: currentEvents
    };

    // Download backup
    const blob = new Blob([JSON.stringify(backup, null, 2)], {
        type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backup-${clientId}-${Date.now()}.json`;
    a.click();
}
```

### Security Best Practices

#### 1. Input Sanitization
- All imported data is sanitized by backend
- HTML/Script tags are escaped
- File size limits enforced (5MB)
- JSON depth limits prevent overflow attacks

#### 2. Access Control
- User must be authenticated to import
- User must have client access permissions
- Rate limiting: 10 imports per minute per user

#### 3. Data Validation
- Server-side validation of all fields
- Type checking for dates, strings, numbers
- Campaign type whitelist enforcement

---

## Troubleshooting

### Common Errors

#### Error: "Invalid JSON format"

**Cause**: Malformed JSON syntax

**Solutions**:
1. Validate JSON at [jsonlint.com](https://jsonlint.com)
2. Check for common issues:
   - Missing commas between objects
   - Trailing commas after last item
   - Unescaped quotes in strings
   - Missing closing brackets

**Example Fix**:
```json
// ❌ Invalid - trailing comma
{
  "events": [
    {"date": "2025-09-01", "title": "Sale"},
  ]
}

// ✅ Valid - no trailing comma
{
  "events": [
    {"date": "2025-09-01", "title": "Sale"}
  ]
}
```

#### Error: "Invalid date format"

**Cause**: Date not in YYYY-MM-DD format

**Solution**: Convert dates to ISO format
```javascript
// Convert various formats to YYYY-MM-DD
const date = new Date("September 15, 2025");
const formatted = date.toISOString().split('T')[0]; // "2025-09-15"
```

#### Error: "Unknown campaign type"

**Cause**: Type field doesn't match allowed values

**Solution**: Use only approved campaign types
```json
// ✅ Valid types
"type": "email"
"type": "promotional"
"type": "sms"

// ❌ Invalid types
"type": "Email"  // Wrong case
"type": "promo"  // Not in list
"type": "marketing"  // Not recognized
```

#### Error: "Missing required field"

**Cause**: Event missing `date`, `title`, or `type`

**Solution**: Ensure all events have required fields
```json
// ❌ Missing 'type'
{
  "date": "2025-09-01",
  "title": "Sale"
}

// ✅ All required fields present
{
  "date": "2025-09-01",
  "title": "Sale",
  "type": "promotional"
}
```

#### Error: "Unrecognized JSON format"

**Cause**: JSON structure doesn't match expected formats

**Solution**: Use one of three accepted structures
```json
// ✅ Option 1: Object with 'events' property
{"events": [{...}, {...}]}

// ✅ Option 2: Object with 'calendar' property
{"calendar": [{...}, {...}]}

// ✅ Option 3: Direct array
[{...}, {...}]

// ❌ Invalid: Object with different property
{"campaigns": [{...}]}
```

#### Warning: "No valid events found in file"

**Cause**: All events failed validation

**Troubleshooting Steps**:
1. Check event structure matches specification
2. Verify all required fields present
3. Confirm date format is YYYY-MM-DD
4. Ensure campaign types are valid
5. Check file isn't empty

#### Error: "Please select a client first"

**Cause**: No client selected before import

**Solution**:
1. Click client dropdown in top navigation
2. Select target client
3. Then open import modal

#### Error: "Failed to save to cloud"

**Cause**: Network error or Firestore connection issue

**Solutions**:
1. Check internet connection
2. Verify Firestore is accessible
3. Check browser console for specific error
4. Try importing again
5. Import smaller batch if large file

### Debugging Steps

#### 1. Enable Console Logging
```javascript
// Open browser console (F12)
// Look for these log messages:
console.log('Importing events:', events);
console.log('Normalized event:', normalizedEvent);
console.log('Save response:', response);
```

#### 2. Validate Individual Event
```javascript
// Test single event normalization in console
const testEvent = {
    date: "2025-09-01",
    title: "Test Campaign",
    type: "email"
};

const normalized = normalizeEventData(testEvent);
console.log('Normalized:', normalized);
```

#### 3. Check Network Requests
```
1. Open DevTools (F12)
2. Go to Network tab
3. Filter by "calendar"
4. Import file
5. Check for failed requests (red status codes)
6. Inspect request/response payload
```

#### 4. Verify Firestore Data
```javascript
// Check if events saved to Firestore
// In browser console:
fetch('/api/calendar/events?client_id=YOUR_CLIENT_ID')
    .then(r => r.json())
    .then(events => console.log('Firestore events:', events));
```

### Recovery Procedures

#### Scenario: Imported Wrong File

**Steps**:
1. Click "Undo" button (if available immediately after import)
2. Or manually delete incorrect campaigns
3. Re-import correct file

**Prevention**: Always backup before import (see Best Practices)

#### Scenario: Duplicate Events

**Causes**:
- Imported same file twice
- Didn't clear calendar before import

**Solution**:
1. Sort calendar by date
2. Identify duplicates (same title + date)
3. Delete duplicates manually
4. Or clear all campaigns and re-import

**Prevention**: Use unique IDs if available

#### Scenario: Lost Local Changes

**Cause**: Imported file overwrote unsaved calendar changes

**Solution**:
1. Check browser localStorage for cached data:
   ```javascript
   const cached = localStorage.getItem('calendar_backup');
   if (cached) {
       console.log('Cached data:', JSON.parse(cached));
   }
   ```
2. Use undo if immediately after import
3. Manually re-enter lost changes

**Prevention**: Save to cloud before importing

### Support Resources

#### Documentation
- [CALENDAR_JSON_UPLOAD_FORMAT.md](./CALENDAR_JSON_UPLOAD_FORMAT.md) - Format specification
- API Documentation - `/api/calendar/` endpoint reference

#### Validation Tools
- **JSON Validator**: [jsonlint.com](https://jsonlint.com)
- **JSON Formatter**: [jsonformatter.org](https://jsonformatter.org)
- **Date Format Checker**: [dateformatter.net](https://dateformatter.net)

#### Contact Support
For persistent issues:
1. Export current calendar state
2. Save problematic JSON file
3. Document steps to reproduce
4. Submit support ticket with:
   - Client ID
   - Error message
   - JSON file (anonymized if needed)
   - Browser console logs

---

## Version History

### v2.0 (2025-09-10) - Current Version
**Features**:
- Support for 13 advanced campaign fields
- Automatic emoji indicators (✉️ Email, 💬 SMS, 📱 Push)
- Enhanced description field with all campaign metadata
- Multi-day campaign support
- Bulk import API endpoint
- Real-time Firestore sync
- CSV column mapping UI
- iCalendar (.ics) format support
- Drag-and-drop file upload
- File preview before import

**API Changes**:
- Added `POST /api/calendar/create-bulk-events`
- Enhanced `CalendarEvent` schema with 13 fields

**Breaking Changes**: None (backward compatible)

### v1.1 (2025-09-10)
**Features**:
- Fixed JSON structure to use `events` property
- Changed `name` field to `title` (with `name` as alternative)
- Added `calendar` property as alternative to `events`
- Direct array format support

**Bug Fixes**:
- Fixed field name mapping issues
- Corrected date parsing for various formats

### v1.0 (2025-09-10) - Initial Release
**Features**:
- Basic JSON import
- Required fields: date, title, type
- Simple calendar display
- Firestore integration

**Compatibility**: EmailPilot Calendar v2.0+

---

## Appendix

### A. Complete Campaign Type Reference

| Type | Category | Emoji | Color | Use Case |
|------|----------|-------|-------|----------|
| `email` | Email | ✉️ | Blue | Standard email campaigns |
| `promotional` | Email | ✉️ | Red | Sales, discounts, special offers |
| `content` | Email | ✉️ | Blue | Educational content, blog posts |
| `engagement` | Email | ✉️ | Green | Surveys, feedback requests |
| `seasonal` | Email | ✉️ | Purple | Holiday and seasonal campaigns |
| `special` | Email | ✉️ | Green | VIP, exclusive content |
| `sms` | SMS | 💬 | Orange | Standard SMS messages |
| `sms-promotional` | SMS | 💬 | Orange | SMS sales and offers |
| `sms-content` | SMS | 💬 | Orange | SMS content updates |
| `sms-engagement` | SMS | 💬 | Orange | SMS surveys |
| `sms-seasonal` | SMS | 💬 | Orange | SMS seasonal campaigns |
| `sms-special` | SMS | 💬 | Orange | SMS exclusive offers |
| `push` | Push | 📱 | Purple | Mobile push notifications |
| `push-promotional` | Push | 📱 | Purple | Push for sales |
| `push-reminder` | Push | 📱 | Purple | Push reminders |

### B. Field Name Alternatives

| Standard Field | Alternatives Accepted |
|----------------|----------------------|
| `title` | `name`, `summary`, `subject_line_a` |
| `date` | `event_date`, `send_date`, `dtstart` |
| `type` | `event_type`, `category` |
| `description` | `content`, `notes` |
| `segment` | `segments`, `audience` |
| `secondary_message` | `sms_variant` |

### C. Color Class Reference

Tailwind CSS classes used for campaign types:

```css
/* Email campaigns */
bg-blue-200 text-blue-800       /* Standard email */
bg-red-300 text-red-800         /* Promotional */
bg-green-200 text-green-800     /* Special/Cheese Club */
bg-purple-200 text-purple-800   /* Seasonal */

/* SMS campaigns */
bg-orange-200 text-orange-800   /* All SMS types */

/* Push notifications */
bg-purple-200 text-purple-800   /* All push types */

/* Default fallback */
bg-gray-200 text-gray-800       /* Unknown type */
```

### D. API Response Examples

**Success Response**:
```json
{
  "message": "Successfully created 15 events",
  "created_events": [...],
  "total_created": 15,
  "total_requested": 15
}
```

**Partial Success Response**:
```json
{
  "message": "Successfully created 12 events",
  "created_events": [...],
  "total_created": 12,
  "total_requested": 15,
  "warnings": [
    "Event 3: Invalid date format, skipped",
    "Event 7: Missing required field 'type', skipped",
    "Event 11: Unknown campaign type, defaulted to 'email'"
  ]
}
```

**Error Response**:
```json
{
  "detail": "Failed to create events: Invalid client_id"
}
```

---

## Quick Reference

### Import Checklist
- [ ] Client selected
- [ ] JSON file validated
- [ ] Required fields present (date, title, type)
- [ ] Dates in YYYY-MM-DD format
- [ ] Campaign types match allowed values
- [ ] File size under 5MB
- [ ] Backup created (if replacing)

### Minimal Valid JSON
```json
{"events":[{"date":"2025-09-01","title":"Campaign","type":"email"}]}
```

### API Quick Reference
```bash
# Bulk import
POST /api/calendar/create-bulk-events
Body: {"client_id": "...", "events": [...]}

# Get events
GET /api/calendar/events?client_id=...&start_date=...&end_date=...

# Delete event
DELETE /api/calendar/events/{event_id}
```

### Support
- **Documentation**: [CALENDAR_JSON_UPLOAD_FORMAT.md](./CALENDAR_JSON_UPLOAD_FORMAT.md)
- **API Reference**: `/api/calendar/` (FastAPI docs)
- **Validation**: [jsonlint.com](https://jsonlint.com)

---

**Document Version**: 2.0
**Last Updated**: 2025-10-06
**Maintainer**: EmailPilot Development Team
**License**: Internal Use Only
