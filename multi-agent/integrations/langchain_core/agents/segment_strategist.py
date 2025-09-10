"""
Segment Strategist Agent
Analyzes customer segments and recommends targeting strategies
"""

from typing import Dict, Any, List
from datetime import datetime

SEGMENT_STRATEGIST_AGENT = {
    "name": "segment_strategist",
    "description": "Expert in customer segmentation analysis and targeting strategy for email campaigns",
    "version": "1.0",
    "status": "active",
    "default_task": "Analyze customer segments for {client_name} and recommend targeting strategies for {selected_month}",
    "policy": {
        "max_tool_calls": 12,
        "timeout_seconds": 60,
        "allowed_tools": [
            "klaviyo_segments",
            "klaviyo_segment_members",
            "klaviyo_profiles",
            "klaviyo_metrics_aggregate",
            "firestore_ro",
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
            "name": "selected_month",
            "type": "string",
            "required": True,
            "pattern": "^\\d{4}-\\d{2}$",
            "description": "Target month for segmentation strategy (YYYY-MM)"
        },
        {
            "name": "segment_criteria",
            "type": "object",
            "required": False,
            "default": {
                "min_segment_size": 100,
                "engagement_threshold": "medium",
                "value_segments": ["high", "medium"]
            },
            "description": "Criteria for segment selection and prioritization"
        },
        {
            "name": "affinity_segments",
            "type": "array",
            "required": False,
            "default": [],
            "description": "Pre-defined affinity segments for the client"
        },
        {
            "name": "revenue_target",
            "type": "number",
            "required": False,
            "description": "Monthly revenue target to inform segment prioritization"
        }
    ],
    "prompt_template": """You are a customer segmentation expert with deep expertise in email marketing strategy.

Analyze the customer segments for {client_name} and develop a targeting strategy for {selected_month}.

Your analysis should include:

1. **Segment Overview**:
   - List all available segments with sizes
   - Identify high-value segments (by revenue potential)
   - Flag underutilized segments

2. **Engagement Analysis**:
   - Segments with highest engagement rates
   - Segments showing declining engagement
   - Re-engagement opportunities

3. **Value Segmentation**:
   - High-value customer segments
   - Growth potential segments
   - At-risk segments needing attention

4. **Affinity Segments** (if provided: {affinity_segments}):
   - Performance of each affinity segment
   - Cross-selling opportunities
   - Segment-specific messaging recommendations

5. **Monthly Strategy for {selected_month}**:
   - Priority segments to target
   - Recommended campaign frequency per segment
   - Personalization strategies
   - Expected revenue contribution per segment

Segment criteria: {segment_criteria}
Revenue target (if set): {revenue_target}

Provide specific recommendations for:
- Which segments to prioritize
- Optimal send frequency for each segment
- Content themes that resonate with each segment
- Cross-segment campaign opportunities

Return structured recommendations that can be directly implemented in campaign planning."""
}

def register_segment_strategist(registry):
    """Register the Segment Strategist agent with the registry"""
    return registry.register_agent(SEGMENT_STRATEGIST_AGENT)

def analyze_segments(segments: List[Dict[str, Any]], criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze customer segments and generate targeting recommendations
    
    Args:
        segments: List of segment data
        criteria: Segmentation criteria
        
    Returns:
        Dictionary with segment analysis and recommendations
    """
    if not segments:
        return {"error": "No segments to analyze"}
    
    min_size = criteria.get("min_segment_size", 100)
    value_segments = criteria.get("value_segments", ["high", "medium"])
    
    # Categorize segments
    viable_segments = [s for s in segments if s.get("member_count", 0) >= min_size]
    
    # Sort by value/engagement potential
    priority_segments = sorted(
        viable_segments,
        key=lambda x: x.get("avg_order_value", 0) * x.get("engagement_rate", 0.2),
        reverse=True
    )
    
    # Calculate segment distribution
    total_audience = sum(s.get("member_count", 0) for s in segments)
    
    # Generate recommendations
    recommendations = []
    targeting_strategy = {}
    
    for i, segment in enumerate(priority_segments[:5], 1):
        segment_name = segment.get("name", f"Segment {i}")
        segment_size = segment.get("member_count", 0)
        coverage = (segment_size / total_audience * 100) if total_audience > 0 else 0
        
        # Determine send frequency based on value and engagement
        if segment.get("value_tier") == "high" or i == 1:
            frequency = "2x per week"
            campaigns = 8
        elif i <= 3:
            frequency = "Weekly"
            campaigns = 4
        else:
            frequency = "Bi-weekly"
            campaigns = 2
            
        targeting_strategy[segment_name] = {
            "priority": i,
            "size": segment_size,
            "coverage": f"{coverage:.1f}%",
            "recommended_frequency": frequency,
            "campaigns_per_month": campaigns,
            "focus": "Personalized offers" if i <= 2 else "Engagement content"
        }
        
        recommendations.append(
            f"Target '{segment_name}' ({segment_size} members) with {frequency} campaigns"
        )
    
    return {
        "summary": {
            "total_segments": len(segments),
            "viable_segments": len(viable_segments),
            "total_audience": total_audience,
            "coverage": f"{sum(s['size'] for s in targeting_strategy.values()) / total_audience * 100:.1f}%"
        },
        "targeting_strategy": targeting_strategy,
        "recommendations": recommendations,
        "segment_themes": {
            "high_value": "Exclusive offers, early access, VIP benefits",
            "engaged": "New products, educational content, community",
            "at_risk": "Win-back offers, surveys, re-engagement",
            "new": "Welcome series, brand story, first-purchase incentives"
        }
    }