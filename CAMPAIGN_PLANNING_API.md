# Campaign Planning API with Gemini AI Integration

## API Design Report

### Spec Files
- `/app/api/calendar.py` ➜ Campaign planning endpoint with Gemini AI integration
- `/app/schemas/calendar.py` ➜ Request/response schemas for campaign planning
- `/app/services/gemini_service.py` ➜ Enhanced with campaign planning method

### Core Decisions

1. **RESTful Endpoint**: `POST /api/calendar/plan-campaign`
2. **AI Integration**: Gemini 1.5 Pro for intelligent campaign generation
3. **Firestore Storage**: Events stored in `calendar_events` collection
4. **Fallback Strategy**: Local campaign generation when AI unavailable
5. **Multi-touchpoint Support**: Email, SMS, and Push notifications

### API Endpoint

```http
POST /api/calendar/plan-campaign
Content-Type: application/json

{
  "client_id": "string",
  "campaign_type": "New Product | Limited Time Offer | Flash Sale | Other",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD", 
  "promotion_details": "string"
}
```

### Response Format

```json
{
  "campaign_plan": "AI-generated strategic overview",
  "events_created": [
    {
      "id": "firestore-doc-id",
      "title": "Campaign Event Title",
      "date": "YYYY-MM-DD",
      "content": "Detailed event description",
      "color": "bg-color-class text-color-class",
      "event_type": "email|sms|push",
      "campaign_metadata": {
        "campaign_type": "Limited Time Offer",
        "sequence_order": 1,
        "touchpoint_type": "announcement"
      },
      "generated_by_ai": true,
      "created_at": "ISO timestamp"
    }
  ],
  "total_events": 4,
  "touchpoints": {
    "email": 2,
    "sms": 1,
    "push": 1
  }
}
```

### AI Strategy

**Gemini Prompt Engineering:**
- Strategic campaign planning with multiple touchpoints
- Intelligent event spacing throughout campaign period
- Color-coded events based on campaign type
- Email and SMS channel optimization
- Sequence ordering for maximum engagement

**Campaign Types & Colors:**
- New Product Launch: `bg-blue-200 text-blue-800`
- Limited Time Offer: `bg-red-200 text-red-800`
- Flash Sale: `bg-orange-200 text-orange-800`
- SMS Alert: `bg-orange-300 text-orange-800`
- RRB Promotion: `bg-red-300 text-red-800`
- Cheese Club: `bg-green-200 text-green-800`

### Campaign Generation Logic

1. **Announcement Phase**: Initial campaign launch (Email)
2. **Engagement Phase**: Mid-campaign reminders (Email + SMS)
3. **Urgency Phase**: Pre-deadline alerts (SMS focus)
4. **Final Push**: Last chance messaging (Email)
5. **Follow-up**: Post-campaign engagement (Optional)

### Event Metadata

Each generated event includes:
- `campaign_type`: Original campaign classification
- `sequence_order`: Event order in campaign (1, 2, 3...)
- `touchpoint_type`: Strategic purpose (announcement, reminder, urgency, last_chance)
- `generated_by_ai`: Boolean flag for AI-created events
- `promotion_details`: Original campaign context

### Error Handling

- **AI Failure**: Automatic fallback to template-based generation
- **Invalid Dates**: Date validation with helpful error messages
- **Firestore Errors**: Graceful degradation with detailed logging
- **Missing Client**: Proceeds with campaign creation (client validation optional)

### Security & Validation

- Input validation via Pydantic schemas
- Date range validation (end_date >= start_date)
- Campaign type enumeration
- SQL injection prevention through Firestore SDK
- API rate limiting (inherited from FastAPI middleware)

### Integration Points

**Existing Calendar System:**
- Events appear in standard calendar views
- Compatible with existing event CRUD operations
- Integrates with calendar dashboard and goals tracking

**Gemini AI Service:**
- Reuses existing authentication and API client
- Shared error handling and retry logic
- Consistent response formatting

### Testing

Run the test suite:
```bash
python test_campaign_planning.py
```

**Test Coverage:**
- API endpoint availability
- Campaign generation with AI
- Event creation in Firestore
- Response format validation
- Error handling scenarios

### Performance Considerations

- **AI Response Time**: 3-10 seconds typical for Gemini API
- **Fallback Speed**: <1 second for template generation
- **Firestore Writes**: Batched for multiple events
- **Memory Usage**: Minimal event data structures

### Future Enhancements

1. **Campaign Templates**: Pre-built templates for common scenarios
2. **A/B Testing**: Generate multiple campaign variations
3. **Performance Analytics**: Track campaign success metrics
4. **Integration**: Connect with Klaviyo API for actual campaign deployment
5. **Scheduling**: Automatic campaign execution at specified times

### Deployment Notes

**Required Environment Variables:**
- `GEMINI_API_KEY`: Google Gemini API authentication
- `GOOGLE_CLOUD_PROJECT`: Firestore project ID
- Firestore service account permissions

**Dependencies:**
- `google-cloud-firestore>=2.17`
- `requests>=2.31.0`
- `fastapi>=0.112`

### Example Usage

```bash
curl -X POST "http://localhost:8000/api/calendar/plan-campaign" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "acme-corp",
    "campaign_type": "Limited Time Offer",
    "start_date": "2025-01-15",
    "end_date": "2025-01-22",
    "promotion_details": "Winter Clearance Sale - 40% off winter items, free shipping over $75"
  }'
```

---

**Status**: ✅ Implemented and Ready for Testing
**Endpoint**: `POST /api/calendar/plan-campaign`
**Integration**: Gemini AI + Firestore + EmailPilot Calendar