"""
Human review gate: Pauses workflow for human approval
"""
from typing import Dict, Any
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Store for pending reviews (in production, use Redis or database)
PENDING_REVIEWS = {}


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Human review gate - pauses execution for approval
    
    Args:
        state: Current workflow state
        
    Returns:
        State with approval status (blocks until approved)
    """
    try:
        run_id = state.get('run_id', 'unknown')
        brand = state.get('brand', 'unknown')
        month = state.get('month', 'unknown')
        
        # Prepare review data
        review_data = {
            'run_id': run_id,
            'brand': brand,
            'month': month,
            'candidates': state.get('candidates', []),
            'validation': state.get('validation', {}),
            'warnings': state.get('warnings', []),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store for retrieval by approve API
        PENDING_REVIEWS[run_id] = review_data
        
        # Write to file for CLI review (optional)
        review_file = Path(f"/tmp/review_{run_id}.json")
        with open(review_file, 'w') as f:
            json.dump(review_data, f, indent=2, default=str)
        
        # Log and display review request
        print("\n" + "="*60)
        print("🛑 HUMAN REVIEW REQUIRED")
        print("="*60)
        print(f"Brand: {brand}")
        print(f"Month: {month}")
        print(f"Run ID: {run_id}")
        print(f"Total Campaigns: {len(state.get('candidates', []))}")
        
        if state.get('warnings'):
            print(f"\n⚠️  Warnings ({len(state['warnings'])}):")
            for warning in state['warnings'][:5]:
                print(f"  - {warning}")
        
        print(f"\nReview file: {review_file}")
        print("\nTo approve via CLI:")
        print(f"  curl -X POST http://localhost:8000/api/workflow/approve/{run_id} \\")
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"approved": true, "notes": "Looks good"}\'')
        
        print("\nTo approve interactively:")
        response = input("\nApprove? (yes/no/file.json): ").strip().lower()
        
        if response.endswith('.json'):
            # Load approval from file
            with open(response) as f:
                approval = json.load(f)
        elif response == 'yes':
            approval = {
                'approved': True,
                'timestamp': datetime.now().isoformat(),
                'notes': 'Approved via CLI'
            }
        else:
            approval = {
                'approved': False,
                'timestamp': datetime.now().isoformat(),
                'notes': response if response != 'no' else 'Rejected via CLI'
            }
        
        # Update state with approval
        state['approvals'] = approval
        
        # Clean up
        if run_id in PENDING_REVIEWS:
            del PENDING_REVIEWS[run_id]
        
        if approval['approved']:
            logger.info(f"Review approved for {brand} - {month}")
        else:
            logger.warning(f"Review rejected for {brand} - {month}: {approval.get('notes')}")
            state['errors'] = state.get('errors', []) + [f"Rejected: {approval.get('notes')}"]
        
        return state
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Review interrupted by user")
        state['approvals'] = {
            'approved': False,
            'timestamp': datetime.now().isoformat(),
            'notes': 'Interrupted by user'
        }
        return state
        
    except Exception as e:
        logger.error(f"Review failed: {e}")
        state['errors'] = state.get('errors', []) + [f"Review error: {str(e)}"]
        state['approvals'] = {
            'approved': False,
            'timestamp': datetime.now().isoformat(),
            'notes': f'Error: {str(e)}'
        }
        return state


def get_pending_review(run_id: str) -> Dict[str, Any]:
    """Get pending review data by run_id"""
    return PENDING_REVIEWS.get(run_id)


def approve_review(run_id: str, approved: bool, notes: str = "") -> Dict[str, Any]:
    """Approve or reject a pending review"""
    if run_id not in PENDING_REVIEWS:
        raise ValueError(f"No pending review for run_id: {run_id}")
    
    approval = {
        'approved': approved,
        'timestamp': datetime.now().isoformat(),
        'notes': notes,
        'run_id': run_id
    }
    
    # Remove from pending
    del PENDING_REVIEWS[run_id]
    
    return approval