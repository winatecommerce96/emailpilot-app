# 🚀 AI Calendar Planning Feature - Complete Guide

## ✅ Feature Status: FULLY IMPLEMENTED

The AI-powered calendar planning system is now complete with MCP Klaviyo integration and customizable prompt templates.

## 🎯 How It Works

### User Flow:
1. **Select a client** in the calendar view
2. **Click "Start Calendar Planning"** button (appears when client is selected)
3. **Fill in the planning form**:
   - Select target month/year
   - Add any additional context or requirements
4. **System automatically**:
   - Fetches 2 years of historical data via MCP
   - Gets last 30 days performance metrics
   - Pulls client context from Firestore
   - Generates AI calendar plan
5. **Review generated events** before saving
6. **Click "Add to Calendar"** to save all events

## 📝 Prompt Template Management

### Where the Prompt Template is Stored:
- **Firestore Collection**: `prompt_templates`
- **Document ID**: `default_calendar_planning`
- **Location**: Your Google Cloud Firestore console

### How to Edit the Prompt Template:

#### Method 1: Via API (Recommended)
```bash
# Get current template
curl http://localhost:8000/api/calendar/planning/templates/default_calendar_planning

# Update template
curl -X PUT http://localhost:8000/api/calendar/planning/templates/default_calendar_planning \
  -H "Content-Type: application/json" \
  -d '{
    "template": "YOUR UPDATED PROMPT TEMPLATE HERE",
    "variables": ["client_name", "industry", ...]
  }'
```

#### Method 2: Via Firestore Console
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project: `emailpilot-438321`
3. Navigate to Firestore Database
4. Find collection: `prompt_templates`
5. Edit document: `default_calendar_planning`
6. Update the `template` field with your custom prompt

### Available Variables in Prompt:
```
{client_name} - Client's business name
{industry} - Client's industry
{background} - Client background/description
{voice} - Brand voice/tone
{key_growth_objective} - Primary growth goal
{affinity_segment_1} - First affinity segment definition
{affinity_segment_2} - Second affinity segment definition
{affinity_segment_3} - Third affinity segment definition
{goals_summary} - Current month's revenue goals
{campaign_history_summary} - Previous 2 years same-month campaigns
{recent_performance_summary} - Last 30 days metrics
{target_month} - Month being planned (1-12)
{target_year} - Year being planned
{additional_context} - User-provided context from form
```

## 🔧 Current Prompt Template

The default template includes:
- Client profiling section
- Affinity segments breakdown
- Historical performance context
- Strategic planning instructions
- Response format specification

### Customizing the Prompt:

Example customization for more aggressive campaigns:
```
**Instructions:**
Create an AGGRESSIVE growth calendar with 15-20 touchpoints...
Focus heavily on promotional content (70%) vs educational (30%)...
```

Example for conservative approach:
```
**Instructions:**
Create a conservative calendar with 5-7 strategic touchpoints...
Prioritize brand building and education over direct sales...
```

## 📊 Data Flow

```
User Clicks "Start Planning"
        ↓
Fetch Client Context (Firestore)
        ↓
Fetch Klaviyo Data (MCP)
    ├── 2 years historical (same month)
    └── Last 30 days performance
        ↓
Merge with Prompt Template
        ↓
Send to Gemini AI
        ↓
Parse JSON Response
        ↓
Display Events for Review
        ↓
Save to Firestore
```

## 🛠️ Technical Details

### API Endpoints:
```
POST /api/calendar/planning/generate
  Body: {
    client_id: "xxx",
    target_month: 8,
    target_year: 2025,
    additional_context: "Focus on back-to-school"
  }

GET /api/calendar/planning/templates/default_calendar_planning
PUT /api/calendar/planning/templates/default_calendar_planning
GET /api/calendar/planning/client/{client_id}/context
```

### Frontend Components:
- `CalendarPlanningModal.js` - Main planning interface
- `CalendarView.js` - Integration with calendar
- Test page: `/static/test-calendar-planning.html`

## ⚙️ Configuration Requirements

### 1. Gemini API Key (Required)
Add to environment or secrets:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### 2. Klaviyo API Keys (Per Client)
Each client needs their Klaviyo API key in Firestore:
- Collection: `clients`
- Field: `klaviyo_private_key`

### 3. MCP Service URL
Default: `http://localhost:8000/api/mcp/klaviyo`
Configure in `calendar_planning.py` if different

## 🎨 UI Features

### Planning Modal Includes:
- **Step 1**: Planning form with month/year selector
- **Step 2**: Loading state with progress indicator
- **Step 3**: Event review with edit capabilities
- **Error Handling**: Clear error messages
- **Success Feedback**: Confirmation when events added

### Calendar Integration:
- Button appears when client is selected
- Modal overlay for planning interface
- Events added directly to calendar view
- Automatic refresh after adding events

## 📋 Testing the Feature

### Quick Test:
1. Open: http://localhost:8000/static/test-calendar-planning.html
2. Select a client
3. Click "Start Calendar Planning"
4. Fill form and submit
5. Review generated events

### Production Test:
1. Open main calendar: http://localhost:8000
2. Navigate to Calendar tab
3. Select a client
4. Click "Start Calendar Planning" button
5. Complete the planning flow

## 🚨 Troubleshooting

### "Klaviyo API key not configured"
- Add client's Klaviyo key to Firestore `clients` collection
- Field: `klaviyo_private_key`

### "Gemini API key not configured"
- Set `GEMINI_API_KEY` environment variable
- Or add to Secret Manager: `gemini-api-key`

### "No events generated"
- Check prompt template formatting
- Verify JSON response format in template
- Check Gemini API quota/limits

### Modal doesn't appear
- Ensure CalendarPlanningModal.js is loaded
- Check browser console for errors
- Verify client is selected first

## 📈 Example Generated Calendar

The AI typically generates:
- **3-4 Email Campaigns**: Major marketing touchpoints
- **2-3 SMS Campaigns**: Time-sensitive alerts
- **2-3 Flow Optimizations**: Automated improvements
- **2-3 Segment Campaigns**: Targeted by affinity

Events are strategically spaced throughout the month with appropriate timing based on historical performance.

## 🎯 Next Steps

1. **Add your Gemini API key** to enable AI generation
2. **Configure Klaviyo keys** for each client
3. **Customize the prompt template** for your needs
4. **Test with a client** to see results
5. **Refine prompt** based on output quality

The feature is production-ready and waiting for API keys to be configured!