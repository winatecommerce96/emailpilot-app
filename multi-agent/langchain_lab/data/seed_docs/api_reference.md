# EmailPilot API Reference

## Core API Endpoints

### Authentication
- `POST /api/auth/login` - User authentication
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - User logout

### Admin Management
- `GET /api/admin/clients` - List all clients
- `POST /api/admin/clients` - Create new client
- `PUT /api/admin/clients/{id}` - Update client
- `GET /api/admin/services` - Service status overview

### Calendar Operations
- `GET /api/calendar/events` - Get calendar events
- `POST /api/calendar/events` - Create calendar event
- `PUT /api/calendar/events/{id}` - Update event
- `DELETE /api/calendar/events/{id}` - Delete event
- `POST /api/calendar/planning` - AI calendar planning

### Campaign Management
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns/{id}` - Get campaign details
- `PUT /api/campaigns/{id}` - Update campaign

### Performance Metrics
- `GET /api/performance/overview` - Performance dashboard
- `GET /api/performance/metrics` - Detailed metrics
- `POST /api/performance/reports` - Generate reports

### Goals & Objectives
- `GET /api/goals` - List goals
- `POST /api/goals` - Create goal
- `PUT /api/goals/{id}` - Update goal
- `GET /api/goals/{id}/progress` - Goal progress

### Multi-Agent Orchestrator
- `POST /api/orchestrator/campaigns` - Start campaign creation
- `GET /api/orchestrator/runs/{id}` - Get run status
- `POST /api/orchestrator/approve/{id}` - Approve workflow step

## Data Models

### Client
```json
{
  "id": "string",
  "name": "string",
  "contact_email": "string",
  "klaviyo_api_key": "string (encrypted)",
  "website": "string",
  "is_active": "boolean",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Campaign Event
```json
{
  "id": "string",
  "client_id": "string",
  "name": "string",
  "type": "email|sms|push",
  "scheduled_date": "timestamp",
  "status": "draft|scheduled|sent|completed",
  "metrics": {
    "sent": "number",
    "delivered": "number",
    "opens": "number",
    "clicks": "number",
    "revenue": "number"
  }
}
```

### Goal
```json
{
  "id": "string",
  "client_id": "string",
  "name": "string",
  "description": "string",
  "metric_type": "revenue|opens|clicks|conversions",
  "target_value": "number",
  "current_value": "number",
  "deadline": "timestamp",
  "status": "active|completed|paused"
}
```

## Response Format

All API responses follow this format:
```json
{
  "success": "boolean",
  "data": "any",
  "message": "string",
  "timestamp": "timestamp"
}
```

Error responses include additional fields:
```json
{
  "success": false,
  "error": {
    "code": "string",
    "message": "string",
    "details": "object"
  }
}
```

## Rate Limiting

- Default: 120 requests per minute per IP
- Authentication endpoints: 20 requests per minute
- Bulk operations: 10 requests per minute

## Authentication

API uses JWT tokens:
1. Obtain token via `/api/auth/login`
2. Include in Authorization header: `Bearer <token>`
3. Tokens expire after 24 hours

## Error Codes

- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

## Webhooks

EmailPilot can send webhooks for:
- Campaign completion
- Goal achievement
- Performance alerts
- System notifications

Configure webhooks in admin panel.