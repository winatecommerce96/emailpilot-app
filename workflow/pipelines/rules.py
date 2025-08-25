"""
LCEL Pipeline for Business Rules Validation
Exports ready-to-run Runnables
"""
from typing import Dict, Any, List
from langchain.schema.runnable import Runnable, RunnableLambda, RunnableParallel
from langchain.schema.runnable.passthrough import RunnablePassthrough
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Individual validation functions
def check_campaign_counts(state: Dict[str, Any]) -> Dict[str, Any]:
    """Check minimum campaign requirements"""
    candidates = state.get('candidates', [])
    params = state.get('_node_params', {})
    rules = params.get('rules', {})
    
    email_count = sum(1 for c in candidates if c.get('type') == 'email')
    sms_count = sum(1 for c in candidates if c.get('type') == 'sms')
    
    errors = []
    if email_count < rules.get('min_campaigns', 20):
        errors.append(f"Only {email_count} email campaigns (min: {rules.get('min_campaigns', 20)})")
    if sms_count < rules.get('min_sms', 4):
        errors.append(f"Only {sms_count} SMS campaigns (min: {rules.get('min_sms', 4)})")
    
    return {
        'email_count': email_count,
        'sms_count': sms_count,
        'count_errors': errors
    }


def check_send_caps(state: Dict[str, Any]) -> Dict[str, Any]:
    """Check weekly send cap violations"""
    candidates = state.get('candidates', [])
    params = state.get('_node_params', {})
    max_weekly = params.get('rules', {}).get('max_weekly_sends', 2)
    
    weekly_sends = defaultdict(int)
    errors = []
    
    for campaign in candidates:
        send_date = campaign.get('sendDate', '')
        if send_date:
            try:
                date = datetime.strptime(send_date, '%Y-%m-%d')
                week = date.isocalendar()[1]
                segment = campaign.get('segment', 'all')
                weekly_sends[(week, segment)] += 1
            except ValueError:
                pass
    
    for (week, segment), count in weekly_sends.items():
        if count > max_weekly:
            errors.append(f"Week {week}/{segment}: {count} sends (max: {max_weekly})")
    
    return {
        'weekly_distribution': dict(weekly_sends),
        'cap_errors': errors
    }


def check_revenue_distribution(state: Dict[str, Any]) -> Dict[str, Any]:
    """Check revenue distribution across segments"""
    candidates = state.get('candidates', [])
    inputs = state.get('inputs', {})
    params = state.get('_node_params', {})
    rules = params.get('rules', {})
    
    segment_revenue = defaultdict(float)
    total_revenue = 0
    
    for campaign in candidates:
        projected_revenue = campaign.get('projected_revenue', 0)
        segment = campaign.get('segment', 'unknown')
        segment_revenue[segment] += projected_revenue
        total_revenue += projected_revenue
    
    warnings = []
    if total_revenue > 0:
        has_three_segments = bool(inputs.get('affinity_segment_3_name'))
        expected = rules.get('revenue_distribution', {}).get(
            'three_segments' if has_three_segments else 'two_segments', {}
        )
        
        for segment, expected_pct in expected.items():
            actual_pct = (segment_revenue.get(segment, 0) / total_revenue * 100)
            if abs(actual_pct - expected_pct) > 10:
                warnings.append(
                    f"{segment}: {actual_pct:.1f}% revenue (expected: {expected_pct}%)"
                )
    
    return {
        'segment_revenue': dict(segment_revenue),
        'total_revenue': total_revenue,
        'revenue_warnings': warnings
    }


def combine_validation_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine all validation results"""
    combined = {
        'errors': [],
        'warnings': [],
        'metrics': {}
    }
    
    for result in results:
        combined['errors'].extend(result.get('count_errors', []))
        combined['errors'].extend(result.get('cap_errors', []))
        combined['warnings'].extend(result.get('revenue_warnings', []))
        
        # Collect metrics
        if 'email_count' in result:
            combined['metrics']['email_count'] = result['email_count']
            combined['metrics']['sms_count'] = result['sms_count']
        if 'weekly_distribution' in result:
            combined['metrics']['weekly_distribution'] = result['weekly_distribution']
        if 'segment_revenue' in result:
            combined['metrics']['segment_revenue'] = result['segment_revenue']
            combined['metrics']['total_revenue'] = result['total_revenue']
    
    combined['valid'] = len(combined['errors']) == 0
    return combined


def apply_validation_to_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply validation results to state"""
    # Run validation pipeline
    validation = validate_pipeline.invoke(state)
    
    # Update state
    state['valid'] = validation['valid']
    state['errors'] = validation['errors']
    state['warnings'] = validation.get('warnings', [])
    state['validation'] = {
        'timestamp': datetime.now().isoformat(),
        'valid': validation['valid'],
        'errors': validation['errors'],
        'warnings': validation.get('warnings', []),
        'metrics': validation.get('metrics', {})
    }
    
    if state['valid']:
        logger.info(f"Validation passed with {len(state.get('warnings', []))} warnings")
    else:
        logger.warning(f"Validation failed with {len(state['errors'])} errors")
    
    return state


# Build the LCEL validation pipeline
validate_pipeline: Runnable = (
    RunnableParallel(
        counts=RunnableLambda(check_campaign_counts),
        caps=RunnableLambda(check_send_caps),
        revenue=RunnableLambda(check_revenue_distribution)
    )
    | RunnableLambda(lambda x: combine_validation_results([x['counts'], x['caps'], x['revenue']]))
)

# Export the main runnable that updates state
validate_and_update: Runnable = RunnableLambda(apply_validation_to_state)


# For backward compatibility
def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy entry point"""
    return validate_and_update.invoke(state)