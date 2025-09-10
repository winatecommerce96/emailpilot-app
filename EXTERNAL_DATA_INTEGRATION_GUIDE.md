# EmailPilot External Data Integration Guide

## Overview

This technical guide documents the data structures, formats, and requirements for integrating external data sources with EmailPilot's locally staged calendar functions. This guide is designed for developers who need to understand how to format and send data from external systems to EmailPilot's calendar and campaign management system.

## Core Data Structures

### 1. Calendar Events (`calendar_events` collection)

#### Primary Event Schema
```json
{
  "id": "string (auto-generated Firestore doc ID)",
  "title": "string (required, 1-255 chars)",
  "content": "string (optional, campaign description/notes)",
  "date": "string (required, YYYY-MM-DD format)",
  "event_date": "date (alternative field name)",
  "client_id": "string (required, client identifier)",
  "color": "string (optional, default: 'bg-gray-200 text-gray-800')",
  "event_type": "string (optional, default: 'email')",
  
  // Campaign-specific fields
  "segment": "string (optional, target audience segment)",
  "send_time": "string (optional, preferred send time)",
  "subject_a": "string (optional, A/B test subject line A)",
  "subject_b": "string (optional, A/B test subject line B)", 
  "preview_text": "string (optional, email preview text)",
  "main_cta": "string (optional, primary call-to-action)",
  "offer": "string (optional, promotional offer details)",
  "ab_test": "string (optional, A/B test configuration)",
  
  // Metadata fields
  "imported_from_doc": "boolean (optional, default: false)",
  "import_doc_id": "string (optional, source document reference)",
  "original_event_id": "string (optional, external system event ID)",
  "generated_by_ai": "boolean (optional, default: false)",
  "campaign_type": "string (optional, campaign category)",
  "promotion_details": "string (optional, promotion description)",
  "campaign_metadata": "object (optional, additional campaign data)",
  
  // Orchestrator-specific fields (for LangGraph workflows)
  "client_firestore_id": "string (alternative client identifier)",
  "planned_send_datetime": "datetime (alternative to date field)",
  "campaign_name": "string (alternative to title field)",
  "channel": "string (email, sms, push)",
  "latest": "boolean (for version control, default: true)",
  
  // System timestamps
  "created_at": "datetime (auto-generated)",
  "updated_at": "datetime (auto-updated)"
}
```

#### Event Type Values
- `"email"` - Email campaign
- `"sms"` - SMS campaign  
- `"push"` - Push notification
- `"general"` - General event
- `"cheese club"` - Specific campaign type (high-value)
- `"rrb"` - Red Ribbon Box promotion
- `"flash sale"` - Time-limited promotion
- `"nurturing"` - Nurture sequence
- `"re-engagement"` - Win-back campaign

#### Color Coding Standards
- `"bg-blue-200 text-blue-800"` - Email campaigns
- `"bg-orange-200 text-orange-800"` - SMS campaigns  
- `"bg-green-200 text-green-800"` - High-value campaigns (Cheese Club)
- `"bg-red-300 text-red-800"` - Promotions (RRB)
- `"bg-purple-200 text-purple-800"` - Push notifications
- `"bg-gray-200 text-gray-800"` - General events

### 2. Client Data (`clients` collection)

