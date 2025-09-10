# Calendar JSON Upload Format Specification

## Overview
This document provides instructions for creating a properly formatted JSON file that can be uploaded to the EmailPilot Calendar system for bulk campaign import.

## JSON Structure

### Basic Format
```json
{
  "events": [
    {
      "date": "YYYY-MM-DD",
      "title": "Campaign Name",
      "type": "campaign_type",
      "description": "Optional description",
      "segment": "target_segment"
    }
  ]
}
```

### Complete Example - Basic Format
```json
{
  "events": [
    {
      "date": "2025-09-01",
      "title": "Labor Day Sale",
      "type": "promotional",
      "description": "20% off sitewide for Labor Day weekend",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-09-05",
      "title": "Fall Collection Launch",
      "type": "content",
      "description": "Introducing our new fall product line",
      "segment": "engaged_subscribers"
    },
    {
      "date": "2025-09-10",
      "title": "Customer Survey",
      "type": "engagement",
      "description": "Quarterly customer satisfaction survey",
      "segment": "vip_customers"
    },
    {
      "date": "2025-09-15",
      "title": "Harvest Festival",
      "type": "seasonal",
      "description": "Celebrate the harvest season with special offers",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-09-20",
      "title": "Flash Friday Sale",
      "type": "sms",
      "description": "SMS exclusive 4-hour flash sale",
      "segment": "sms_subscribers"
    }
  ]
}
```

### Complete Example - Advanced Format with All Fields
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
      "hero_image": "labor-day-hero.jpg - Patriotic theme with fireworks and products",
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
    },
    {
      "week_number": 38,
      "date": "2025-09-15",
      "send_time": "09:00",
      "type": "push",
      "segments": "app_users",
      "title": "New Collection Alert",
      "description": "Push notification for fall collection launch",
      "cta_copy": "View Collection",
      "hero_image": "fall-collection-thumb.jpg - Autumn colors, cozy theme"
    }
  ]
}
```

## Field Specifications

### Required Fields

#### `date` (string, required)
- **Format**: `YYYY-MM-DD`
- **Example**: `"2025-09-15"`
- **Description**: The date when the campaign should be scheduled
- **Validation**: Must be a valid date in ISO 8601 format
- **Alternative Names**: `send_date`

#### `title` (string, required)
- **Maximum Length**: 100 characters
- **Example**: `"Back to School Sale"`
- **Description**: The name/title of the campaign
- **Best Practice**: Keep it concise and descriptive
- **Alternative Names**: `name`, `subject_line_a`
- **Note**: Emojis are automatically added based on type (✉️ Email, 💬 SMS, 📱 Push)

#### `type` (string, required)
- **Allowed Values**:
  - **Email Campaign Types**:
    - `"email"` - Standard email campaign (default)
    - `"promotional"` - Sales, discounts, special offers
    - `"content"` - Educational, blog posts, guides
    - `"engagement"` - Surveys, feedback, community
    - `"seasonal"` - Holiday or season-specific campaigns
    - `"special"` - VIP, exclusive, or unique campaigns
  - **SMS Campaign Types**:
    - `"sms"` - Standard SMS message
    - `"sms-promotional"` - SMS sales and offers
    - `"sms-content"` - SMS content updates
    - `"sms-engagement"` - SMS surveys and engagement
    - `"sms-seasonal"` - SMS seasonal campaigns
    - `"sms-special"` - SMS exclusive offers
  - **Push Notification Types**:
    - `"push"` - Mobile push notification
    - `"push-promotional"` - Push notification for sales
    - `"push-reminder"` - Push notification reminders

### Optional Fields - Basic

#### `description` (string, optional)
- **Maximum Length**: 2000 characters
- **Example**: `"Exclusive 30% discount for VIP members only"`
- **Description**: Additional details about the campaign
- **Default**: Empty string if not provided

#### `segment` (string, optional)
- **Example**: `"vip_customers"`, `"new_subscribers"`, `"engaged_30_days"`
- **Description**: Target audience segment for the campaign
- **Alternative Names**: `segments`
- **Default**: `"all_subscribers"` if not provided
- **Common Segments**:
  - `"all_subscribers"` - Entire email list
  - `"engaged_subscribers"` - Recently active subscribers
  - `"vip_customers"` - High-value customers
  - `"new_subscribers"` - Recent sign-ups
  - `"sms_subscribers"` - SMS opt-in list
  - `"inactive_subscribers"` - Re-engagement targets

### Optional Fields - Advanced Campaign Details

#### `week_number` (integer, optional)
- **Example**: `35`
- **Description**: Week number in the year for campaign tracking

#### `send_time` (string, optional)
- **Format**: `HH:MM` (24-hour format)
- **Example**: `"14:30"`
- **Description**: Scheduled send time in local timezone

#### `subject_line_a` (string, optional)
- **Example**: `"Don't Miss Out: 50% Off Everything!"`
- **Description**: Primary subject line for A/B testing

#### `subject_line_b` (string, optional)
- **Example**: `"Flash Sale: Half Price on All Items"`
- **Description**: Alternative subject line for A/B testing

#### `preview_text` (string, optional)
- **Example**: `"Shop now and save big - sale ends midnight!"`
- **Description**: Email preview text shown in inbox

#### `hero_h1` (string, optional)
- **Example**: `"BIGGEST SALE OF THE YEAR"`
- **Description**: Main headline in email content

#### `sub_head` (string, optional)
- **Example**: `"Save up to 50% on selected items"`
- **Description**: Sub-headline or secondary heading

#### `hero_image` (string, optional)
- **Example**: `"summer-sale-hero.jpg - Bright, vibrant beach scene with products"`
- **Description**: Hero image filename and tone/shot notes

#### `cta_copy` (string, optional)
- **Example**: `"Shop Now & Save"`
- **Description**: Call-to-action button text

#### `offer` (string, optional)
- **Example**: `"50% off sitewide + free shipping over $50"`
- **Description**: Special offer details

#### `ab_test_idea` (string, optional)
- **Example**: `"Test emoji in subject line vs. no emoji"`
- **Description**: A/B testing strategy for copy, creative, or timing

#### `secondary_message` (string, optional)
- **Example**: `"Text SAVE to 12345 for exclusive SMS deals"`
- **Description**: Secondary message suggestion or SMS variant
- **Alternative Names**: `sms_variant`

## Multiple Months Format

For importing campaigns across multiple months:

```json
{
  "events": [
    {
      "date": "2025-08-28",
      "title": "August End Sale",
      "type": "promotional",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-09-01",
      "title": "September Welcome",
      "type": "content",
      "segment": "all_subscribers"
    },
    {
      "date": "2025-10-01",
      "title": "October Fest",
      "type": "seasonal",
      "segment": "all_subscribers"
    }
  ]
}
```

## Alternative Array Format

The system also accepts a simple array format:

```json
[
  {
    "date": "2025-09-01",
    "title": "Labor Day Sale",
    "type": "promotional"
  },
  {
    "date": "2025-09-15",
    "title": "Mid-Month Check-in",
    "type": "engagement"
  }
]
```

## Validation Rules

1. **Date Validation**:
   - Must be in `YYYY-MM-DD` format
   - Year must be between 2020-2030
   - Month must be 01-12
   - Day must be valid for the given month

2. **Type Validation**:
   - Must be one of the allowed campaign types
   - Case-sensitive (use lowercase)

3. **Title/Name Validation**:
   - Cannot be empty
   - Maximum 100 characters
   - Special characters are allowed
   - Field must be named `title` (or `name` as alternative)

4. **File Size**:
   - Maximum file size: 5MB
   - Maximum campaigns per file: 1000

## Common Errors and Solutions

### Error: "Invalid date format"
**Solution**: Ensure dates use `YYYY-MM-DD` format with leading zeros (e.g., `2025-09-05` not `2025-9-5`)

### Error: "Unknown campaign type"
**Solution**: Check that the type exactly matches one of the allowed values (case-sensitive, lowercase)

### Error: "Missing required field"
**Solution**: Ensure each campaign has at minimum: `date`, `title` (or `name`), and `type` fields

### Error: "Invalid JSON format"
**Solution**: Validate your JSON using a JSON validator. Common issues:
- Missing commas between objects
- Trailing commas after last item
- Unescaped quotes in strings
- Missing closing brackets

### Error: "Unrecognized JSON format"
**Solution**: The JSON must either be:
- An array of event objects directly: `[{...}, {...}]`
- An object with an `events` property: `{"events": [{...}, {...}]}`
- An object with a `calendar` property: `{"calendar": [{...}, {...}]}`

## Tips for Third-Party Tools

### Excel/Google Sheets Export
1. Create columns: `date`, `title`, `type`, `description`, `segment`
2. Format date column as `YYYY-MM-DD`
3. Export as CSV
4. Convert CSV to JSON using an online converter or script
5. Wrap the array in an object with `events` property: `{"events": [...]}`

### Using a JSON Generator
1. Use a tool like [json-generator.com](https://json-generator.com)
2. Copy the template structure
3. Fill in your campaign data
4. Validate before downloading

### Programmatic Generation (Python Example)
```python
import json
from datetime import datetime, timedelta

