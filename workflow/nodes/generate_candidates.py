"""
Generate candidates node: Creates campaign candidates using agent
This node is referenced by generate node in workflow but provides direct implementation
"""
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate campaign candidates using Calendar Planner agent
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with campaign candidates
    """
    try:
        # This is a fallback implementation when agent is not available
        # In production, this would be replaced by the agent execution
        
        brand = state.get('brand', 'Unknown')
        month = state.get('month', datetime.now().strftime('%Y-%m'))
        inputs = state.get('inputs', {})
        
        # Parse month
        year, month_num = map(int, month.split('-'))
        start_date = datetime(year, month_num, 1)
        
        # Calculate days in month
        if month_num == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month_num + 1, 1)
        days_in_month = (next_month - start_date).days
        
        # Generate campaigns
        candidates = []
        
        # Email campaigns (20 minimum)
        for i in range(20):
            day = (i % days_in_month) + 1
            send_date = start_date.replace(day=day)
            
            # Determine segment
            if i % 3 == 0:
                segment = inputs.get('affinity_segment_1_name', 'VIP Customers')
            elif i % 3 == 1:
                segment = inputs.get('affinity_segment_2_name', 'Regular Customers')
            else:
                segment = 'All Subscribers'
            
            campaign = {
                'type': 'email',
                'week': f"Week {(day - 1) // 7 + 1}",
                'sendDate': send_date.strftime('%Y-%m-%d'),
                'sendTime': f"{9 + (i % 3)}:00 AM",
                'segment': segment,
                'subjectLineAB': f"{brand} Special Offer #{i+1} | Limited Time",
                'previewText': f"Don't miss out on this exclusive deal for {segment}",
                'heroH1': f"Special Offer for {segment}",
                'subhead': "Limited time offer just for you",
                'heroImage': f"hero_{i+1}.jpg",
                'ctaCopy': "Shop Now",
                'offer': f"{10 + (i % 3) * 5}% off",
                'abTestIdea': "Test subject line emoji vs no emoji",
                'projected_revenue': random.uniform(1000, 5000)
            }
            candidates.append(campaign)
        
        # SMS campaigns (4 minimum)
        for i in range(4):
            day = (i * 7) + 3  # Spread throughout month
            if day > days_in_month:
                day = days_in_month
            send_date = start_date.replace(day=day)
            
            campaign = {
                'type': 'sms',
                'week': f"Week {(day - 1) // 7 + 1}",
                'sendDate': send_date.strftime('%Y-%m-%d'),
                'sendTime': "2:00 PM",
                'segment': 'SMS Subscribers',
                'message': f"{brand}: Flash sale today only! {15 + i*5}% off. Reply STOP to opt out.",
                'projected_revenue': random.uniform(500, 2000)
            }
            candidates.append(campaign)
        
        # Sort by date
        candidates.sort(key=lambda x: x['sendDate'])
        
        # Update state
        state['candidates'] = candidates
        
        logger.info(f"Generated {len(candidates)} campaign candidates for {brand} - {month}")
        
        return state
        
    except Exception as e:
        logger.error(f"Generate candidates failed: {e}")
        state['errors'] = state.get('errors', []) + [f"Generation error: {str(e)}"]
        state['candidates'] = []
        return state