#### Client Schema
```json
{
  "id": "string (client slug: 'rogue-creamery', 'consumer-law-attorneys')",
  "name": "string (required, human-readable client name)",
  "client_name": "string (alternative field name)",
  "client_slug": "string (URL-safe identifier)",
  
  // Contact information
  "primary_contact_name": "string (optional)",
  "primary_contact_email": "string (optional)",
  "contact_email": "string (alternative field name)",
  "account_manager": "string (optional)",
  
  // Business details
  "industry": "string (optional)",
  "company_size": "string (optional: small, medium, large, enterprise)",
  "timezone": "string (optional, e.g. 'America/Los_Angeles')",
  "currency": "string (optional, default: 'USD')",
  
  // Klaviyo integration
  "klaviyo_account_id": "string (optional)",
  "klaviyo_company_id": "string (optional)", 
  "klaviyo_api_key_secret": "string (Secret Manager reference)",
  "klaviyo_secret_name": "string (legacy field)",
  
  // Metric configurations
  "placed_order_metric_id": "string (primary metric ID)",
  "metrics": {
    "placed_order_metric_id": "string (alternative location)"
  },
  "klaviyo_placed_order_metric_id": "string (alternative field)",
  
  // Campaign settings
  "segment_configurations": "object (optional)",
  "default_send_times": "array (optional)",
  "brand_guidelines": "object (optional)",
  
  // Goals and targets
  "monthly_revenue_goal": "number (optional)",
  "quarterly_goals": "object (optional)",
  "kpi_targets": "object (optional)",
  
  // System fields
  "is_active": "boolean (default: true)",
  "created_at": "datetime (auto-generated)",
  "updated_at": "datetime (auto-updated)"
}
```

### 3. Campaign Planning Requests

#### AI Campaign Planning Request
```json
{
  "client_id": "string (required)",
  "campaign_type": "string (required: 'New Product', 'Limited Time Offer', 'Flash Sale', 'Other')",
  "start_date": "string (required, YYYY-MM-DD)",
  "end_date": "string (required, YYYY-MM-DD)", 
  "promotion_details": "string (required, campaign description)"
}
```

#### Bulk Event Creation Request
```json
{
  "client_id": "string (required)",
  "events": [
    {
      "title": "string (required)",
      "date": "string (required, YYYY-MM-DD)", 
      "event_date": "string (alternative field)",
      "content": "string (optional)",
      "color": "string (optional)",
      "event_type": "string (optional)",
      "segment": "string (optional)",
      "send_time": "string (optional)",
      "subject_a": "string (optional)",
      "subject_b": "string (optional)",
      "preview_text": "string (optional)",
      "main_cta": "string (optional)",
      "offer": "string (optional)",
      "ab_test": "string (optional)"
    }
  ]
}
```

### 4. LangGraph Workflow State

#### Calendar Workflow State
```json
{
  // Input parameters
  "client_id": "string (required)",
  "client_name": "string (required)",  
  "selected_month": "string (YYYY-MM)",
  "campaign_count": "number (target number of campaigns)",
  "client_sales_goal": "number (revenue target)",
  "optimization_goal": "string (optimization objective)",
  "llm_type": "string (gemini, gpt-4, claude)",
  "additional_context": "string (user-provided context)",
  "use_real_data": "boolean (whether to use live Klaviyo data)",
  "mcp_queries": "array (custom MCP queries)",
  
  // External data integration
  "mcp_tools": "array (LangChain tool instances)",
  "klaviyo_segments": "object (cached segment data)",
  "klaviyo_campaigns": "object (cached campaign data)",
  "klaviyo_metrics": "object (cached metrics data)",
  "klaviyo_flows": "object (cached flow data)",
  "klaviyo_lists": "object (cached list data)",
  "klaviyo_profiles": "object (cached profile data)",
  
  // Processing outputs
  "brand_data": "object (brand analysis results)",
  "historical_insights": "object (performance analysis)",
  "segment_analysis": "object (audience insights)",
  "content_recommendations": "array (content suggestions)",
  "final_calendar": "object (generated calendar)",
  "validation_results": "object (quality checks)",
  
  // Workflow metadata  
  "status": "string (workflow status)",
  "errors": "array (error messages)",
  "execution_time": "number (processing time)",
  "mcp_status": "object (data connection status)"
}
```

## API Endpoints for External Integration

### Calendar Management