events = []
start_date = datetime(2025, 9, 1)

for i in range(10):
    campaign_date = start_date + timedelta(days=i*3)
    events.append({
        "date": campaign_date.strftime("%Y-%m-%d"),
        "title": f"Campaign {i+1}",
        "type": "promotional" if i % 2 == 0 else "content",
        "description": f"Description for campaign {i+1}",
        "segment": "all_subscribers"
    })

output = {"events": events}

with open('campaigns.json', 'w') as f:
    json.dump(output, f, indent=2)
```

## Testing Your JSON

Before uploading to production:

1. **Validate JSON Syntax**: Use [jsonlint.com](https://jsonlint.com) to check for syntax errors

2. **Check Required Fields**: Ensure every campaign has `date`, `title` (or `name`), and `type`

3. **Verify Date Format**: All dates should be `YYYY-MM-DD`

4. **Test with Sample**: Start with 2-3 campaigns to test the upload process

5. **Review in Calendar**: After upload, verify campaigns appear on correct dates

## Upload Process

1. Click the **"Import"** button in the calendar interface
2. Select your `.json` file
3. Review the preview of campaigns to be imported
4. Confirm the import
5. Campaigns will be added to the calendar immediately

## Support

For issues or questions about the JSON format:
- Check that your JSON validates at [jsonlint.com](https://jsonlint.com)
- Ensure all required fields are present
- Verify campaign types match the allowed values exactly
- Test with a small sample first

## Version History
- v2.0 (2025-09-10): Added comprehensive campaign fields and automatic emoji indicators
  - Support for 13 advanced campaign fields (week number, send time, A/B testing, etc.)
  - Automatic emoji indicators for Email (✉️), SMS (💬), and Push (📱) notifications
  - Enhanced description field to include all campaign metadata
- v1.1 (2025-09-10): Fixed JSON structure to use `events` property and `title` field
- v1.0 (2025-09-10): Initial format specification
- Supports both object (`{"events": [...]}` or `{"calendar": [...]}`) and array formats
- Compatible with EmailPilot Calendar v2.0+