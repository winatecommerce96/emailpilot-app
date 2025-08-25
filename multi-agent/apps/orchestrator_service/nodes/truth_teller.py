"""
Truth Teller Node - Analytics and measurement setup.
Defines KPIs, instrumentation, and success criteria.
"""

from datetime import datetime
from typing import Dict, Any, List

from ..schemas import CampaignBrief, CopyPacket
from ..config import get_settings


def setup_analytics(
    campaign_brief: CampaignBrief,
    copy_packet: CopyPacket,
) -> Dict[str, Any]:
    """
    Setup analytics and monitoring plan.
    
    This node:
    1. Defines measurement framework
    2. Sets up tracking parameters
    3. Creates dashboard requirements
    4. Establishes success criteria
    """
    
    settings = get_settings()
    
    # KPI definitions
    kpis = {
        "primary": {
            "revenue": {
                "target": campaign_brief.performance_targets["revenue"],
                "measurement": "klaviyo_conversion_tracking",
                "attribution_window": "7_days",
            },
            "conversion_rate": {
                "target": campaign_brief.performance_targets["conversion_rate"],
                "measurement": "orders / delivered",
                "minimum_acceptable": 3.0,
            }
        },
        "secondary": {
            "open_rate": {
                "target": campaign_brief.performance_targets["open_rate"],
                "benchmark": 35.0,
                "segment_breakdown": True,
            },
            "click_rate": {
                "target": campaign_brief.performance_targets["click_rate"],
                "benchmark": 6.5,
                "link_level_tracking": True,
            },
            "engagement_score": {
                "formula": "(opens + clicks*2 + conversions*10) / sends",
                "target": 0.5,
            }
        },
        "health": {
            "unsubscribe_rate": {
                "threshold": campaign_brief.performance_targets["unsubscribe_rate"],
                "alert_level": 0.2,
            },
            "complaint_rate": {
                "threshold": 0.01,
                "alert_level": 0.005,
            },
            "bounce_rate": {
                "threshold": 2.0,
                "alert_level": 3.0,
            }
        }
    }
    
    # Tracking parameters
    tracking = {
        "utm_parameters": {
            "source": "email",
            "medium": "vip_campaign",
            "campaign": campaign_brief.campaign_name.replace(" ", "_").lower(),
            "content": "{{variant_id}}",
            "term": "{{segment}}",
        },
        "klaviyo_tracking": {
            "campaign_id": campaign_brief.campaign_id,
            "flow_id": None,
            "template_id": "{{template_id}}",
            "variation_id": "{{variant_id}}",
        },
        "custom_parameters": {
            "vip_tier": "{{customer.vip_tier}}",
            "member_since": "{{customer.member_since}}",
            "lifecycle_stage": "{{customer.lifecycle_stage}}",
        }
    }
    
    # A/B test measurement
    ab_test_plan = {
        "test_type": "subject_line_and_copy",
        "variants": len(copy_packet.variants),
        "sample_size": copy_packet.a_b_test_plan["sample_size_per_variant"],
        "success_metric": "conversion_rate",
        "statistical_confidence": 0.95,
        "minimum_detectable_effect": 0.10,
        "test_duration": "24_hours",
        "winner_criteria": "highest_revenue_per_recipient",
    }
    
    # Dashboard requirements
    dashboard = {
        "real_time_metrics": [
            "sends", "opens", "clicks", "conversions", "revenue"
        ],
        "visualizations": [
            {
                "type": "time_series",
                "metric": "cumulative_revenue",
                "interval": "hourly",
            },
            {
                "type": "funnel",
                "stages": ["sent", "opened", "clicked", "converted"],
            },
            {
                "type": "heatmap",
                "data": "link_clicks",
            },
            {
                "type": "comparison",
                "metrics": ["variant_performance"],
            }
        ],
        "alerts": [
            {
                "condition": "unsubscribe_rate > 0.2",
                "action": "pause_campaign",
                "notify": ["campaign_manager", "deliverability_team"],
            },
            {
                "condition": "conversion_rate < 2.0 after 6 hours",
                "action": "review_required",
                "notify": ["campaign_manager"],
            }
        ]
    }
    
    # Post-send analysis plan
    post_send_analysis = {
        "immediate": {
            "timing": "2_hours",
            "metrics": ["open_rate", "click_rate", "early_conversions"],
            "actions": ["variant_performance_check", "deliverability_monitoring"],
        },
        "day_one": {
            "timing": "24_hours",
            "metrics": ["conversion_rate", "revenue", "variant_winner"],
            "actions": ["winner_rollout", "segment_analysis"],
        },
        "week_one": {
            "timing": "7_days",
            "metrics": ["total_revenue", "customer_lifetime_value_impact", "cross_sell"],
            "actions": ["performance_report", "learnings_documentation"],
        },
        "month_end": {
            "timing": "30_days",
            "metrics": ["long_tail_conversions", "retention_impact", "brand_health"],
            "actions": ["executive_summary", "strategy_recommendations"],
        }
    }
    
    # Success criteria
    success_criteria = {
        "minimum": {
            "revenue": campaign_brief.performance_targets["revenue"] * 0.8,
            "conversion_rate": 3.0,
            "no_deliverability_issues": True,
        },
        "target": {
            "revenue": campaign_brief.performance_targets["revenue"],
            "conversion_rate": campaign_brief.performance_targets["conversion_rate"],
            "positive_engagement_lift": True,
        },
        "exceptional": {
            "revenue": campaign_brief.performance_targets["revenue"] * 1.2,
            "conversion_rate": campaign_brief.performance_targets["conversion_rate"] * 1.2,
            "viral_sharing": True,
        }
    }
    
    return {
        "kpis": kpis,
        "tracking": tracking,
        "ab_test_plan": ab_test_plan,
        "dashboard": dashboard,
        "post_send_analysis": post_send_analysis,
        "success_criteria": success_criteria,
        "instrumentation_complete": True,
        "estimated_reporting_lag": "15_minutes",
        "data_retention_days": 90,
        "provenance": {
            "node": "truth_teller",
            "version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
        }
    }