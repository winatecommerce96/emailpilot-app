# Klaviyo Data Backfill System

## Overview
A comprehensive data synchronization system for backfilling historical Klaviyo data into Firestore. The system processes campaigns, flows, and granular order data day-by-day for accurate historical reporting.

## Features

### 1. **Granular Data Collection**
- **Campaigns**: Email campaign metadata, statistics, and performance metrics
- **Flows**: Automated flow data and engagement statistics  
- **Orders**: Complete order details including:
  - Order value and currency
  - Items and quantities
  - Customer information
  - UTM tracking parameters
  - Discount and shipping details
  - Categories and brands

### 2. **Progress Tracking**
- Real-time progress monitoring stored in Firestore
- Status updates: `in_progress`, `completed`, `failed`
- Detailed metrics on synced data counts
- Resume capability after failures

### 3. **Management Interface**
- Web-based dashboard at `/static/backfill_manager.html`
- Visual progress bars and status indicators
- Quick actions for test runs and bulk operations
- Detailed data viewer with revenue summaries

## API Endpoints

### Start Backfill
```bash
POST /api/backfill/start/{client_id}?years=1&include_orders=true
```

### Check Status
```bash
GET /api/backfill/status/{client_id}
GET /api/backfill/status  # All clients
```

### View Data
```bash
GET /api/backfill/data/{client_id}/summary
GET /api/backfill/data/{client_id}/orders?date=2024-12-25&limit=100
```

### Bulk Operations
```bash
POST /api/backfill/start-all
{
  "years": 1,
  "include_orders": true,
  "test_mode": false
}
```

## Data Storage Structure

```
Firestore Structure:
clients/
  {client_id}/
    klaviyo/
      data/
        campaigns/
          {campaign_id}  # Full campaign data
        flows/
          {flow_id}      # Full flow data
        orders/
          {event_id}     # Granular order details
        daily/
          campaigns/
            {date}/
              {campaign_id}  # Daily snapshot
          flows/
            {date}/
              {flow_id}      # Daily snapshot
          orders/
            {date}/
              {event_id}     # Daily orders

backfill_status/
  {client_id}  # Progress tracking
```

## Usage Examples

### Test with Single Client (Rogue Creamery)
```python
# Via API
curl -X POST "http://localhost:8000/api/backfill/start/rogue-creamery?years=1&include_orders=true"

# Via Web Interface
Navigate to: http://localhost:8000/static/backfill_manager.html
Click "Start Test" button
```

### Backfill All Clients
```python
# Via API
curl -X POST "http://localhost:8000/api/backfill/start-all" \
  -H "Content-Type: application/json" \
  -d '{"years": 1, "include_orders": true}'
```

### Monitor Progress
```python
# Check specific client
curl "http://localhost:8000/api/backfill/status/rogue-creamery"

# Check all
curl "http://localhost:8000/api/backfill/status"
```

## Implementation Details

### Key Components

1. **`app/services/klaviyo_data_service.py`**
   - Core backfill logic
   - Day-by-day processing
   - Klaviyo API integration
   - Order data extraction

2. **`app/api/backfill.py`**
   - REST API endpoints
   - Background task management
   - Status tracking

3. **`frontend/public/backfill_manager.html`**
   - Web management interface
   - Real-time progress updates
   - Data visualization

### Performance Considerations

- **Rate Limiting**: Respects Klaviyo API limits
- **Pagination**: Handles large datasets efficiently
- **Background Processing**: Non-blocking async operations
- **Error Recovery**: Automatic retry on transient failures
- **Progress Persistence**: Survives server restarts

## Security

- API keys stored in Google Secret Manager
- Client-specific key resolution
- Secure project-scoped access
- No keys in code or logs

## Monitoring

### Success Metrics
- Total orders synced
- Revenue captured
- Average order value
- Campaign/flow counts

### Error Handling
- Detailed error logging
- Failed status with error messages
- Manual retry capability
- Clear status option for reset

## Next Steps

1. **Incremental Updates**: Add support for updating only new data since last sync
2. **Scheduling**: Automated daily/weekly backfill runs
3. **Alerting**: Slack/email notifications on completion or failure
4. **Data Validation**: Verify data integrity post-backfill
5. **Export**: Generate CSV/Excel reports from backfilled data

## Testing

The system has been tested with:
- ✅ Rogue Creamery (1 year of data)
- ⏳ Ready for deployment to all clients

Access the management interface at:
**http://localhost:8000/static/backfill_manager.html**