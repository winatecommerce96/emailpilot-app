# Workflow Additional Fields Request

**From:** EmailPilot Calendar App
**To:** EmailPilot Simple Workflow
**Date:** 2025-11-20
**Purpose:** Request for additional fields in calendar import payload

---

## Overview

The Calendar App import endpoint (`POST /api/calendar/import`) is ready to receive additional fields that will make imported campaigns immediately actionable for brief generation without manual entry.

Please add the following fields to the `events[]` array in the import payload.

---

## Required Additional Fields

### 1. Email Creative Fields

Add these fields at the event level (same level as `title`, `date`, etc.):

```json
{
  "date": "2026-01-02",
  "title": "...",
  "type": "...",
  "description": "...",
  "send_time": "...",
  "segment": "...",

  // NEW FIELDS - Add these:
  "subject_a": "Primary subject line for the email",
  "subject_b": "A/B test variant subject line (optional)",
  "preview_text": "Email preview text shown in inbox",
  "main_cta": "Call-to-action button text",
  "offer": "Top-level offer summary",

  "strategy": { ... }
}
```

#### Field Specifications

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `subject_a` | string | Yes | Primary subject line | "New Year, New Brew - Fresh Start Collection" |
| `subject_b` | string | No | A/B test variant subject (if ab_test planned) | "Fresh Start with Fresh Roasts - New Collection" |
| `preview_text` | string | Yes | Preview text for inbox display | "Exclusive new collection inside. Limited time only." |
| `main_cta` | string | Yes | Primary call-to-action button text | "Shop New Collection" |
| `offer` | string | No | Offer summary (for promotional campaigns) | "15% off + Free Shipping" |

---

### 2. Content Planning Fields

Add these fields at the event level for content guidance:

```json
{
  // ... existing fields ...

  // CONTENT PLANNING FIELDS - Add these:
  "content_brief": "Brief description of email content and layout",
  "template_type": "Template/layout type identifier"
}
```

#### Field Specifications

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `content_brief` | string | Yes | Content description for brief generation | "Hero image of new collection, 3 product feature cards, customer testimonial, CTA button" |
| `template_type` | string | No | Email template/layout type | "product-launch", "newsletter", "promotional", "educational" |

---

## Complete Event Example

Here's a complete event object with all fields:

```json
{
  "date": "2026-01-02",
  "title": "New Year, New Brew - Fresh Start Collection",
  "type": "promotional",
  "description": "product_launch",
  "send_time": "10:17",
  "segment": "Engaged Subscribers",

  "subject_a": "New Year, New Brew - Fresh Start Collection",
  "subject_b": "Fresh Start with Fresh Roasts - New Collection",
  "preview_text": "Three exclusive new roasts. Available through January only.",
  "main_cta": "Shop New Collection",
  "offer": "Free shipping on orders $50+",
  "content_brief": "Hero: New Year collection lifestyle image. Body: 3 product cards for each new roast with tasting notes. Social proof: customer quote. Footer CTA: Shop now with free shipping.",
  "template_type": "product-launch",

  "strategy": {
    "send_time_rationale": "Tuesday at 10:17 AM - top performing time...",
    "targeting_rationale": "Engaged Subscribers (8,500 contacts)...",
    "performance_forecast": { ... },
    "ab_test": {
      "element": "subject_line",
      "hypothesis": "Benefit-driven will outperform seasonal by 8-12%",
      "expected_impact": "+8-12% open rate"
    },
    "offer_strategy": { ... },
    "mcp_evidence": { ... }
  }
}
```

---

## Notes on Existing Fields

### Consistency Requirements

1. **offer vs offer_strategy.details**: Both can exist. `offer` is the short summary shown in UI; `offer_strategy.details` is the detailed explanation in strategy.

2. **subject_a/subject_b vs ab_test**:
   - `subject_a` and `subject_b` are the actual subject lines
   - `ab_test` in strategy explains the hypothesis and expected impact
   - Both should be provided when an A/B test is planned

3. **description vs content_brief**:
   - `description` = campaign type classification (e.g., "product_launch", "educational")
   - `content_brief` = actual content guidance for brief generation

---

## Response Format

The import endpoint will return:

```json
{
  "success": true,
  "message": "Calendar imported successfully with strategy",
  "events_imported": 13,
  "client_id": "chris-bean",
  "has_send_strategy": true,
  "event_ids": ["abc123", "def456", ...]
}
```

---

## Questions

If you need clarification on any field or have suggestions for additional data that would be valuable, please let me know.

**Calendar App Import Endpoint:** `POST /api/calendar/import`
**Endpoint Status:** Ready to receive these additional fields
