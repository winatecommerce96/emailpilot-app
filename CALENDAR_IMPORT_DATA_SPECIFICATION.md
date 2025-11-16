# Calendar Event Import - Rich Data Specification

**Version**: 1.0
**Last Updated**: November 15, 2025
**Purpose**: Comprehensive guide for external applications generating calendar events for EmailPilot import

---

## Overview

This document specifies how external calendar applications should format event data to provide the richest possible information when importing into EmailPilot's Campaign Calendar system. Following these specifications ensures seamless integration, maximum utility, and optimal AI-assisted campaign planning.

---

## Table of Contents

1. [Data Format](#data-format)
2. [Required Fields](#required-fields)
3. [Recommended Fields](#recommended-fields)
4. [Optional Enrichment Fields](#optional-enrichment-fields)
5. [Channel-Specific Fields](#channel-specific-fields)
6. [Campaign Type Specifications](#campaign-type-specifications)
7. [AI Assistant Integration](#ai-assistant-integration)
8. [Date and Time Formatting](#date-and-time-formatting)
9. [Import Formats](#import-formats)
10. [Validation Rules](#validation-rules)
11. [Examples](#examples)
12. [Best Practices](#best-practices)

---

## Data Format

EmailPilot accepts calendar event data in the following formats:

### Primary Format: JSON
```json
{
  "events": [
    {
      "id": "unique-event-id",
      "name": "Campaign Name",
      "date": "2025-12-15T10:00:00.000Z",
      ...
    }
  ],
  "metadata": {
    "source": "external-calendar-app",
    "version": "1.0",
    "generated_at": "2025-11-15T12:00:00.000Z"
  }
}
```

### Alternative Formats Supported:
- **CSV** - For bulk imports via spreadsheet
- **iCal (.ics)** - For calendar application compatibility
- **Google Calendar API** - Direct integration
- **Klaviyo Campaign Export** - Native format alignment

---

## Required Fields

These fields MUST be present for every event:

### 1. `id` (string)
- **Purpose**: Unique identifier for event tracking and updates
- **Format**: UUID, alphanumeric string, or external system ID
- **Requirements**:
  - Must be globally unique across all imports
  - Should be stable (same event = same ID on re-import)
  - Maximum length: 255 characters
- **Example**: `"campaign-2025-12-holiday-email-01"`

### 2. `name` (string)
- **Purpose**: Display name of the campaign/event
- **Requirements**:
  - Must be human-readable
  - Should be descriptive and specific
  - Maximum length: 500 characters
  - Avoid generic names like "Email #1"
- **Good Examples**:
  - `"Black Friday Sale - Early Access VIP Email"`
  - `"New Product Launch: Winter Collection SMS"`
  - `"Re-engagement Campaign: 90-Day Inactive Users"`
- **Bad Examples**:
  - `"Email"` (too generic)
  - `"Campaign 1"` (not descriptive)
  - `"Test"` (unclear purpose)

### 3. `date` (ISO 8601 DateTime string)
- **Purpose**: Scheduled send date and time
- **Format**: `YYYY-MM-DDTHH:mm:ss.sssZ`
- **Requirements**:
  - Must be valid ISO 8601 format
  - Should include timezone (UTC recommended)
  - Must be a future date for scheduled campaigns
- **Examples**:
  - `"2025-12-15T10:00:00.000Z"` (December 15, 2025 at 10:00 AM UTC)
  - `"2025-12-25T14:30:00-05:00"` (December 25, 2025 at 2:30 PM EST)

### 4. `channel` (enum string)
- **Purpose**: Communication channel for the campaign
- **Allowed Values**:
  - `"email"` - Email campaigns
  - `"sms"` - SMS/text messaging
  - `"push"` - Push notifications
  - `"in-app"` - In-app messages
  - `"webhook"` - Webhook/API triggers
- **Requirements**: Must be lowercase, exact match
- **Default**: `"email"` if not specified

### 5. `type` (enum string)
- **Purpose**: Campaign category/purpose
- **Allowed Values**:
  - `"promotional"` - Sales, discounts, offers
  - `"newsletter"` - Regular content updates
  - `"transactional"` - Order confirmations, receipts
  - `"educational"` - How-to guides, tips
  - `"announcement"` - Product launches, news
  - `"lifecycle"` - Welcome series, onboarding
  - `"re-engagement"` - Win-back campaigns
  - `"seasonal"` - Holiday, seasonal events
  - `"custom"` - Other campaign types
- **Requirements**: Must be lowercase, exact match
- **Default**: `"promotional"` if not specified

---

## Recommended Fields

These fields significantly enhance calendar functionality and should be included when available:

### 6. `time` (string)
- **Purpose**: Human-readable send time (complements `date`)
- **Format**: `"HH:MM AM/PM"` or `"HH:MM"`
- **Examples**: `"10:00 AM"`, `"14:30"`, `"9:00 PM"`
- **Notes**: Extracted automatically from `date` if not provided

### 7. `description` (string)
- **Purpose**: Detailed campaign description
- **Recommendations**:
  - Include campaign objective
  - Mention target audience
  - Note key messaging points
  - Reference any special offers
- **Maximum Length**: 2000 characters
- **Example**:
```text
"Early access Black Friday sale for VIP customers. Features 30% off winter collection with free shipping. Targets customers who purchased in last 90 days with average order value > $100. Email highlights limited-time offer and exclusive VIP benefits."
```

### 8. `status` (enum string)
- **Purpose**: Campaign workflow status
- **Allowed Values**:
  - `"draft"` - Being created/edited
  - `"scheduled"` - Approved and scheduled
  - `"sent"` - Already deployed
  - `"paused"` - Temporarily stopped
  - `"cancelled"` - Cancelled campaign
- **Default**: `"scheduled"`

### 9. `client_id` (string)
- **Purpose**: Associate event with specific client/brand
- **Format**: Must match existing EmailPilot client ID
- **Example**: `"buca-di-beppo"`, `"client-abc-123"`
- **Required for**: Multi-client calendars

### 10. `client_name` (string)
- **Purpose**: Human-readable client/brand name
- **Example**: `"Buca di Beppo"`, `"ACME Corporation"`
- **Auto-resolved**: If `client_id` provided

---

## Optional Enrichment Fields

These fields enable advanced features, AI assistance, and richer analytics:

### Campaign Performance & Goals

#### 11. `goal` (object)
```json
{
  "type": "revenue" | "engagement" | "conversions" | "clicks" | "opens",
  "target": 50000,
  "unit": "dollars" | "count" | "percentage"
}
```
- **Purpose**: Define success metrics
- **Example**:
```json
{
  "goal": {
    "type": "revenue",
    "target": 50000,
    "unit": "dollars"
  }
}
```

#### 12. `estimated_reach` (number)
- **Purpose**: Expected audience size
- **Example**: `15000` (15,000 recipients)

#### 13. `priority` (enum string)
- **Purpose**: Campaign importance level
- **Values**: `"low"`, `"normal"`, `"high"`, `"critical"`
- **Default**: `"normal"`

### Audience & Targeting

#### 14. `audience_segments` (array of strings)
- **Purpose**: Target audience segments
- **Example**:
```json
["VIP Customers", "90-Day Active", "Email Subscribers"]
```

#### 15. `exclusion_segments` (array of strings)
- **Purpose**: Segments to exclude
- **Example**:
```json
["Recently Purchased", "Email Unsubscribed"]
```

#### 16. `audience_size` (number)
- **Purpose**: Actual segment size after filters
- **Example**: `12458`

### Content & Messaging

#### 17. `subject_line` (string)
- **Purpose**: Email subject line (email channel only)
- **Maximum Length**: 150 characters
- **Example**: `"🎁 VIP Early Access: Black Friday Starts NOW"`

#### 18. `preview_text` (string)
- **Purpose**: Email preview/pre-header text
- **Maximum Length**: 255 characters
- **Example**: `"Your exclusive 30% off code expires in 24 hours"`

#### 19. `message_body` (string)
- **Purpose**: Campaign message content
- **Format**: Plain text or HTML (indicate with `content_type`)
- **Maximum Length**: 100,000 characters

#### 20. `content_type` (enum string)
- **Purpose**: Message format type
- **Values**: `"text/plain"`, `"text/html"`, `"markdown"`
- **Default**: `"text/html"`

#### 21. `call_to_action` (object)
```json
{
  "text": "Shop Now",
  "url": "https://example.com/sale",
  "type": "primary" | "secondary"
}
```

### Visual Assets

#### 22. `thumbnail_url` (string)
- **Purpose**: Preview image for calendar display
- **Format**: Full URL to image
- **Recommendations**:
  - Minimum: 300x200px
  - Optimal: 1200x630px (social share size)
  - Formats: JPG, PNG, WebP
- **Example**: `"https://cdn.example.com/campaigns/thumbnails/black-friday-2025.jpg"`

#### 23. `creative_assets` (array of objects)
```json
[
  {
    "type": "hero_image",
    "url": "https://cdn.example.com/hero.jpg",
    "alt_text": "Winter collection preview"
  },
  {
    "type": "product_image",
    "url": "https://cdn.example.com/product-1.jpg",
    "alt_text": "Featured product"
  }
]
```

### Design & Templates

#### 24. `template_id` (string)
- **Purpose**: Reference to email template
- **Example**: `"template-holiday-sale-v2"`

#### 25. `template_name` (string)
- **Purpose**: Human-readable template name
- **Example**: `"Holiday Sale - 2 Column Layout"`

#### 26. `theme` (string)
- **Purpose**: Visual theme or brand style
- **Example**: `"winter-2025"`, `"brand-primary"`

### Campaign Relationships

#### 27. `campaign_series` (string)
- **Purpose**: Group related campaigns
- **Example**: `"black-friday-2025"`, `"welcome-series"`

#### 28. `parent_campaign_id` (string)
- **Purpose**: Link to parent campaign (for A/B tests, follow-ups)
- **Example**: `"campaign-parent-001"`

#### 29. `variant_type` (enum string)
- **Purpose**: Identify test variants
- **Values**: `"control"`, `"variant_a"`, `"variant_b"`, `"variant_c"`

### Automation & Triggers

#### 30. `trigger_type` (enum string)
- **Purpose**: How campaign is initiated
- **Values**:
  - `"scheduled"` - Time-based
  - `"behavioral"` - User action triggered
  - `"api"` - External system trigger
  - `"manual"` - Admin-initiated

#### 31. `trigger_conditions` (array of objects)
```json
[
  {
    "condition": "user_action",
    "action": "abandoned_cart",
    "timeframe": "24_hours"
  }
]
```

#### 32. `automation_flow_id` (string)
- **Purpose**: Link to marketing automation flow
- **Example**: `"flow-abandoned-cart-recovery"`

### Integration & Tracking

#### 33. `external_id` (string)
- **Purpose**: ID in external system (Klaviyo, HubSpot, etc.)
- **Example**: `"klaviyo-campaign-abc123"`

#### 34. `tracking_parameters` (object)
```json
{
  "utm_source": "emailpilot",
  "utm_medium": "email",
  "utm_campaign": "black-friday-2025",
  "utm_content": "vip-early-access"
}
```

#### 35. `tags` (array of strings)
- **Purpose**: Flexible categorization and filtering
- **Example**:
```json
["black-friday", "vip", "limited-time", "high-priority"]
```

### Compliance & Approval

#### 36. `approval_status` (enum string)
- **Purpose**: Approval workflow state
- **Values**: `"pending"`, `"approved"`, `"rejected"`, `"revision_needed"`

#### 37. `approved_by` (string)
- **Purpose**: Name/email of approver
- **Example**: `"john.doe@example.com"`

#### 38. `approval_date` (ISO 8601 DateTime)
- **Purpose**: When campaign was approved
- **Example**: `"2025-11-14T15:30:00.000Z"`

#### 39. `compliance_notes` (string)
- **Purpose**: Legal/regulatory compliance information
- **Example**: `"CAN-SPAM compliant, GDPR consent verified"`

### Metadata & Administration

#### 40. `created_by` (string)
- **Purpose**: Campaign creator name/email
- **Example**: `"marketing@example.com"`

#### 41. `created_at` (ISO 8601 DateTime)
- **Purpose**: Event creation timestamp
- **Example**: `"2025-11-01T09:00:00.000Z"`

#### 42. `updated_by` (string)
- **Purpose**: Last editor name/email

#### 43. `updated_at` (ISO 8601 DateTime)
- **Purpose**: Last modification timestamp

#### 44. `notes` (string)
- **Purpose**: Internal notes and comments
- **Maximum Length**: 5000 characters

#### 45. `custom_fields` (object)
- **Purpose**: Application-specific data
- **Format**: Key-value pairs
- **Example**:
```json
{
  "internal_cost": 500,
  "agency_fee": 150,
  "designer": "Jane Smith",
  "copywriter": "Bob Johnson"
}
```

---

## Channel-Specific Fields

### Email-Only Fields

#### `from_name` (string)
- Sender display name
- Example: `"Buca di Beppo Marketing"`

#### `from_email` (string)
- Sender email address
- Example: `"marketing@bucadibeppo.com"`

#### `reply_to` (string)
- Reply-to email address
- Example: `"support@bucadibeppo.com"`

#### `preheader` (string)
- Email preheader text (alias for `preview_text`)

### SMS-Only Fields

#### `message_length` (number)
- Character count
- Example: `145`

#### `segment_count` (number)
- Number of SMS segments
- Example: `1` (1-160 chars), `2` (161-320 chars)

#### `from_phone` (string)
- Sending phone number or short code
- Example: `"+12125551234"` or `"54321"`

### Push Notification Fields

#### `push_title` (string)
- Notification title
- Maximum: 65 characters

#### `push_body` (string)
- Notification message
- Maximum: 240 characters

#### `deep_link` (string)
- App deep link URL
- Example: `"myapp://products/winter-collection"`

#### `badge_count` (number)
- iOS badge number
- Example: `3`

---

## Campaign Type Specifications

### Promotional Campaigns

**Recommended Fields**:
- `goal` - Revenue or conversion target
- `call_to_action` - Clear CTA
- `tracking_parameters` - UTM codes
- `offer_details` (custom field) - Discount amount, code, expiration

**Example**:
```json
{
  "type": "promotional",
  "goal": {
    "type": "revenue",
    "target": 100000,
    "unit": "dollars"
  },
  "call_to_action": {
    "text": "Shop 30% Off",
    "url": "https://example.com/sale?code=VIP30"
  },
  "custom_fields": {
    "offer_code": "VIP30",
    "discount_percentage": 30,
    "offer_expires": "2025-12-20T23:59:59Z"
  }
}
```

### Transactional Campaigns

**Recommended Fields**:
- `trigger_type` - Usually `"behavioral"` or `"api"`
- `priority` - Often `"high"` or `"critical"`
- `compliance_notes` - Legal requirements

**Example**:
```json
{
  "type": "transactional",
  "trigger_type": "api",
  "priority": "critical",
  "compliance_notes": "CAN-SPAM exempt - transactional",
  "subject_line": "Order Confirmation #12345"
}
```

### Lifecycle Campaigns

**Recommended Fields**:
- `campaign_series` - Group the series
- `automation_flow_id` - Link to flow
- `trigger_conditions` - Entry criteria

**Example**:
```json
{
  "type": "lifecycle",
  "campaign_series": "welcome-series",
  "automation_flow_id": "flow-welcome-7day",
  "trigger_conditions": [
    {
      "condition": "list_subscription",
      "list": "newsletter",
      "delay": "1_day"
    }
  ]
}
```

---

## AI Assistant Integration

EmailPilot's Ask EmailPilot AI can leverage rich data for intelligent campaign management:

### AI-Enhanced Fields

#### 46. `ai_suggestions_enabled` (boolean)
- **Purpose**: Allow AI to suggest optimizations
- **Default**: `true`

#### 47. `ai_context` (object)
```json
{
  "campaign_objective": "Increase Q4 revenue from VIP segment",
  "target_emotion": "urgency and exclusivity",
  "brand_voice": "friendly, upscale, family-oriented",
  "competitive_context": "Black Friday market saturation"
}
```

#### 48. `optimization_history` (array of objects)
```json
[
  {
    "timestamp": "2025-11-10T10:00:00Z",
    "optimization_type": "subject_line",
    "original": "Black Friday Sale",
    "optimized": "🎁 VIP Early Access: Black Friday Starts NOW",
    "reason": "Increased urgency and exclusivity",
    "performance_lift": 23.5
  }
]
```

### Natural Language Commands

When providing rich data, the AI can respond to commands like:

- `"Move all Black Friday campaigns to week of Dec 15"`
- `"Show me all campaigns with revenue goal > $50k"`
- `"Create a follow-up email 3 days after the Holiday Sale campaign"`
- `"What's the best send time for VIP segment emails?"`

**Required fields for AI commands**:
- `tags` - For filtering and grouping
- `campaign_series` - For related campaigns
- `goal` - For performance queries
- `audience_segments` - For targeting optimization

---

## Date and Time Formatting

### ISO 8601 Standard

**Full Format**: `YYYY-MM-DDTHH:mm:ss.sssZ`

**Components**:
- `YYYY` - 4-digit year (e.g., 2025)
- `MM` - 2-digit month (01-12)
- `DD` - 2-digit day (01-31)
- `T` - Date/time separator (literal)
- `HH` - 2-digit hour, 24-hour format (00-23)
- `mm` - 2-digit minutes (00-59)
- `ss` - 2-digit seconds (00-59)
- `.sss` - Milliseconds (optional)
- `Z` - UTC timezone indicator (or `±HH:mm` for offset)

### Examples

**UTC Timezone**:
```
2025-12-15T10:00:00.000Z       // December 15, 2025, 10:00 AM UTC
2025-01-01T00:00:00Z           // January 1, 2025, midnight UTC
```

**Timezone Offsets**:
```
2025-12-15T10:00:00-05:00      // 10:00 AM EST (UTC-5)
2025-12-15T10:00:00+09:00      // 10:00 AM JST (UTC+9)
```

### Timezone Recommendations

1. **Always include timezone** - Don't use naive datetimes
2. **Prefer UTC** - Convert local times to UTC for storage
3. **Document timezone** - Specify in metadata if using offsets
4. **Handle DST** - Account for daylight saving time transitions

---

## Import Formats

### JSON Format (Recommended)

**File Extension**: `.json`

**Structure**:
```json
{
  "metadata": {
    "source": "external-app-name",
    "version": "1.0",
    "generated_at": "2025-11-15T12:00:00.000Z",
    "client_id": "buca-di-beppo",
    "import_mode": "merge" | "replace" | "append"
  },
  "events": [
    {
      "id": "event-001",
      "name": "Campaign Name",
      "date": "2025-12-15T10:00:00.000Z",
      "channel": "email",
      "type": "promotional",
      ...
    }
  ]
}
```

### CSV Format

**File Extension**: `.csv`

**Header Row** (required):
```csv
id,name,date,time,channel,type,description,status,client_id,goal_type,goal_target,audience_segments,tags,priority
```

**Data Rows**:
```csv
event-001,"Black Friday Sale",2025-12-15T10:00:00.000Z,10:00 AM,email,promotional,"VIP early access sale",scheduled,buca-di-beppo,revenue,50000,"VIP Customers|Email Subscribers","black-friday|vip",high
```

**CSV Notes**:
- Quote strings containing commas
- Array values (segments, tags) use pipe `|` separator
- Nested objects (goal, CTA) flatten with underscore: `goal_type`, `goal_target`

### iCal Format (.ics)

**File Extension**: `.ics`

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//EmailPilot//Calendar Import//EN
BEGIN:VEVENT
UID:event-001
DTSTAMP:20251115T120000Z
DTSTART:20251215T100000Z
SUMMARY:Black Friday Sale - VIP Early Access
DESCRIPTION:VIP early access campaign for Black Friday
CATEGORIES:promotional,email,vip
STATUS:TENTATIVE
X-EMAILPILOT-CHANNEL:email
X-EMAILPILOT-CLIENT:buca-di-beppo
X-EMAILPILOT-GOAL-TYPE:revenue
X-EMAILPILOT-GOAL-TARGET:50000
END:VEVENT
END:VCALENDAR
```

**Custom iCal Properties**:
- `X-EMAILPILOT-*` - Custom fields for EmailPilot-specific data

### Google Calendar Integration

**API Endpoint**: `/api/calendar/import/google`

**Method**: POST

**Body**:
```json
{
  "calendar_id": "primary",
  "date_range": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  },
  "filters": {
    "categories": ["email-campaign", "sms-campaign"]
  }
}
```

### Klaviyo Campaign Export

**API Endpoint**: `/api/calendar/import/klaviyo`

**Method**: POST

**Body**:
```json
{
  "klaviyo_api_key": "pk_xxx",
  "campaign_status": ["scheduled", "draft"],
  "date_range": {
    "start": "2025-12-01",
    "end": "2025-12-31"
  }
}
```

---

## Validation Rules

### Required Field Validation

**Rule**: All required fields must be present and non-null

**Error Response**:
```json
{
  "status": "error",
  "code": "MISSING_REQUIRED_FIELD",
  "message": "Missing required field: 'name'",
  "event_id": "event-001",
  "field": "name"
}
```

### Data Type Validation

**Rule**: Fields must match expected data types

**Examples**:
- `date` must be valid ISO 8601 string
- `goal.target` must be number, not string
- `tags` must be array, not string

**Error Response**:
```json
{
  "status": "error",
  "code": "INVALID_DATA_TYPE",
  "message": "Field 'goal.target' must be a number, received string",
  "event_id": "event-001",
  "field": "goal.target",
  "expected_type": "number",
  "received_type": "string"
}
```

### Enum Validation

**Rule**: Enum fields must use allowed values

**Error Response**:
```json
{
  "status": "error",
  "code": "INVALID_ENUM_VALUE",
  "message": "Invalid value 'push_notification' for field 'channel'. Allowed values: email, sms, push, in-app, webhook",
  "event_id": "event-001",
  "field": "channel",
  "received_value": "push_notification",
  "allowed_values": ["email", "sms", "push", "in-app", "webhook"]
}
```

### Date Validation

**Rule**: Dates must be valid and reasonable

**Checks**:
- Valid ISO 8601 format
- Date is parseable
- Future dates for scheduled campaigns
- Not more than 2 years in future (configurable)

**Error Response**:
```json
{
  "status": "error",
  "code": "INVALID_DATE",
  "message": "Invalid date format '2025-13-45'. Expected ISO 8601 format YYYY-MM-DDTHH:mm:ss.sssZ",
  "event_id": "event-001",
  "field": "date"
}
```

### Business Logic Validation

**Rule**: Data must make business sense

**Examples**:
- SMS messages < 1600 characters
- Email subject lines < 150 characters
- Goal targets > 0
- Audience size > 0

---

## Examples

### Example 1: Minimal Email Campaign

**Use Case**: Simple promotional email with only required fields

```json
{
  "id": "promo-001",
  "name": "Weekly Newsletter - November",
  "date": "2025-11-20T10:00:00.000Z",
  "channel": "email",
  "type": "newsletter"
}
```

### Example 2: Rich Promotional Campaign

**Use Case**: Black Friday sale with full metadata

```json
{
  "id": "bf-2025-vip-early",
  "name": "Black Friday VIP Early Access",
  "date": "2025-11-27T06:00:00.000Z",
  "time": "6:00 AM",
  "channel": "email",
  "type": "promotional",
  "status": "scheduled",
  "priority": "high",

  "description": "Exclusive 48-hour early access to Black Friday deals for VIP customers. 30% off entire store with free shipping on orders $50+",

  "client_id": "buca-di-beppo",
  "client_name": "Buca di Beppo",

  "goal": {
    "type": "revenue",
    "target": 150000,
    "unit": "dollars"
  },

  "audience_segments": [
    "VIP Customers",
    "Purchased Last 90 Days",
    "Email Subscribers"
  ],
  "audience_size": 8542,
  "estimated_reach": 8200,

  "subject_line": "🎁 VIP Only: Black Friday Starts NOW (48hrs Early)",
  "preview_text": "Your exclusive code: VIP30 expires Friday at midnight",
  "from_name": "Buca di Beppo",
  "from_email": "marketing@bucadibeppo.com",
  "reply_to": "support@bucadibeppo.com",

  "call_to_action": {
    "text": "Shop VIP Sale",
    "url": "https://bucadibeppo.com/black-friday?code=VIP30",
    "type": "primary"
  },

  "thumbnail_url": "https://cdn.bucadibeppo.com/campaigns/bf-2025-hero.jpg",

  "template_id": "holiday-sale-2col",
  "template_name": "Holiday Sale - 2 Column Layout",

  "campaign_series": "black-friday-2025",
  "trigger_type": "scheduled",

  "tracking_parameters": {
    "utm_source": "emailpilot",
    "utm_medium": "email",
    "utm_campaign": "black-friday-2025",
    "utm_content": "vip-early-access"
  },

  "tags": ["black-friday", "vip", "high-priority", "revenue-driver"],

  "approval_status": "approved",
  "approved_by": "john.marketing@bucadibeppo.com",
  "approval_date": "2025-11-15T14:30:00.000Z",

  "created_by": "jane.doe@bucadibeppo.com",
  "created_at": "2025-11-01T10:00:00.000Z",
  "updated_by": "jane.doe@bucadibeppo.com",
  "updated_at": "2025-11-14T16:45:00.000Z",

  "notes": "Tested subject lines with Litmus. Hero image optimized for mobile. Segment excludes recent purchasers to avoid overlap with general BF campaign.",

  "custom_fields": {
    "offer_code": "VIP30",
    "discount_percentage": 30,
    "offer_expires": "2025-11-29T23:59:59Z",
    "free_shipping_threshold": 50,
    "designer": "Sarah Designer",
    "copywriter": "Mike Writer",
    "estimated_cost": 450
  }
}
```

### Example 3: SMS Campaign

```json
{
  "id": "sms-flash-sale-001",
  "name": "Flash Sale Alert - 4 Hour Only",
  "date": "2025-12-10T12:00:00.000Z",
  "time": "12:00 PM",
  "channel": "sms",
  "type": "promotional",
  "status": "scheduled",
  "priority": "high",

  "description": "Time-sensitive flash sale notification for mobile subscribers",

  "client_id": "buca-di-beppo",

  "message_body": "⚡ FLASH SALE! 4 hours only - 40% off lunch menu. Show this text in-store or use code FLASH40 online. Ends 4pm! bucadibeppo.com/flash",
  "message_length": 145,
  "segment_count": 1,

  "from_phone": "+12125551234",

  "audience_segments": ["SMS Subscribers", "Lunch Customers"],
  "audience_size": 2340,

  "goal": {
    "type": "conversions",
    "target": 200,
    "unit": "count"
  },

  "call_to_action": {
    "text": "Redeem Now",
    "url": "https://bucadibeppo.com/flash",
    "type": "primary"
  },

  "tracking_parameters": {
    "utm_source": "sms",
    "utm_medium": "flash-sale",
    "utm_campaign": "lunch-promo-dec"
  },

  "tags": ["flash-sale", "sms", "time-sensitive"],

  "custom_fields": {
    "offer_code": "FLASH40",
    "offer_duration_hours": 4,
    "compliance_checked": true
  }
}
```

### Example 4: Automated Lifecycle Email

```json
{
  "id": "welcome-day1-001",
  "name": "Welcome Series - Day 1",
  "date": "2025-12-01T09:00:00.000Z",
  "channel": "email",
  "type": "lifecycle",
  "status": "draft",

  "description": "First email in 7-day welcome series for new subscribers",

  "client_id": "buca-di-beppo",

  "campaign_series": "welcome-series-7day",
  "automation_flow_id": "flow-welcome-001",

  "trigger_type": "behavioral",
  "trigger_conditions": [
    {
      "condition": "list_subscription",
      "list": "newsletter",
      "delay": "0_hours"
    }
  ],

  "subject_line": "Welcome to the Buca Family! Here's Your Gift 🎁",
  "preview_text": "Enjoy 15% off your first visit - on us!",

  "goal": {
    "type": "engagement",
    "target": 45,
    "unit": "percentage"
  },

  "audience_segments": ["New Subscribers"],

  "template_id": "welcome-v3",

  "tags": ["welcome", "automation", "first-purchase"],

  "custom_fields": {
    "series_position": 1,
    "series_total": 7,
    "offer_code": "WELCOME15",
    "offer_expiration_days": 14
  }
}
```

### Example 5: Bulk Import (JSON Array)

```json
{
  "metadata": {
    "source": "external-calendar-pro",
    "version": "1.0",
    "generated_at": "2025-11-15T12:00:00.000Z",
    "client_id": "buca-di-beppo",
    "import_mode": "merge",
    "total_events": 3
  },
  "events": [
    {
      "id": "dec-newsletter",
      "name": "December Newsletter",
      "date": "2025-12-01T10:00:00.000Z",
      "channel": "email",
      "type": "newsletter",
      "tags": ["monthly", "content"]
    },
    {
      "id": "holiday-promo",
      "name": "Holiday Gift Guide",
      "date": "2025-12-15T09:00:00.000Z",
      "channel": "email",
      "type": "promotional",
      "goal": {
        "type": "revenue",
        "target": 75000,
        "unit": "dollars"
      },
      "tags": ["holiday", "revenue-driver"]
    },
    {
      "id": "new-year-sms",
      "name": "New Year's Eve Reservation Reminder",
      "date": "2025-12-30T10:00:00.000Z",
      "channel": "sms",
      "type": "announcement",
      "tags": ["holiday", "reservations"]
    }
  ]
}
```

---

## Best Practices

### 1. Data Quality

**Completeness**:
- Provide all required fields
- Include recommended fields when available
- Add optional fields for enhanced functionality

**Accuracy**:
- Validate data before export
- Use precise dates and times
- Ensure IDs are unique and stable

**Consistency**:
- Use consistent naming conventions
- Standardize enum values (lowercase)
- Maintain uniform date formats

### 2. Field Population Guidelines

**Name Field**:
- Be specific and descriptive
- Include campaign purpose
- Mention key differentiators
- Good: `"Black Friday VIP Early Access Email"`
- Bad: `"Email 1"`, `"Campaign"`, `"Test"`

**Description Field**:
- Include campaign objective
- Mention target audience
- List key messaging points
- Reference offers/promotions
- Note any special requirements

**Tags**:
- Use consistent taxonomy
- Include campaign type tags
- Add priority/status tags
- Reference related initiatives
- Example: `["black-friday", "vip", "email", "revenue-driver", "approved"]`

### 3. Audience Segments

**Naming**:
- Use human-readable names
- Be specific about criteria
- Avoid abbreviations
- Good: `"VIP Customers - Purchased Last 90 Days"`
- Bad: `"VIP_90D"`, `"Segment_A"`

**Documentation**:
- Include segment definitions
- Note size/reach estimates
- Document exclusion criteria

### 4. Goals and Metrics

**SMART Goals**:
- Specific: Define exact metric
- Measurable: Include numeric target
- Achievable: Set realistic targets
- Relevant: Align with campaign type
- Time-bound: Link to campaign date

**Examples**:
```json
// Good
{
  "goal": {
    "type": "revenue",
    "target": 50000,
    "unit": "dollars"
  }
}

// Better
{
  "goal": {
    "type": "revenue",
    "target": 50000,
    "unit": "dollars"
  },
  "estimated_reach": 10000,
  "expected_conversion_rate": 5.0,
  "average_order_value": 100
}
```

### 5. Template and Asset References

**Use Absolute URLs**:
- Always provide full URLs for images
- Include protocol (https://)
- Use CDN URLs when available
- Ensure URLs are publicly accessible (for import testing)

**Asset Optimization**:
- Optimize images before upload
- Use appropriate formats (WebP for web)
- Include alt text for accessibility
- Provide multiple sizes if available

### 6. Campaign Relationships

**Series and Flows**:
- Group related campaigns with `campaign_series`
- Link automation steps with `automation_flow_id`
- Reference parent campaigns for A/B tests
- Use consistent series naming

**Example Series**:
```json
// Email 1
{
  "id": "welcome-001",
  "name": "Welcome Email - Day 1",
  "campaign_series": "welcome-series-7day",
  "custom_fields": {
    "series_position": 1,
    "series_total": 7
  }
}

// Email 2
{
  "id": "welcome-002",
  "name": "Welcome Email - Day 3",
  "campaign_series": "welcome-series-7day",
  "custom_fields": {
    "series_position": 2,
    "series_total": 7
  }
}
```

### 7. Compliance and Approval

**Required Documentation**:
- Always include approval status
- Document approver name/email
- Note compliance requirements
- Track approval dates

**Legal Compliance**:
- Note CAN-SPAM compliance
- Document GDPR consent
- Include opt-out mechanisms
- Reference legal review

### 8. Performance Optimization

**Batch Imports**:
- Group events in batches of 50-100
- Use `import_mode` to control behavior
- Provide metadata for tracking
- Include error handling

**Import Modes**:
- `merge` - Update existing, add new (default)
- `replace` - Delete all, import provided
- `append` - Only add new, skip existing

### 9. Error Handling

**Graceful Degradation**:
- Required fields MUST be present
- Recommended fields enhance experience
- Optional fields are skipped if invalid
- Provide clear error messages

**Validation Response**:
```json
{
  "status": "partial_success",
  "imported": 45,
  "failed": 5,
  "errors": [
    {
      "event_id": "event-003",
      "field": "date",
      "error": "Invalid date format",
      "suggestion": "Use ISO 8601 format: YYYY-MM-DDTHH:mm:ss.sssZ"
    }
  ]
}
```

### 10. Testing

**Pre-Import Validation**:
- Test with small dataset first
- Validate all required fields
- Check enum values
- Verify date formats
- Test with single event before bulk

**Test Event**:
```json
{
  "id": "test-import-001",
  "name": "Test Import Event",
  "date": "2025-12-31T23:59:59.000Z",
  "channel": "email",
  "type": "custom",
  "tags": ["test", "do-not-send"],
  "status": "draft"
}
```

---

## API Endpoints

### Import Events

**Endpoint**: `POST /api/calendar/import`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer {api_key}
```

**Request Body**:
```json
{
  "metadata": {
    "source": "your-app-name",
    "version": "1.0",
    "client_id": "client-slug",
    "import_mode": "merge"
  },
  "events": [...]
}
```

**Response (Success)**:
```json
{
  "status": "success",
  "imported": 50,
  "updated": 10,
  "created": 40,
  "failed": 0,
  "processing_time_ms": 1234
}
```

**Response (Partial Success)**:
```json
{
  "status": "partial_success",
  "imported": 45,
  "updated": 8,
  "created": 37,
  "failed": 5,
  "errors": [...],
  "processing_time_ms": 1567
}
```

**Response (Error)**:
```json
{
  "status": "error",
  "code": "VALIDATION_ERROR",
  "message": "Multiple validation errors found",
  "errors": [...]
}
```

### Validate Import

**Endpoint**: `POST /api/calendar/import/validate`

**Purpose**: Test import without committing changes

**Request/Response**: Same as import endpoint, but no data is saved

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-15 | Initial specification document |

---

## Support and Contact

For questions about calendar import specifications:

- **Documentation**: `https://app.emailpilot.ai/docs/calendar-import`
- **API Reference**: `https://app.emailpilot.ai/api/docs`
- **Support Email**: `support@emailpilot.ai`
- **GitHub Issues**: `https://github.com/emailpilot/calendar-import/issues`

---

**Document Status**: ✅ Production Ready
**Maintained By**: EmailPilot Engineering Team
**Next Review**: 2026-02-15
