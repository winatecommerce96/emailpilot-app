# Calendar Integration for EmailPilot

This document outlines the successful integration of the Interactive Campaign Calendar into the EmailPilot.ai platform.

## 🎯 Integration Overview

The original standalone HTML calendar has been fully converted and integrated into EmailPilot as a React-based component with FastAPI backend support.

### Key Features Preserved
- ✅ **Drag-and-Drop Calendar** - Full calendar functionality with event management
- ✅ **Client Management Integration** - Seamlessly works with EmailPilot's client system
- ✅ **AI Chat Assistant** - Gemini-powered calendar AI for event management
- ✅ **Google Doc Import** - Import campaign plans from Google Documents
- ✅ **Campaign Classification** - Color-coded campaign types (RRB, Cheese Club, etc.)
- ✅ **Event CRUD Operations** - Create, read, update, delete calendar events
- ✅ **Export Functionality** - Export calendar data in JSON format
- ✅ **Authentication** - Integrated with EmailPilot's auth system

## 🏗️ Architecture

### Backend (FastAPI)
- **Calendar API Router** (`/api/calendar/*`) - RESTful endpoints for calendar operations
- **SQLAlchemy Models** - `CalendarEvent`, `CalendarImportLog`, `CalendarChatHistory`
- **Services Layer** - `CalendarService`, `GoogleService`, `GeminiService`
- **Authentication** - JWT-based auth integration with existing EmailPilot auth

### Frontend (React Components)
- **CalendarView** - Main calendar container with client selection
- **Calendar** - Core calendar component with drag-drop functionality
- **EventModal** - Event creation/editing modal with full form fields
- **CalendarChat** - AI chat interface for calendar interactions
- **CalendarStats** - Statistics and analytics for calendar events

### Database Schema
```sql
-- Calendar Events
calendar_events (
    id, title, content, event_date, color, event_type,
    client_id (FK), segment, send_time, subject_a, subject_b,
    preview_text, main_cta, offer, ab_test,
    imported_from_doc, import_doc_id, original_event_id,
    created_at, updated_at
)

-- Import Logs
calendar_import_logs (
    id, client_id (FK), import_type, source_id, status,
    events_imported, events_updated, events_failed,
    error_message, raw_data, processed_data,
    started_at, completed_at
)

-- Chat History
calendar_chat_history (
    id, client_id (FK), user_message, ai_response,
    is_action, action_type, action_result, session_id,
    created_at
)
```

## 🚀 Setup Instructions

### 1. Database Setup
```bash
# Create calendar tables
cd emailpilot-app
python create_calendar_tables.py
```

### 2. Environment Variables
Add to your `.env` file:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 5. Access the Calendar
- Open http://localhost:8080
- Login with demo credentials
- Navigate to "Calendar" in the top navigation
- Select a client to start managing campaigns

## 📊 API Endpoints

### Calendar Events
- `GET /api/calendar/events` - Get calendar events
- `POST /api/calendar/events` - Create new event
- `PUT /api/calendar/events/{id}` - Update event
- `DELETE /api/calendar/events/{id}` - Delete event
- `POST /api/calendar/events/{id}/duplicate` - Duplicate event

### Google Integration
- `POST /api/calendar/import/google-doc` - Import from Google Doc

### AI Chat
- `POST /api/calendar/chat` - Chat with calendar AI

### Analytics & Export
- `GET /api/calendar/client/{id}/stats` - Get calendar statistics
- `GET /api/calendar/export/{id}` - Export calendar data

## 🤖 AI Chat Capabilities

The calendar AI can handle:
- **Questions**: "How many campaigns this month?", "What's scheduled for next week?"
- **Actions**: "Delete the cheese club campaign", "Create SMS for Friday"
- **Analysis**: Campaign type breakdowns, upcoming events, scheduling conflicts

### Example Chat Commands
```
User: "How many nurturing campaigns do we have in October?"
AI: "You have 3 Nurturing/Education campaigns scheduled for October..."

User: "Delete the promotion campaign on October 15th"
AI: "Okay, I've deleted the event." (Performs the action)

User: "Create a new SMS campaign for next Friday"
AI: "Okay, I've created the new event: 'New SMS Campaign'." (Creates event)
```

## 🎨 Campaign Types & Colors

- **RRB Promotion**: Red (`bg-red-300 text-red-800`)
- **Cheese Club**: Green (`bg-green-200 text-green-800`)
- **Nurturing/Education**: Blue (`bg-blue-200 text-blue-800`)
- **Community/Lifestyle**: Purple (`bg-purple-200 text-purple-800`)
- **Re-engagement**: Yellow (`bg-yellow-200 text-yellow-800`)
- **SMS Alert**: Orange (`bg-orange-300 text-orange-800`)

## 🔧 Development Notes

### Client Integration
The calendar is fully integrated with EmailPilot's client management system:
- Calendar events are tied to specific clients
- Client selection updates calendar view
- All calendar operations respect client boundaries

### Authentication
All calendar endpoints require authentication:
- JWT tokens from EmailPilot auth system
- Session-based authentication for frontend
- Automatic token validation on all requests

### Google APIs
Google Doc import functionality:
- Server-side Google API integration
- Document content extraction
- AI-powered campaign parsing
- Background processing with status tracking

### Error Handling
Comprehensive error handling:
- API-level error responses
- Frontend error states and messages
- Background task failure recovery
- Database transaction rollbacks

## 🐛 Troubleshooting

### Common Issues

1. **Calendar not loading**
   - Check if client is selected
   - Verify authentication token
   - Check browser console for API errors

2. **Google Doc import failing**
   - Verify access token validity
   - Check document permissions
   - Ensure Gemini API key is set

3. **AI chat not responding**
   - Check Gemini API key configuration
   - Verify client selection
   - Check network connectivity

4. **Drag-drop not working**
   - Ensure JavaScript is enabled
   - Check for console errors
   - Verify event handlers are attached

## 📈 Future Enhancements

Potential improvements for the calendar integration:

1. **Enhanced Google Integration**
   - Full OAuth 2.0 flow
   - Google Calendar sync
   - Real-time collaboration

2. **Advanced AI Features**
   - Campaign optimization suggestions
   - Automated scheduling
   - Performance predictions

3. **Analytics Dashboard**
   - Campaign performance metrics
   - Send time optimization
   - A/B testing results integration

4. **Mobile Optimization**
   - Responsive design improvements
   - Touch-friendly interactions
   - Mobile app integration

## ✅ Integration Complete!

The Interactive Campaign Calendar has been successfully integrated into EmailPilot.ai with all original functionality preserved and enhanced through integration with the existing client management and authentication systems.