#### Create Single Event
```http
POST /api/calendar/events
Content-Type: application/json

{
  "title": "Flash Sale - 50% Off Winter Collection",
  "date": "2024-02-15",
  "client_id": "fashion-retailer",
  "content": "24-hour flash sale targeting winter inventory clearance",
  "color": "bg-red-300 text-red-800",
  "event_type": "flash sale",
  "segment": "engaged_shoppers",
  "send_time": "10:00 AM EST",
  "subject_a": "⏰ 24 Hours Only: 50% Off Winter Styles",
  "subject_b": "🔥 Flash Sale Alert: Winter Collection 50% Off",
  "main_cta": "Shop Now",
  "offer": "50% off all winter styles with code WINTER50"
}
```

#### Create Multiple Events (Bulk)
```http
POST /api/calendar/create-bulk-events
Content-Type: application/json

{
  "client_id": "subscription-service",
  "events": [
    {
      "title": "Welcome Series - Day 1",
      "date": "2024-02-10",
      "event_type": "nurturing",
      "segment": "new_subscribers",
      "subject_a": "Welcome to [Brand]! Here's what to expect",
      "send_time": "2:00 PM"
    },
    {
      "title": "Welcome Series - Day 3", 
      "date": "2024-02-12",
      "event_type": "nurturing",
      "segment": "new_subscribers", 
      "subject_a": "Getting the most out of your subscription",
      "send_time": "2:00 PM"
    },
    {
      "title": "Welcome Series - Day 7",
      "date": "2024-02-16", 
      "event_type": "nurturing",
      "segment": "new_subscribers",
      "subject_a": "Still have questions? We're here to help!",
      "send_time": "2:00 PM"
    }
  ]
}
```

#### AI-Powered Campaign Planning
```http
POST /api/calendar/plan-campaign
Content-Type: application/json

{
  "client_id": "health-supplements",
  "campaign_type": "New Product",
  "start_date": "2024-03-01",
  "end_date": "2024-03-31", 
  "promotion_details": "Launching new collagen supplement line targeting women 25-45. Premium product positioning with clinical research backing. Key selling points: anti-aging benefits, third-party tested, subscription available."
}
```

### Client Management

#### Create/Update Client
```http
POST /api/admin/clients
Content-Type: application/json

{
  "name": "Organic Skincare Co",
  "industry": "Beauty & Personal Care",
  "company_size": "medium",
  "primary_contact_name": "Sarah Johnson", 
  "primary_contact_email": "sarah@organicskincare.com",
  "account_manager": "Jennifer Martinez",
  "timezone": "America/Los_Angeles",
  "currency": "USD",
  "klaviyo_account_id": "XXXXXX",
  "klaviyo_api_key_secret": "klaviyo-api-organic-skincare-co",
  "monthly_revenue_goal": 75000,
  "brand_guidelines": {
    "voice": "friendly, educational, trustworthy",
    "colors": ["#8FBC8F", "#F5F5DC", "#DEB887"],
    "key_messaging": "Clean beauty, sustainable ingredients, cruelty-free"
  }
}
```

## External Data Source Integration Patterns

### 1. Direct API Integration

For external systems that can make HTTP requests directly to EmailPilot:

```python
import requests
import json
from datetime import datetime, timedelta

class EmailPilotIntegration:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def create_campaign_series(self, client_id, series_data):
        """Create a series of related campaigns"""
        events = []
        start_date = datetime.strptime(series_data["start_date"], "%Y-%m-%d")
        
        for i, campaign in enumerate(series_data["campaigns"]):
            event_date = start_date + timedelta(days=campaign.get("day_offset", i * 3))
            
            event = {
                "title": campaign["title"],
                "date": event_date.strftime("%Y-%m-%d"),
                "client_id": client_id,
                "content": campaign.get("description", ""),
                "event_type": campaign.get("type", "email"),
                "segment": campaign.get("target_segment"),
                "subject_a": campaign.get("subject_line"),
                "send_time": campaign.get("send_time", "10:00 AM"),
                "color": self._get_color_for_type(campaign.get("type", "email"))
            }
            events.append(event)
        
        # Send bulk creation request
        response = requests.post(
            f"{self.base_url}/api/calendar/create-bulk-events",
            headers=self.headers,
            json={"client_id": client_id, "events": events}
        )
        
        return response.json()
    
    def _get_color_for_type(self, event_type):
        color_map = {
            "email": "bg-blue-200 text-blue-800",
            "sms": "bg-orange-200 text-orange-800", 
            "flash sale": "bg-red-300 text-red-800",
            "nurturing": "bg-green-100 text-green-800"
        }
        return color_map.get(event_type, "bg-gray-200 text-gray-800")

# Usage example
integration = EmailPilotIntegration()

campaign_series = {
    "start_date": "2024-03-01",
    "campaigns": [
        {
            "title": "New Collection Teaser",
            "type": "email",
            "target_segment": "vip_customers", 
            "subject_line": "Something special is coming...",
            "day_offset": 0
        },
        {
            "title": "New Collection Launch",
            "type": "email",
            "target_segment": "all_subscribers",
            "subject_line": "Introducing Our Spring Collection",
            "day_offset": 3
        },
        {
            "title": "Launch Reminder SMS", 
            "type": "sms",
            "target_segment": "sms_subscribers",
            "subject_line": "New spring styles just dropped!",
            "day_offset": 4
        }
    ]
}

result = integration.create_campaign_series("fashion-brand", campaign_series)
```

### 2. File-Based Data Import

For systems that export data to files:

```python
import csv
import json
from datetime import datetime

class FileImporter:
    def __init__(self, emailpilot_api):
        self.api = emailpilot_api
    
    def import_from_csv(self, file_path, client_id):
        """Import calendar events from CSV file"""
        events = []
        
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Map CSV columns to EmailPilot format
                event = {
                    "title": row.get("Campaign Name", "").strip(),
                    "date": self._parse_date(row.get("Launch Date", "")),
                    "client_id": client_id,
                    "content": row.get("Description", "").strip(),
                    "event_type": self._map_campaign_type(row.get("Type", "")),
                    "segment": row.get("Target Audience", "").strip(),
                    "subject_a": row.get("Subject Line A", "").strip(),
                    "subject_b": row.get("Subject Line B", "").strip(),
                    "send_time": row.get("Send Time", "10:00 AM").strip(),
                    "offer": row.get("Promotion Details", "").strip()
                }
                
                # Only add valid events
                if event["title"] and event["date"]:
                    events.append(event)
        
        if events:
            return self.api.create_bulk_events(client_id, events)
        else:
            return {"error": "No valid events found in CSV"}
    
    def _parse_date(self, date_str):
        """Parse various date formats to YYYY-MM-DD"""
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
    
    def _map_campaign_type(self, campaign_type):
        """Map external campaign types to EmailPilot types"""
        type_map = {
            "Newsletter": "email",
            "Promotion": "email", 
            "Text Message": "sms",
            "Flash Sale": "flash sale",
            "Product Launch": "email",
            "Welcome Series": "nurturing",
            "Winback": "re-engagement"
        }
        return type_map.get(campaign_type.strip(), "email")

# Usage
api = EmailPilotIntegration()
importer = FileImporter(api)

result = importer.import_from_csv("campaign_export.csv", "beauty-brand")
print(f"Import result: {result}")
```

### 3. CRM Integration Example

For CRM systems with webhook capabilities:

