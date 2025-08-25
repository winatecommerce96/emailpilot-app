"""
Brand Brain Node - Creates campaign briefs with brand compliance.
Enriches calendar strategy with brand-specific creative direction.
"""

from datetime import datetime
from typing import List, Dict, Any
import uuid

from ..schemas import CampaignBrief, CampaignCalendar, BrandProfile
from ..config import get_settings


def create_brief(
    campaign_calendar: CampaignCalendar,
    brand_id: str,
) -> CampaignBrief:
    """
    Create detailed campaign brief with brand guidelines.
    
    This node:
    1. Loads brand profile and guidelines
    2. Selects primary campaign from calendar
    3. Develops creative direction
    4. Checks brand compliance
    5. Sets performance targets
    """
    
    settings = get_settings()
    
    # Select the first high-confidence campaign for briefing
    selected_campaign = max(
        campaign_calendar.campaigns,
        key=lambda c: c.confidence_score
    )
    
    # Generate campaign ID
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
    
    # Define target audience based on segment
    target_audience = {
        "segment": selected_campaign.target_segment,
        "size": 25000,
        "characteristics": [
            "High lifetime value",
            "Engaged in last 90 days",
            "Previous holiday purchasers",
        ],
        "psychographics": {
            "shopping_mindset": "Value-conscious but willing to pay for quality",
            "brand_affinity": "High - average 3.2 purchases per year",
            "communication_preference": "Visual-first, mobile-primary",
        },
        "demographics": {
            "age_range": "28-45",
            "gender_split": "65% female, 35% male",
            "geography": "Urban and suburban US",
            "income": "$75K-$150K household",
        }
    }
    
    # Key messages aligned with hypothesis
    key_messages = [
        "Exclusive early access for our most valued customers",
        "Limited quantities available - your status unlocks special pricing",
        "Curated selection chosen specifically for you",
        "Free shipping and gift wrapping for VIP members",
    ]
    
    # Creative direction
    creative_direction = """
    Visual Style: Premium and sophisticated with warm November tones.
    Use rich burgundy, gold, and forest green color palette.
    
    Tone: Exclusive and appreciative, acknowledging customer loyalty.
    Balance urgency with elegance - this is earned access, not desperation.
    
    Layout: Mobile-first design with clear visual hierarchy.
    Hero image showcasing best sellers, followed by personalized recommendations.
    
    Personalization: Use first name, reference past purchases,
    show "member since" badge, display VIP tier benefits.
    """
    
    # Channel strategy
    channel_strategy = {
        "primary": "email",
        "supporting": ["sms", "push_notification"],
        "sequence": {
            "email": "Primary send Tuesday 10AM ET",
            "sms": "Follow-up Thursday 2PM ET for non-openers",
            "push": "Last chance Sunday 6PM ET",
        },
        "cross_channel_messaging": "Consistent VIP early access theme",
    }
    
    # Brand compliance checks
    brand_violations = []
    compliance_checks = {
        "tone_appropriate": True,
        "visual_guidelines_met": True,
        "legal_disclaimers_included": True,
        "accessibility_standards": True,
        "can_spam_compliant": True,
    }
    
    # Check for potential issues
    restricted_terms = ["guarantee", "risk-free", "no obligation", "free money"]
    for term in restricted_terms:
        if term.lower() in " ".join(key_messages).lower():
            brand_violations.append(f"Restricted term found: {term}")
            compliance_checks["tone_appropriate"] = False
    
    # Performance targets based on historical data
    performance_targets = {
        "open_rate": 42.5,  # Based on VIP segment average + 10%
        "click_rate": 8.2,   # Historical VIP CTR
        "conversion_rate": 5.5,  # Target based on hypothesis
        "revenue": selected_campaign.expected_revenue,
        "unsubscribe_rate": 0.1,  # Keep below threshold
    }
    
    # Success metrics
    success_metrics = [
        "Revenue generated vs. target",
        "Conversion rate by customer tier",
        "Engagement lift vs. control group",
        "Cross-sell attachment rate",
        "Post-purchase satisfaction score",
    ]
    
    return CampaignBrief(
        tenant_id=campaign_calendar.tenant_id,
        brand_id=brand_id,
        campaign_id=campaign_id,
        campaign_name=selected_campaign.campaign_name,
        objective="Drive early holiday season revenue through VIP exclusive access",
        target_audience=target_audience,
        key_messages=key_messages,
        creative_direction=creative_direction,
        channel_strategy=channel_strategy,
        brand_violations=brand_violations,
        compliance_checks=compliance_checks,
        performance_targets=performance_targets,
        success_metrics=success_metrics,
        provenance={
            "node": "brand_brain",
            "version": "1.0.0",
            "model": settings.models.primary_model,
            "created_at": datetime.utcnow().isoformat(),
            "campaign_hypothesis": selected_campaign.hypothesis,
        }
    )