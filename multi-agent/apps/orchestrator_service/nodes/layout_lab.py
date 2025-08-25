"""
Layout Lab Node - Creates design specifications.
Generates mobile-first responsive design requirements.
"""

from datetime import datetime
from typing import List, Dict, Any

from ..schemas import DesignSpec, CopyPacket, CampaignBrief
from ..config import get_settings


def create_design(
    copy_packet: CopyPacket,
    campaign_brief: CampaignBrief,
) -> DesignSpec:
    """
    Create design specifications for the campaign.
    
    This node:
    1. Defines mobile-first layout
    2. Specifies asset requirements
    3. Sets accessibility standards
    4. Provides responsive breakpoints
    """
    
    settings = get_settings()
    
    # Define layout sections
    sections = [
        {
            "type": "header",
            "height": "80px",
            "elements": ["logo", "view_in_browser_link"],
            "mobile_height": "60px",
        },
        {
            "type": "hero",
            "height": "400px",
            "elements": ["hero_image", "overlay_text", "countdown_timer"],
            "mobile_height": "300px",
            "image_requirements": {
                "dimensions": "1200x400",
                "format": "jpg",
                "max_size": "150KB",
                "alt_text_required": True,
            }
        },
        {
            "type": "content",
            "elements": ["headline", "body_copy", "bullet_points"],
            "padding": "40px",
            "mobile_padding": "20px",
        },
        {
            "type": "product_grid",
            "columns": 3,
            "mobile_columns": 1,
            "elements": ["product_cards", "quick_shop_buttons"],
            "max_products": 6,
        },
        {
            "type": "cta",
            "elements": ["primary_button", "secondary_link"],
            "button_style": {
                "min_height": "48px",
                "border_radius": "4px",
                "font_size": "16px",
            }
        },
        {
            "type": "footer",
            "elements": ["social_links", "unsubscribe", "address", "preferences"],
            "background": "#f5f5f5",
        }
    ]
    
    # Asset requirements
    asset_requirements = [
        {
            "name": "hero_image",
            "type": "image",
            "dimensions": "1200x400",
            "variants": ["desktop", "mobile"],
            "description": "November collection hero showcasing VIP products",
        },
        {
            "name": "product_images",
            "type": "image",
            "dimensions": "400x400",
            "quantity": 6,
            "description": "Square product shots on white background",
        },
        {
            "name": "logo",
            "type": "svg",
            "max_width": "200px",
            "description": "Brand logo for email header",
        },
        {
            "name": "social_icons",
            "type": "svg",
            "quantity": 4,
            "description": "Instagram, Facebook, Twitter, Pinterest icons",
        }
    ]
    
    # Color scheme from brand
    color_scheme = [
        "#2C1810",  # Primary - Rich brown
        "#D4A574",  # Secondary - Warm gold
        "#8B4513",  # Accent - Saddle brown
        "#FFFFFF",  # Background - White
        "#F5F5F5",  # Alt background - Light gray
        "#333333",  # Text - Dark gray
    ]
    
    # Typography specifications
    typography_specs = {
        "font_stack": "Georgia, 'Times New Roman', serif",
        "fallback_stack": "Arial, Helvetica, sans-serif",
        "headline": {
            "size": "32px",
            "weight": "700",
            "line_height": "1.2",
            "mobile_size": "24px",
        },
        "body": {
            "size": "16px",
            "weight": "400",
            "line_height": "1.6",
            "mobile_size": "14px",
        },
        "cta": {
            "size": "18px",
            "weight": "600",
            "text_transform": "none",
        }
    }
    
    # Responsive breakpoints
    responsive_breakpoints = {
        "mobile": 480,
        "tablet": 768,
        "desktop": 1024,
        "wide": 1440,
    }
    
    # Accessibility requirements
    accessibility_requirements = [
        "All images must have descriptive alt text",
        "Minimum contrast ratio 4.5:1 for body text",
        "Minimum contrast ratio 3:1 for large text",
        "Touch targets minimum 44x44px",
        "Logical reading order maintained",
        "Screen reader friendly table structure",
        "Semantic HTML markup",
    ]
    
    # Interactive elements
    interactive_elements = [
        {
            "type": "countdown_timer",
            "fallback": "static_text",
            "update_frequency": "1s",
            "end_behavior": "hide",
        },
        {
            "type": "product_carousel",
            "fallback": "static_grid",
            "swipe_enabled": True,
            "auto_advance": False,
        },
        {
            "type": "hover_effects",
            "elements": ["buttons", "product_cards"],
            "mobile_behavior": "tap",
        }
    ]
    
    # Fallback strategies
    fallback_strategies = {
        "images_blocked": "Styled ALT text with brand colors",
        "css_unsupported": "Inline styles on all elements",
        "javascript_disabled": "Static content only",
        "dark_mode": "Inverted color scheme with preserved contrast",
    }
    
    # Production notes
    production_notes = """
    Priority: Mobile-first design - 65% of opens expected on mobile.
    
    Critical requirements:
    - Single column layout on mobile for optimal readability
    - Finger-friendly tap targets (minimum 48px)
    - Fast load time - keep total email size under 100KB
    - Test in iOS Mail, Gmail app, and Outlook mobile
    
    VIP emphasis:
    - Gold accents to signify exclusive access
    - "VIP EXCLUSIVE" badge on hero image
    - Personalized greeting prominently displayed
    - Member benefits highlighted in dedicated section
    
    Performance optimizations:
    - Lazy load below-fold images
    - Compress all images to 72 DPI
    - Use system fonts for faster rendering
    - Preheader text optimized for mobile preview
    """
    
    return DesignSpec(
        tenant_id=campaign_brief.tenant_id,
        brand_id=campaign_brief.brand_id,
        copy_packet_id=copy_packet.campaign_brief_id,
        layout_type="single_column_responsive",
        mobile_first=True,
        sections=sections,
        asset_requirements=asset_requirements,
        color_scheme=color_scheme,
        typography_specs=typography_specs,
        responsive_breakpoints=responsive_breakpoints,
        accessibility_requirements=accessibility_requirements,
        interactive_elements=interactive_elements,
        fallback_strategies=fallback_strategies,
        production_notes=production_notes,
        provenance={
            "node": "layout_lab",
            "version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
            "design_system": "email_v2",
        }
    )