"""
Publish node: Saves approved calendar to Firestore or other targets
"""
from typing import Dict, Any
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish approved calendar to storage
    
    Args:
        state: Current workflow state with approved calendar
        
    Returns:
        Updated state with publish confirmation
    """
    try:
        # Check if approved
        approvals = state.get('approvals', {})
        if not approvals.get('approved'):
            logger.warning("Cannot publish: Calendar not approved")
            state['errors'] = state.get('errors', []) + ["Calendar not approved for publishing"]
            return state
        
        # Get publish params
        params = state.get('_node_params', {})
        target = params.get('target', 'firestore')
        collection = params.get('collection', 'calendars')
        
        # Prepare calendar document
        calendar_doc = {
            'run_id': state.get('run_id'),
            'brand': state.get('brand'),
            'month': state.get('month'),
            'campaigns': state.get('candidates', []),
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'approved_at': approvals.get('timestamp'),
                'approved_by': state.get('user_id', 'system'),
                'approval_notes': approvals.get('notes', ''),
                'validation': state.get('validation', {}),
                'inputs': state.get('inputs', {})
            }
        }
        
        # Publish based on target
        if target == 'firestore':
            try:
                from google.cloud import firestore
                db = firestore.Client()
                
                # Create document ID
                doc_id = f"{state['brand']}_{state['month']}_{state['run_id'][:8]}"
                
                # Save to Firestore
                doc_ref = db.collection(collection).document(doc_id)
                doc_ref.set(calendar_doc)
                
                logger.info(f"Published calendar to Firestore: {collection}/{doc_id}")
                state['published'] = {
                    'success': True,
                    'target': 'firestore',
                    'path': f"{collection}/{doc_id}",
                    'timestamp': datetime.now().isoformat()
                }
                
            except ImportError:
                logger.warning("Firestore not available, saving to file")
                target = 'file'
            except Exception as e:
                logger.error(f"Firestore publish failed: {e}")
                target = 'file'
        
        if target == 'file':
            # Fallback to file storage
            filename = f"/tmp/calendar_{state['brand']}_{state['month']}.json"
            with open(filename, 'w') as f:
                json.dump(calendar_doc, f, indent=2, default=str)
            
            logger.info(f"Published calendar to file: {filename}")
            state['published'] = {
                'success': True,
                'target': 'file',
                'path': filename,
                'timestamp': datetime.now().isoformat()
            }
        
        # Update calendar state
        state['calendar'] = {
            'brand': state['brand'],
            'month': state['month'],
            'campaign_count': len(state.get('candidates', [])),
            'published_at': datetime.now().isoformat(),
            'status': 'published'
        }
        
        # Log success metrics
        logger.info(f"Successfully published calendar for {state['brand']} - {state['month']}")
        logger.info(f"Total campaigns: {len(state.get('candidates', []))}")
        
        return state
        
    except Exception as e:
        logger.error(f"Publish failed: {e}")
        state['errors'] = state.get('errors', []) + [f"Publish error: {str(e)}"]
        state['published'] = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        return state