"""
Validate node: Checks generated calendar against business rules
"""
from typing import Dict, Any, List
import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate generated calendar against business rules
    
    Args:
        state: Current workflow state with candidates
        
    Returns:
        Updated state with validation results
    """
    try:
        candidates = state.get('candidates', [])
        params = state.get('_node_params', {})
        rules = params.get('rules', {
            'min_campaigns': 20,
            'min_sms': 4,
            'max_weekly_sends': 2,
            'revenue_distribution': {
                'two_segments': {'primary': 70, 'secondary': 30},
                'three_segments': {'primary': 70, 'secondary': 15, 'tertiary': 15}
            }
        })
        
        errors = []
        warnings = []
        
        # Check minimum campaign counts
        email_count = sum(1 for c in candidates if c.get('type') == 'email')
        sms_count = sum(1 for c in candidates if c.get('type') == 'sms')
        
        if email_count < rules['min_campaigns']:
            errors.append(f"Only {email_count} email campaigns (minimum: {rules['min_campaigns']})")
        
        if sms_count < rules['min_sms']:
            errors.append(f"Only {sms_count} SMS campaigns (minimum: {rules['min_sms']})")
        
        # Check weekly send caps
        weekly_sends = defaultdict(int)
        for campaign in candidates:
            send_date = campaign.get('sendDate', '')
            if send_date:
                try:
                    date = datetime.strptime(send_date, '%Y-%m-%d')
                    week = date.isocalendar()[1]
                    segment = campaign.get('segment', 'all')
                    weekly_sends[(week, segment)] += 1
                except ValueError:
                    warnings.append(f"Invalid date format: {send_date}")
        
        # Check for violations
        for (week, segment), count in weekly_sends.items():
            if count > rules['max_weekly_sends']:
                errors.append(f"Week {week} has {count} sends to {segment} (max: {rules['max_weekly_sends']})")
        
        # Check revenue distribution
        segment_revenue = defaultdict(float)
        total_revenue = 0
        
        for campaign in candidates:
            projected_revenue = campaign.get('projected_revenue', 0)
            segment = campaign.get('segment', 'unknown')
            segment_revenue[segment] += projected_revenue
            total_revenue += projected_revenue
        
        if total_revenue > 0:
            # Calculate percentages
            segment_percentages = {
                seg: (rev / total_revenue * 100)
                for seg, rev in segment_revenue.items()
            }
            
            # Check against rules
            inputs = state.get('inputs', {})
            has_three_segments = bool(inputs.get('affinity_segment_3_name'))
            
            if has_three_segments:
                expected = rules['revenue_distribution']['three_segments']
            else:
                expected = rules['revenue_distribution']['two_segments']
            
            # Add warnings for significant deviations
            for segment, expected_pct in expected.items():
                actual_pct = segment_percentages.get(segment, 0)
                if abs(actual_pct - expected_pct) > 10:
                    warnings.append(
                        f"{segment} segment: {actual_pct:.1f}% of revenue (expected: {expected_pct}%)"
                    )
        
        # Check for unengaged segment handling
        inputs = state.get('inputs', {})
        unengaged_size = inputs.get('unengaged_segment_size', 0)
        unengaged_percentage = unengaged_size / max(inputs.get('total_list_size', 10000), 1)
        
        if unengaged_percentage > 0.15:
            has_unengaged_campaign = any(
                'unengaged' in c.get('segment', '').lower()
                for c in candidates
            )
            if not has_unengaged_campaign:
                warnings.append(f"High unengaged percentage ({unengaged_percentage:.1%}) but no targeted campaigns")
        
        # Update state
        state['valid'] = len(errors) == 0
        state['errors'] = errors
        state['warnings'] = warnings
        
        # Add validation metadata
        state['validation'] = {
            'timestamp': datetime.now().isoformat(),
            'email_count': email_count,
            'sms_count': sms_count,
            'total_campaigns': len(candidates),
            'errors': errors,
            'warnings': warnings,
            'valid': state['valid']
        }
        
        if state['valid']:
            logger.info(f"Validation passed with {len(warnings)} warnings")
        else:
            logger.warning(f"Validation failed with {len(errors)} errors")
            logger.debug(f"Errors: {errors}")
        
        return state
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        state['errors'] = [f"Validation error: {str(e)}"]
        state['valid'] = False
        return state