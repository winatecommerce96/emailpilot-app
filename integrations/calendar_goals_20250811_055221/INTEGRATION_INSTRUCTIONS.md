# Calendar Goals Integration - Backend Components

## API Routes to Add to main_firestore.py or main.py:

```python
# Add these imports at the top
from app.api import firebase_calendar_test, goals_calendar_test

# Add these router includes
app.include_router(firebase_calendar_test.router, prefix="/api/firebase-calendar-test", tags=["Firebase Calendar Test"])
app.include_router(goals_calendar_test.router, prefix="/api/goals-calendar-test", tags=["Goals Calendar Test"])
```

## Calendar Route Update:
Update the /calendar route to serve the integrated calendar:

```python
@app.get("/calendar")
async def serve_integrated_calendar():
    """Serve the integrated EmailPilot calendar with goals evaluation"""
    calendar_path = Path(__file__).parent / "calendar_integrated.html"
    if calendar_path.exists():
        return FileResponse(calendar_path)
    else:
        # Fallback to production calendar
        calendar_path = Path(__file__).parent / "calendar_production.html"
        if calendar_path.exists():
            return FileResponse(calendar_path)
        else:
            return HTMLResponse("Calendar not found", status_code=404)
```

## Features Included:
- Real-time goal evaluation as campaigns are added
- Revenue multipliers for different campaign types
- Strategic recommendations based on performance
- AI planning assistant with goal awareness
- Firebase integration for data persistence

## Testing:
1. Visit https://emailpilot.ai/calendar
2. Create/select a client
3. Add campaigns and watch goal progress update
4. Use AI assistant for strategic planning
