"""
Content Optimizer Agent
Generates optimized campaign content ideas based on brand voice and goals
"""

from typing import Dict, Any, List
import random

CONTENT_OPTIMIZER_AGENT = {
    "name": "content_optimizer", 
    "description": "Creative expert specializing in email content optimization and campaign ideation",
    "version": "1.0",
    "status": "active",
    "default_task": "Generate optimized campaign ideas and content for {client_name} aligned with {optimization_goal}",
    "policy": {
        "max_tool_calls": 10,
        "timeout_seconds": 60,
        "allowed_tools": [
            "klaviyo_templates",
            "klaviyo_campaigns",
            "firestore_ro",
            "generate_copy",
            "calculate"
        ]
    },
    "variables": [
        {
            "name": "client_name",
            "type": "string",
            "required": True,
            "description": "Name of the client"
        },
        {
            "name": "brand_voice",
            "type": "string",
            "required": False,
            "default": "professional and friendly",
            "description": "Brand voice and tone guidelines"
        },
        {
            "name": "optimization_goal",
            "type": "string",
            "required": False,
            "default": "balanced",
            "description": "Primary goal: revenue, engagement, retention, or balanced"
        },
        {
            "name": "content_themes",
            "type": "array",
            "required": False,
            "default": [],
            "description": "Preferred content themes for the brand"
        },
        {
            "name": "product_focus",
            "type": "string",
            "required": False,
            "description": "Key products or categories to highlight"
        },
        {
            "name": "campaign_count",
            "type": "integer",
            "required": False,
            "default": 8,
            "description": "Number of campaign ideas to generate"
        },
        {
            "name": "selected_month",
            "type": "string",
            "required": False,
            "description": "Target month for seasonal relevance (YYYY-MM)"
        }
    ],
    "prompt_template": """You are a creative director with 20 years of experience in email marketing and content optimization.

Generate {campaign_count} optimized campaign ideas for {client_name} that align with their brand and goals.

Brand Context:
- Brand Voice: {brand_voice}
- Optimization Goal: {optimization_goal}
- Content Themes: {content_themes}
- Product Focus: {product_focus}
- Target Month: {selected_month}

For each campaign idea, provide:

1. **Campaign Concept**:
   - Theme and messaging angle
   - Target audience segment
   - Key value proposition

2. **Subject Lines** (A/B variants):
   - Primary subject line (emotional hook)
   - Alternative subject line (logical/benefit-driven)
   - Preview text

3. **Content Structure**:
   - Hero message (H1)
   - Supporting copy points
   - Call-to-action (CTA) copy
   - Recommended imagery style

4. **Optimization Elements**:
   - Personalization opportunities
   - Dynamic content blocks
   - Social proof elements
   - Urgency/scarcity tactics (if appropriate)

5. **Performance Predictions**:
   - Expected open rate range
   - Expected click rate range
   - Best send day/time

Based on the optimization goal of '{optimization_goal}':
- Revenue focus: Include offers, promotions, product highlights
- Engagement focus: Educational content, stories, community
- Retention focus: Loyalty rewards, exclusive access, appreciation
- Balanced: Mix of all elements

Ensure all content:
- Matches the brand voice
- Is seasonally relevant for {selected_month}
- Includes clear CTAs
- Follows email marketing best practices
- Is mobile-optimized

Return structured campaign ideas that can be immediately implemented."""
}

def register_content_optimizer(registry):
    """Register the Content Optimizer agent with the registry"""
    return registry.register_agent(CONTENT_OPTIMIZER_AGENT)

def generate_campaign_ideas(
    client_name: str,
    brand_voice: str,
    optimization_goal: str,
    campaign_count: int = 8
) -> List[Dict[str, Any]]:
    """
    Generate optimized campaign ideas
    
    Args:
        client_name: Client name
        brand_voice: Brand voice description
        optimization_goal: Primary optimization goal
        campaign_count: Number of ideas to generate
        
    Returns:
        List of campaign ideas with content
    """
    
    # Campaign templates based on optimization goal
    templates = {
        "revenue": [
            {"type": "promotion", "theme": "Limited Time Offer", "urgency": "high"},
            {"type": "product_launch", "theme": "New Arrival Announcement", "urgency": "medium"},
            {"type": "bundle", "theme": "Value Bundle Deal", "urgency": "medium"},
            {"type": "flash_sale", "theme": "Flash Sale Event", "urgency": "very_high"}
        ],
        "engagement": [
            {"type": "educational", "theme": "How-To Guide", "urgency": "low"},
            {"type": "story", "theme": "Behind the Scenes", "urgency": "low"},
            {"type": "community", "theme": "Customer Spotlight", "urgency": "low"},
            {"type": "survey", "theme": "We Want Your Feedback", "urgency": "medium"}
        ],
        "retention": [
            {"type": "loyalty", "theme": "VIP Exclusive Access", "urgency": "medium"},
            {"type": "appreciation", "theme": "Thank You Gift", "urgency": "low"},
            {"type": "milestone", "theme": "Anniversary Celebration", "urgency": "medium"},
            {"type": "rewards", "theme": "Points Multiplier Event", "urgency": "high"}
        ],
        "balanced": [
            {"type": "promotion", "theme": "Seasonal Sale", "urgency": "medium"},
            {"type": "educational", "theme": "Expert Tips", "urgency": "low"},
            {"type": "product_highlight", "theme": "Featured Product", "urgency": "medium"},
            {"type": "community", "theme": "Community Update", "urgency": "low"}
        ]
    }
    
    # Select templates based on goal
    selected_templates = templates.get(optimization_goal, templates["balanced"])
    
    campaign_ideas = []
    
    for i in range(min(campaign_count, len(selected_templates) * 2)):
        template = selected_templates[i % len(selected_templates)]
        
        campaign = {
            "campaign_number": i + 1,
            "concept": {
                "theme": template["theme"],
                "type": template["type"],
                "urgency": template["urgency"],
                "target_segment": "Engaged Subscribers" if i < 4 else "All Subscribers"
            },
            "subject_lines": {
                "primary": f"{template['theme']}: Special for {client_name} Customers",
                "alternative": f"Don't Miss Out - {template['theme']} Inside",
                "preview_text": f"Exclusive offer for our valued customers..."
            },
            "content": {
                "hero_h1": f"{template['theme']}",
                "subhead": f"Specially curated for you",
                "cta_primary": "Shop Now" if template["type"] in ["promotion", "product_launch"] else "Learn More",
                "cta_secondary": "View Details"
            },
            "optimization": {
                "personalization": ["First name", "Past purchase category"],
                "dynamic_content": ["Product recommendations", "Local store info"],
                "social_proof": template["urgency"] in ["high", "very_high"]
            },
            "predictions": {
                "open_rate": f"{20 + (i % 10)}%-{25 + (i % 10)}%",
                "click_rate": f"{2 + (i % 3)}%-{4 + (i % 3)}%",
                "best_send_time": "10:00 AM" if i % 2 == 0 else "2:00 PM",
                "best_send_day": ["Tuesday", "Thursday", "Friday"][i % 3]
            }
        }
        
        campaign_ideas.append(campaign)
    
    return campaign_ideas