```python
from fastapi import FastAPI, Request
import json

class CRMWebhookHandler:
    def __init__(self, emailpilot_api):
        self.api = emailpilot_api
        self.app = FastAPI()
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.post("/webhook/campaign-scheduled")
        async def handle_campaign_scheduled(request: Request):
            data = await request.json()
            
            # Extract campaign data from CRM webhook
            campaign_data = {
                "title": data.get("campaign_name"),
                "date": data.get("scheduled_date"),
                "client_id": self._get_client_id(data.get("account_id")),
                "content": data.get("campaign_description"),
                "event_type": self._map_crm_type(data.get("campaign_type")),
                "segment": data.get("target_list_name"),
                "subject_a": data.get("email_subject"),
                "send_time": data.get("send_time", "10:00 AM")
            }
            
            # Create event in EmailPilot
            result = self.api.create_event(campaign_data)
            
            return {"status": "success", "event_id": result.get("id")}
        
        @self.app.post("/webhook/campaign-updated") 
        async def handle_campaign_updated(request: Request):
            data = await request.json()
            
            # Update existing event
            event_id = self._find_event_by_external_id(data.get("campaign_id"))
            if event_id:
                updates = {
                    "title": data.get("campaign_name"),
                    "date": data.get("scheduled_date"),
                    "content": data.get("campaign_description")
                }
                result = self.api.update_event(event_id, updates)
                return {"status": "updated", "event_id": event_id}
            else:
                return {"status": "event_not_found"}
    
    def _get_client_id(self, account_id):
        """Map CRM account ID to EmailPilot client ID"""
        # Implement mapping logic based on your CRM
        mapping = {
            "crm_123": "fashion-retailer",
            "crm_456": "tech-startup", 
            "crm_789": "restaurant-chain"
        }
        return mapping.get(account_id, "default-client")
    
    def _map_crm_type(self, crm_type):
        """Map CRM campaign types to EmailPilot types"""
        type_map = {
            "email_blast": "email",
            "sms_campaign": "sms", 
            "promotional": "flash sale",
            "nurture": "nurturing",
            "reactivation": "re-engagement"
        }
        return type_map.get(crm_type, "email")

# Usage
api = EmailPilotIntegration()
webhook_handler = CRMWebhookHandler(api)

# Run with: uvicorn webhook_handler:app --host 0.0.0.0 --port 8001
```

## Data Validation Requirements

### Required Fields
- `title`: Must be 1-255 characters
- `date`: Must be valid YYYY-MM-DD format  
- `client_id`: Must match existing client document ID

### Optional but Recommended Fields
- `event_type`: Helps with filtering and reporting
- `color`: Improves visual organization
- `segment`: Critical for campaign targeting
- `content`: Provides context for campaign planning

### Field Constraints
- Dates must not be in the past (for new events)
- Client ID must exist in clients collection
- Color values should follow TailwindCSS format
- Send times should include timezone information

## Error Handling

### Common Error Responses
```json
{
  "detail": "Client not found",
  "status_code": 404
}

{
  "detail": "Invalid date format. Use YYYY-MM-DD",
  "status_code": 400
}

{
  "detail": "Title is required and must be 1-255 characters",
  "status_code": 422
}
```

### Integration Best Practices
1. **Validate data before sending** - Check required fields and formats locally
2. **Handle rate limits** - Implement backoff for bulk operations
3. **Use idempotency keys** - Prevent duplicate event creation
4. **Store external IDs** - Use `original_event_id` field for mapping
5. **Implement error retry logic** - Handle temporary failures gracefully
6. **Batch operations when possible** - Use bulk endpoints for efficiency

## Testing Integration

### Local Testing Setup
```bash
# Start EmailPilot locally
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Test basic connectivity
curl http://localhost:8000/api/calendar/health

# Test event creation
curl -X POST http://localhost:8000/api/calendar/events \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Event","date":"2024-02-15","client_id":"test-client"}'
```

### Integration Testing Checklist
- [ ] Event creation with minimal fields
- [ ] Event creation with all optional fields
- [ ] Bulk event creation (multiple events)
- [ ] Event updates and modifications
- [ ] Client creation and management
- [ ] Error handling for invalid data
- [ ] Authentication (if implemented)
- [ ] Rate limiting behavior
- [ ] Webhook endpoint reliability

This guide provides the foundational knowledge needed to integrate external systems with EmailPilot's calendar and campaign management functions. The flexible schema design allows for various integration patterns while maintaining data consistency and system reliability.