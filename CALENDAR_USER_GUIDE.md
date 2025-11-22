# EmailPilot Calendar - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Selecting a Client](#selecting-a-client)
3. [Viewing and Filtering Campaigns](#viewing-and-filtering-campaigns)
4. [Creating Campaigns Manually](#creating-campaigns-manually)
5. [Importing Campaign Data](#importing-campaign-data)
6. [Managing Multi-Day Campaigns](#managing-multi-day-campaigns)
7. [Calendar Features](#calendar-features)
8. [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### Accessing the Calendar
1. Navigate to `https://calendar.emailpilot.ai`
2. Click **"Login with Asana"** to authenticate
3. You'll be redirected back to the calendar after successful authentication

### Interface Overview
The EmailPilot Calendar interface consists of:
- **Top Navigation**: Client selector, date navigation, and action buttons
- **Filter Pills**: Email/SMS channel filters and affinity segment filters
- **Calendar Grid**: Monthly view with all campaigns displayed
- **Stats Panel**: Campaign counts and analytics

---

## Selecting a Client

### Step-by-Step
1. **Click the client dropdown** in the top-left corner
   - Shows all active clients with configured Klaviyo integration
   - Clients are listed alphabetically by name

2. **Select your client** from the dropdown
   - The calendar will load with the current month
   - Affinity segments for that client will appear as filter pills
   - Any existing campaigns will be displayed

3. **Client Information Displayed**:
   - Client name in the header
   - Affinity segments (if configured)
   - Channel filter pills (Email/SMS)

---

## Viewing and Filtering Campaigns

### Email and SMS Channel Filters

#### Using the Email Filter Pill
The **📧 Email** pill allows you to view only email campaigns:

1. **Click the "📧 Email" pill** above the calendar
   - The pill will highlight with a purple ring
   - The calendar will show only email campaigns
   - SMS campaigns will be hidden
   - A notification will confirm: "Showing only Email campaigns"

2. **Click again to remove the filter**
   - The calendar will show all campaigns again
   - Notification: "Showing all Email campaigns"

#### Using the SMS Filter Pill
The **📱 SMS** pill works identically for SMS campaigns:

1. **Click the "📱 SMS" pill**
   - Shows only SMS campaigns
   - Email campaigns are hidden
   - Notification: "Showing only SMS campaigns"

2. **Click again to remove the filter**
   - Shows all campaigns again

#### Channel Filter Behavior
- **Only one channel can be filtered at a time**
  - Clicking "Email" when "SMS" is active switches to Email filter
  - Clicking "SMS" when "Email" is active switches to SMS filter

- **Channel filters clear segment filters**
  - Activating a channel filter automatically clears any active segment filters
  - This ensures you see ALL campaigns of that channel type, not just specific segments

- **Visual feedback**
  - Active filters show a purple ring and background highlight
  - Toast notifications confirm filter changes

### Affinity Segment Filters

#### What Are Affinity Segments?
Affinity segments are your client's key audience groups (e.g., "VIP Customers", "New Subscribers", "Lapsed Users"). Each segment appears as a colored pill with an emoji and name.

#### Using Segment Filters

1. **Click any segment pill** to filter by that audience
   - Example: Click "🔥 VIP Customers"
   - The calendar shows only campaigns targeting VIP Customers
   - The segment pill highlights with a purple ring
   - Notification: "Filtering for VIP Customers"

2. **Filter by multiple segments**
   - Click additional segment pills to add more filters
   - The calendar shows campaigns targeting ANY of the selected segments
   - Example: Select both "VIP" and "New" to see campaigns for either group

3. **Remove segment filters**
   - Click an active segment pill to deactivate it
   - Click multiple times to remove all segment filters
   - Or click a channel filter to clear all segments at once

#### Segment Filter Behavior
- **Multiple segments can be active simultaneously**
  - Shows campaigns targeting any of the selected segments (OR logic)

- **Cannot combine with channel filters**
  - Activating a channel filter clears all segment filters
  - Activating a segment filter when a channel is active will keep only the segment filter

### Clearing All Filters
To see all campaigns with no filters:
1. Click any active filter pill to deactivate it
2. Or refresh the page to reset all filters

---

## Creating Campaigns Manually

### Opening the Campaign Creator

1. **Click any empty date** on the calendar
   - A modal will appear: "Create Campaign"
   - The selected date will be pre-filled

2. **Or click the "+" button** in the navigation bar
   - Opens the same modal
   - You'll need to select the date manually

### Filling Out Campaign Details

#### 1. Campaign Name (Required)
```
Enter a descriptive name for your campaign
Example: "Summer Sale - Email Blast"
```
- Be specific and descriptive
- Include the campaign type or offer
- Use consistent naming conventions across your team

#### 2. Campaign Type (Required)
Select from the dropdown:
- **Email**: Standard email campaign
- **SMS**: Text message campaign
- **Flash Sale**: Time-sensitive promotional offer
- **Promotional**: General promotional campaign
- **Nurturing**: Educational or relationship-building content
- **RRB**: Replenishment/Re-engagement campaign
- **Seasonal**: Holiday or seasonal campaign

The type determines the campaign's color on the calendar.

#### 3. Campaign Date (Required)
- **Click the date field** to open the date picker
- Select the launch date for your campaign
- Time zones are based on your client's configured timezone

#### 4. Target Segment (Optional)
Select the audience segment for this campaign:
- **All Subscribers**: Sends to entire list (default)
- **Client-specific segments**: Choose from configured affinity segments
  - Example: "VIP Customers", "New Subscribers", "Lapsed Users"

#### 5. Description (Optional)
```
Add campaign details, notes, or strategy
Example: "Announcing summer collection with 30% off. Sending to VIPs first."
```
- Use this for campaign notes and strategy
- Include key details like offers, creative direction, or A/B tests
- This helps your team understand campaign goals

### Multi-Day Campaign Options

#### Enable Multi-Day Campaign
Check the **"Multi-day campaign"** checkbox to create a campaign spanning multiple days.

**When to use**:
- Launch sequences (Day 1: Teaser, Day 2: Reveal, Day 3: Last Chance)
- Multi-touch campaigns (Email + SMS + Email)
- Week-long promotions

**See [Managing Multi-Day Campaigns](#managing-multi-day-campaigns)** for detailed instructions.

### Saving Your Campaign

1. **Click "Create Campaign"** button
   - The campaign appears on the calendar
   - The campaign is automatically saved to the cloud
   - A success notification appears

2. **Cancel Creation**
   - Click "Cancel" or click outside the modal
   - No campaign is created

---

## Importing Campaign Data

### When to Import Files
Import campaigns when you have:
- Campaigns planned in external tools (Google Sheets, Excel, Project Management tools)
- Bulk campaign data from another system
- Historical campaign data to visualize

### Supported File Formats
- **JSON** (`.json`): EmailPilot format or custom structures
- **CSV** (`.csv`): Standard spreadsheet format
- **Excel** (`.xlsx`, `.xls`): Excel workbooks
- **iCalendar** (`.ics`): Calendar exports from other tools

### Step-by-Step Import Process

#### Step 1: Open Import Modal
1. **Ensure a client is selected** first
2. **Click the "📄 Import File" button** in the top navigation
3. The import modal will appear

#### Step 2: Select File Type
1. **Choose the file type** from the dropdown:
   - JSON (EmailPilot Format)
   - CSV (Spreadsheet)
   - Excel (.xlsx)
   - iCalendar (.ics)

2. The file input will update to accept the chosen format

#### Step 3: Upload Your File

**Option A: Drag and Drop**
1. Drag your file from your computer
2. Drop it into the upload area
3. The file name will appear

**Option B: Click to Browse**
1. Click the upload area
2. Select your file from the file picker
3. Click "Open"

#### Step 4: Preview and Map Columns (CSV/Excel only)

For CSV and Excel files, you'll need to map columns:

1. **The system auto-detects common column names**:
   - Title: "Campaign Name", "Title", "Name", "Campaign"
   - Date: "Launch Date", "Date", "Start Date", "Schedule Date"
   - Type: "Type", "Campaign Type", "Category"
   - Content: "Description", "Content", "Notes"

2. **Review the column mapping**:
   - **Title Column** (required): Maps to campaign name
   - **Date Column** (required): Maps to campaign date
   - **Campaign Type Column** (optional): Maps to campaign type
   - **Description Column** (optional): Maps to campaign description

3. **Adjust mappings if needed**:
   - Click the dropdown for each field
   - Select the correct column from your file
   - Required fields must be mapped

#### Step 5: Import Events

1. **Click "📥 Import Events" button**
   - Processing indicator will show
   - The system parses your file
   - Events are normalized and added to calendar

2. **Success notification**:
   - Shows number of events imported
   - Example: "Successfully imported 24 events"

3. **Calendar updates automatically**:
   - All imported campaigns appear on the calendar
   - You can immediately filter by channel or segment
   - Changes are automatically saved to the cloud

### Import File Format Examples

#### JSON Format Example
```json
[
  {
    "title": "Summer Sale Launch",
    "date": "2024-06-15",
    "type": "email",
    "channel": "email",
    "content": "50% off summer collection for VIP customers",
    "segment": "vip_customers"
  },
  {
    "title": "Flash Sale Alert",
    "date": "2024-06-16",
    "type": "sms",
    "channel": "sms",
    "content": "24-hour flash sale notification"
  }
]
```

#### CSV Format Example
```csv
Campaign Name,Launch Date,Type,Description,Channel,Target Segment
Summer Sale Launch,2024-06-15,email,50% off summer collection,email,vip_customers
Flash Sale Alert,2024-06-16,sms,24-hour flash sale,sms,all_subscribers
Newsletter #45,2024-06-20,email,Monthly updates and tips,email,all_subscribers
```

### Troubleshooting Import Issues

#### "No valid events found in file"
- **Check date formats**: Must be YYYY-MM-DD or MM/DD/YYYY
- **Verify required fields**: Title and date are required for each event
- **Check file encoding**: Use UTF-8 encoding for special characters

#### "Please select a client first"
- You must select a client before importing
- Return to the calendar and choose a client from the dropdown

#### "Error importing file: [error message]"
- **JSON errors**: Validate your JSON syntax at jsonlint.com
- **CSV errors**: Ensure proper comma separation and quoted fields
- **Date parsing errors**: Use consistent date formats throughout the file

---

## Managing Multi-Day Campaigns

### What Are Multi-Day Campaigns?
Multi-day campaigns span multiple consecutive dates, appearing as a connected series on the calendar. Perfect for:
- Launch sequences
- Weekly promotions
- Multi-touch campaigns (Email → SMS → Email)
- Event countdowns

### Creating a Multi-Day Campaign

#### Step 1: Start Campaign Creation
1. Click a date on the calendar
2. Fill in campaign details (name, type, description)

#### Step 2: Enable Multi-Day Mode
1. **Check the "Multi-day campaign" checkbox**
2. Additional options will appear:
   - Days input field
   - Day labels section

#### Step 3: Set Campaign Duration
1. **Enter the number of days** (2-7 days supported)
   - Example: Enter "3" for a 3-day campaign

2. **The calendar preview updates**:
   - Shows the date range
   - Displays how the campaign will appear

#### Step 4: Customize Day Labels (Optional)
For each day of your campaign:

1. **Enter a custom label** for each day
   - Day 1: "Teaser Email"
   - Day 2: "Launch Email"
   - Day 3: "Last Chance SMS"

2. **Leave blank to use default labels**:
   - "Day 1 of 3"
   - "Day 2 of 3"
   - "Day 3 of 3"

#### Step 5: Create the Campaign
1. **Click "Create Campaign"**
2. The multi-day campaign appears on the calendar
3. Each day shows its label or "Day X of Y"

### Visual Indicators for Multi-Day Campaigns
- **First day**: Shows full campaign name + "Day 1"
- **Middle days**: Shows "Day 2", "Day 3", etc.
- **Last day**: Shows "Day X" (final day indicator)
- **Connected appearance**: All days use the same color and appear connected

### Editing Multi-Day Campaigns
To edit a multi-day campaign:
1. **Click any day** of the multi-day campaign
2. The campaign details modal opens
3. **Make your changes**:
   - Update name, type, or description
   - Changes apply to the entire multi-day series
4. **Click "Save Changes"**

### Deleting Multi-Day Campaigns
To delete a multi-day campaign:
1. **Click any day** of the multi-day campaign
2. Click the **"Delete"** button in the modal
3. **The entire series is deleted** (all days removed)
4. A confirmation notification appears

### Multi-Day Campaign Examples

#### Example 1: Product Launch Sequence
```
Day 1 (June 15): "Teaser - Coming Soon"
Day 2 (June 16): "Launch - New Collection"
Day 3 (June 17): "Last Chance - 24hr Only"
```

#### Example 2: Holiday Promotion
```
Day 1 (Dec 20): "Holiday Sale - Early Access Email"
Day 2 (Dec 21): "Holiday Sale - SMS Reminder"
Day 3 (Dec 22): "Holiday Sale - Final Hours Email"
Day 4 (Dec 23): "Holiday Sale - Last Call SMS"
```

#### Example 3: Re-engagement Campaign
```
Day 1: "We Miss You - Special Offer"
Day 2: "Your Exclusive 25% Off Code"
Day 3: "Reminder - Code Expires Tonight"
```

---

## Calendar Features

### Date Navigation

#### Month Navigation
- **Previous Month**: Click the "←" arrow
- **Next Month**: Click the "→" arrow
- **Current Month**: The month/year is displayed in the header

#### Today Button
- **Click "Today"** to jump to the current month
- Useful after navigating to future or past months

### Campaign Display

#### Campaign Colors
Campaigns are color-coded by type:
- **Email**: Blue (`bg-blue-200`)
- **SMS**: Orange (`bg-orange-200`)
- **Flash Sale**: Red (`bg-red-300`)
- **Promotional**: Red (`bg-red-300`)
- **Nurturing**: Green (`bg-green-100`)
- **RRB**: Red (`bg-red-300`)
- **Seasonal**: Purple (`bg-purple-200`)

#### Campaign Details
Click any campaign to view:
- Full campaign name
- Campaign type and date
- Target segment
- Description and notes
- Edit and delete options

### Statistics Panel

The stats panel shows:
- **Total Campaigns**: Count for the month
- **By Channel**: Email vs. SMS breakdown
- **By Type**: Distribution across campaign types
- **By Segment**: Which segments are targeted most

### Cloud Synchronization

#### Auto-Save
- All changes are automatically saved to the cloud
- No manual save button needed
- Changes sync in real-time

#### Loading States
- **Aviation animation**: Appears during save operations
- **Progress indicators**: Show during imports and loads

### Light/Dark Mode
Toggle between light and dark themes:
- **Click the theme toggle** in the top-right corner
- Preference is saved locally
- Applies to all calendar elements

---

## Tips and Best Practices

### Organizing Campaigns

#### Use Consistent Naming
```
Good: "Summer Sale - VIP Early Access - Email"
Good: "Newsletter #45 - Product Updates"
Bad: "campaign1"
Bad: "email"
```

#### Leverage Segment Targeting
- Assign segments to campaigns for better filtering
- Use "All Subscribers" sparingly
- Target specific audiences when possible

#### Color-Code by Type
- Use campaign types consistently
- The colors help visualize your campaign mix at a glance

### Planning Strategies

#### Balance Email and SMS
- Use the channel filters to check Email/SMS ratio
- Avoid over-sending on either channel
- Mix channels for multi-touch campaigns

#### Check for Gaps
- Use filters to view each channel separately
- Look for weeks with no campaigns
- Plan nurturing content for slow periods

#### Review by Segment
- Filter by each affinity segment
- Ensure each audience receives regular communication
- Don't neglect smaller segments

### Import Best Practices

#### Prepare Your Data
- Use consistent date formats (YYYY-MM-DD recommended)
- Include all required fields (title, date)
- Add channel and segment info for better filtering

#### Test with Small Files First
- Import 2-3 campaigns to test formatting
- Verify dates appear correctly
- Check that filters work as expected
- Then import the full file

#### Keep Backups
- Save a copy of your import file
- Use version control for JSON files
- Keep a master spreadsheet of campaigns

### Collaboration Tips

#### Document Campaign Strategy
- Use the description field to explain campaign goals
- Note A/B test variables
- Include creative direction or offers

#### Use Multi-Day Campaigns for Sequences
- Plan launch sequences ahead of time
- Create multi-day campaigns for cohesive experiences
- Label each day clearly

#### Review Before Launch
- Use filters to review each channel
- Check campaign density (not too many on one day)
- Verify segment targeting is correct

---

## Troubleshooting

### Campaigns Not Appearing

**Issue**: Created a campaign but don't see it on the calendar

**Solutions**:
1. Check if a filter is active (Email/SMS/Segment pill highlighted)
2. Verify you're viewing the correct month
3. Click "Today" to return to the current month
4. Refresh the page if needed

### Import Not Working

**Issue**: Import button is disabled or file won't process

**Solutions**:
1. Ensure a client is selected first
2. Check file format matches selected type (JSON/CSV/Excel/ICS)
3. Verify file size is under 5MB
4. Check that dates are in valid format

### Filter Pills Not Responding

**Issue**: Clicking filter pills doesn't update the calendar

**Solutions**:
1. Refresh the page
2. Check browser console for errors (F12)
3. Ensure JavaScript is enabled
4. Try a different browser

### Authentication Issues

**Issue**: Can't log in or session expires

**Solutions**:
1. Log out completely from Asana
2. Clear browser cookies for calendar.emailpilot.ai
3. Try the login flow again
4. Verify your Asana account has access to EmailPilot

---

## Keyboard Shortcuts

### Navigation
- **Left Arrow**: Previous month
- **Right Arrow**: Next month
- **T**: Jump to today
- **Escape**: Close any open modal

### Actions
- **N**: Create new campaign (opens modal)
- **I**: Open import modal
- **F**: Toggle filter menu (when implemented)

---

## Getting Help

### Support Resources
- **Technical Documentation**: FILE_IMPORT_TECH_SPECS.md
- **Integration Guide**: EXTERNAL_DATA_INTEGRATION_GUIDE.md
- **GitHub Issues**: Report bugs and request features

### Common Questions

**Q: Can I export my calendar data?**
A: Currently, export functionality is planned for a future release. For now, campaigns are stored in the cloud and accessible through the calendar interface.

**Q: How many campaigns can I create?**
A: There is no hard limit. The calendar is designed to handle hundreds of campaigns per client.

**Q: Can I bulk edit campaigns?**
A: Bulk editing is not currently supported. Edit campaigns individually or re-import with updated data.

**Q: Can I share my calendar with team members?**
A: Anyone with Asana access and EmailPilot permissions can view and edit the calendar for your clients.

**Q: What timezone are campaigns displayed in?**
A: Campaigns use the timezone configured for each client. Check with your account manager if you need to update your client's timezone.

---

## Appendix: Field Reference

### Campaign Object Structure
```javascript
{
  id: "string",              // Auto-generated unique ID
  name: "string",            // Campaign name (required)
  type: "string",            // Campaign type (required)
  date: "Date",              // Launch date (required)
  channel: "email" | "sms",  // Communication channel
  description: "string",     // Campaign notes (optional)
  segment: "string",         // Target segment (optional)
  color: "string",           // TailwindCSS color class
  isMultiDay: boolean,       // Multi-day campaign flag
  dayLabel: "string",        // Custom day label for multi-day
  imported: boolean          // Was this campaign imported?
}
```

### Import File Schema (JSON)
```json
{
  "title": "string (required)",
  "date": "string YYYY-MM-DD (required)",
  "type": "string (optional)",
  "channel": "email | sms (optional)",
  "content": "string (optional)",
  "segment": "string (optional)",
  "color": "string (optional)",
  "send_time": "string (optional)"
}
```

### CSV Column Mapping
| Calendar Field | Accepted Column Names |
|----------------|----------------------|
| Title | Campaign Name, Title, Name, Campaign |
| Date | Launch Date, Date, Start Date, Schedule Date, Time |
| Type | Type, Campaign Type, Category, Kind |
| Content | Description, Content, Notes, Details |
| Channel | Channel, Medium, Platform |
| Segment | Target Segment, Segment, Audience |

---

**Last Updated**: 2024-06-15
**Version**: 1.0
**For**: EmailPilot Calendar v1.0
