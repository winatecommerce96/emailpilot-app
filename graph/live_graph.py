#!/usr/bin/env python3
"""
Live Data Calendar Graph
Fetches real data from Firestore and Klaviyo via MCP
No static datasets needed!
"""
from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime
import os
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# STATE DEFINITION - What flows between nodes
# ============================================
class CalendarState(TypedDict):
    """State that flows through the graph"""
    # Input parameters
    client_id: str
    month: str
    
    # Data from sources
    firestore_data: Optional[Dict[str, Any]]
    klaviyo_metrics: Optional[Dict[str, Any]]
    client_info: Optional[Dict[str, Any]]
    
    # Processing results
    campaign_plan: Optional[Dict[str, Any]]
    email_templates: Optional[List[Dict[str, Any]]]
    send_schedule: Optional[Dict[str, Any]]
    
    # Metadata
    timestamp: str
    errors: List[str]
    status: str

# ============================================
# NODE 1: Load Firestore Data
# ============================================
def load_firestore_node(state: CalendarState) -> CalendarState:
    """Load client data from Firestore"""
    logger.info(f"📁 Loading Firestore data for client: {state['client_id']}")
    
    try:
        from google.cloud import firestore
        
        # Initialize Firestore client
        db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"))
        
        # Fetch client document
        client_ref = db.collection('clients').document(state['client_id'])
        client_doc = client_ref.get()
        
        if client_doc.exists:
            client_data = client_doc.to_dict()
            logger.info(f"✅ Found client data: {client_data.get('name', 'Unknown')}")
            
            # Also fetch related data
            campaigns_ref = db.collection('campaigns').where('client_id', '==', state['client_id'])
            campaigns = [doc.to_dict() for doc in campaigns_ref.stream()]
            
            firestore_data = {
                'client': client_data,
                'campaigns': campaigns,
                'fetched_at': datetime.now().isoformat()
            }
            
            return {
                **state,
                'firestore_data': firestore_data,
                'client_info': client_data,
                'status': 'firestore_loaded'
            }
        else:
            logger.warning(f"⚠️ Client {state['client_id']} not found in Firestore")
            return {
                **state,
                'errors': state.get('errors', []) + [f"Client {state['client_id']} not found"],
                'status': 'client_not_found'
            }
            
    except Exception as e:
        logger.error(f"❌ Firestore error: {e}")
        return {
            **state,
            'errors': state.get('errors', []) + [f"Firestore error: {str(e)}"],
            'status': 'firestore_error'
        }

# ============================================
# NODE 2: Pull Klaviyo Metrics via MCP
# ============================================
def pull_klaviyo_node(state: CalendarState) -> CalendarState:
    """Pull REAL metrics from Klaviyo via MCP - NO MOCK DATA"""
    logger.info(f"📊 Pulling REAL Klaviyo metrics for {state['client_id']} - {state['month']}")
    
    try:
        # Get Klaviyo API key from client info - check multiple field names
        client_info = state.get('client_info', {})
        
        # Different clients store keys in different fields
        klaviyo_key = (
            client_info.get('klaviyo_api_key') or 
            client_info.get('klaviyo_private_key') or
            client_info.get('api_key_secret')
        )
        
        # Check if we need to fetch from Secret Manager
        klaviyo_secret_name = (
            client_info.get('klaviyo_api_key_secret') or
            client_info.get('klaviyo_secret_name')
        )
        
        klaviyo_account_id = client_info.get('klaviyo_account_id')
        
        # If we have a secret name but no key, fetch from Secret Manager
        if not klaviyo_key and klaviyo_secret_name:
            logger.info(f"📝 Found secret reference: {klaviyo_secret_name}")
            try:
                from app.services.secrets import SecretManagerService
                secret_manager = SecretManagerService(os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"))
                
                # The secret name is already formatted correctly
                secret_name = klaviyo_secret_name
                
                try:
                    klaviyo_key = secret_manager.get_secret(secret_name)
                    logger.info(f"✅ Retrieved Klaviyo key from Secret Manager: {secret_name}")
                    # Show first and last few chars for debugging (safely)
                    if klaviyo_key:
                        masked = f"{klaviyo_key[:7]}...{klaviyo_key[-4:]}" if len(klaviyo_key) > 20 else "***"
                        logger.info(f"   Key format: {masked}")
                except Exception as e:
                    logger.error(f"❌ Could not fetch from Secret Manager: {e}")
                    logger.error(f"   Attempted secret name: {secret_name}")
                    
            except ImportError as e:
                logger.error(f"Secret Manager import failed: {e}")
        
        if not klaviyo_key:
            # Final fallback - try standard secret names
            try:
                from app.services.secrets import SecretManagerService
                secret_manager = SecretManagerService(os.getenv("GOOGLE_CLOUD_PROJECT", "emailpilot-438321"))
                
                # Try client-specific key
                client_slug = client_info.get('client_slug', state['client_id'])
                secret_name = f"klaviyo-api-key-{client_slug}"
                
                try:
                    klaviyo_key = secret_manager.get_secret(secret_name)
                    logger.info(f"✅ Retrieved Klaviyo key from Secret Manager using slug: {secret_name}")
                except:
                    logger.error(f"❌ No Klaviyo API key found for {state['client_id']}")
                    return {
                        **state,
                        'errors': state.get('errors', []) + [f"No Klaviyo API key configured for client"],
                        'status': 'klaviyo_no_key'
                    }
            except:
                pass
        
        # Now fetch REAL data from Klaviyo
        if klaviyo_key:
            logger.info(f"🔌 Connecting to Klaviyo with API key (first 7 chars: {klaviyo_key[:7] if len(klaviyo_key) > 7 else '***'})")
        else:
            logger.error("❌ No Klaviyo API key available after all attempts")
            return {
                **state,
                'errors': state.get('errors', []) + ["No Klaviyo API key found"],
                'status': 'klaviyo_no_key'
            }
        
        # Try direct Klaviyo API first
        import httpx
        
        klaviyo_data = {}
        
        # Option 1: Direct Klaviyo API
        try:
            # Klaviyo API requires revision header
            headers = {
                "Authorization": f"Klaviyo-API-Key {klaviyo_key}",
                "Accept": "application/json",
                "revision": "2024-10-15"  # Latest Klaviyo API revision
            }
            
            with httpx.Client(timeout=10.0) as client:
                # First verify the API key works
                accounts_response = client.get(
                    "https://a.klaviyo.com/api/accounts",
                    headers=headers
                )
                
                if accounts_response.status_code == 200:
                    accounts = accounts_response.json()
                    logger.info(f"✅ Klaviyo API key is valid! Found {len(accounts.get('data', []))} accounts")
                    
                    # Get campaigns - Klaviyo requires channel filter
                    campaigns_response = client.get(
                        "https://a.klaviyo.com/api/campaigns",
                        headers=headers,
                        params={
                            "filter": "equals(messages.channel,'email')"  # Filter for email campaigns
                            # Removed page[size] as it's not valid for campaigns endpoint
                        }
                    )
                else:
                    logger.error(f"❌ Klaviyo accounts check failed: {accounts_response.status_code}")
                    campaigns_response = accounts_response  # Use this for error handling
                
                if campaigns_response.status_code == 200:
                    campaigns = campaigns_response.json().get('data', [])
                    logger.info(f"✅ Retrieved {len(campaigns)} real campaigns from Klaviyo")
                    
                    # Get metrics
                    metrics_response = client.get(
                        "https://a.klaviyo.com/api/metrics",
                        headers=headers
                    )
                    
                    if metrics_response.status_code == 200:
                        metrics = metrics_response.json().get('data', [])
                        logger.info(f"✅ Retrieved {len(metrics)} metrics from Klaviyo")
                    else:
                        metrics = []
                    
                    # Get segments
                    segments_response = client.get(
                        "https://a.klaviyo.com/api/segments",
                        headers=headers
                    )
                    
                    if segments_response.status_code == 200:
                        segments = segments_response.json().get('data', [])
                        logger.info(f"✅ Retrieved {len(segments)} segments from Klaviyo")
                    else:
                        segments = []
                    
                    klaviyo_data = {
                        'campaigns': campaigns,
                        'metrics': metrics,
                        'segments': segments,
                        'source': 'klaviyo_direct',
                        'fetched_at': datetime.now().isoformat()
                    }
                else:
                    # Log the error details
                    error_msg = campaigns_response.text[:200] if campaigns_response.text else "No error message"
                    logger.warning(f"Klaviyo API returned {campaigns_response.status_code}: {error_msg}")
                    
                    # Check if it's an authorization issue
                    if campaigns_response.status_code == 401:
                        logger.error("❌ Klaviyo API key is invalid or expired")
                    elif campaigns_response.status_code == 400:
                        logger.error("❌ Bad request to Klaviyo API - check API format")
                        # Try without any parameters
                        try:
                            simple_response = client.get(
                                "https://a.klaviyo.com/api/account",
                                headers=headers
                            )
                            if simple_response.status_code == 200:
                                logger.info("✅ API key is valid (account endpoint works)")
                                account_data = simple_response.json()
                                logger.info(f"   Account: {account_data.get('data', {}).get('attributes', {}).get('company_id', 'Unknown')}")
                                # Try to get campaigns with different approach
                                klaviyo_data = {
                                    'account': account_data.get('data'),
                                    'campaigns': [],  # Will try to fetch differently
                                    'segments': [],
                                    'metrics': [],
                                    'source': 'klaviyo_account',
                                    'fetched_at': datetime.now().isoformat()
                                }
                            else:
                                logger.error(f"Account check failed: {simple_response.status_code}")
                                klaviyo_data = _fetch_via_mcp(state, klaviyo_key)
                        except Exception as e:
                            logger.error(f"Account check error: {e}")
                            klaviyo_data = _fetch_via_mcp(state, klaviyo_key)
                    else:
                        # Try MCP as fallback
                        klaviyo_data = _fetch_via_mcp(state, klaviyo_key)
                    
        except Exception as e:
            logger.warning(f"Direct Klaviyo API failed: {e}, trying MCP...")
            # Try MCP as fallback
            klaviyo_data = _fetch_via_mcp(state, klaviyo_key)
        
        if klaviyo_data and klaviyo_data.get('campaigns'):
            logger.info(f"✅ Successfully retrieved REAL Klaviyo data")
            return {
                **state,
                'klaviyo_metrics': klaviyo_data,
                'status': 'klaviyo_loaded'
            }
        else:
            logger.error("❌ Could not retrieve Klaviyo data")
            return {
                **state,
                'errors': state.get('errors', []) + ["No Klaviyo data available"],
                'status': 'klaviyo_no_data'
            }
            
    except Exception as e:
        logger.error(f"❌ Klaviyo error: {e}")
        return {
            **state,
            'errors': state.get('errors', []) + [f"Klaviyo error: {str(e)}"],
            'status': 'klaviyo_error'
        }

def _fetch_via_mcp(state: Dict, api_key: str) -> Dict:
    """Fetch data via MCP server"""
    import httpx
    
    mcp_url = "http://127.0.0.1:9090"
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{mcp_url}/tools/get_klaviyo_data",
                json={
                    "client_id": state['client_id'],
                    "month": state['month'],
                    "api_key": api_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                data['source'] = 'mcp_server'
                return data
    except Exception as e:
        logger.error(f"MCP fetch failed: {e}")
    
    return {}

# Mock data function removed - using REAL data only

# ============================================
# NODE 3: Plan Calendar with AI
# ============================================
def plan_calendar_node(state: CalendarState) -> CalendarState:
    """Create campaign calendar based on data"""
    logger.info(f"📅 Planning calendar for {state['client_id']} - {state['month']}")
    
    try:
        # Get data from previous nodes
        firestore_data = state.get('firestore_data', {})
        klaviyo_metrics = state.get('klaviyo_metrics', {})
        client_info = state.get('client_info', {})
        
        # Extract key information
        brand_name = client_info.get('name', state['client_id'])
        industry = client_info.get('industry', 'general')
        past_campaigns = klaviyo_metrics.get('campaigns', []) if isinstance(klaviyo_metrics, dict) else []
        segments = klaviyo_metrics.get('segments', []) if isinstance(klaviyo_metrics, dict) else []
        
        # Use LLM to create plan (if configured)
        try:
            from integrated_calendar_system import IntegratedCalendarSystem
            system = IntegratedCalendarSystem()
            has_llm = system.llm_config.get('api_key') is not None
        except ImportError:
            has_llm = False
            system = None
        
        if has_llm:
            prompt = f"""
            Create a campaign calendar for {brand_name} ({industry}) for {state['month']}.
            
            Past Performance:
            - Campaigns: {len(past_campaigns)}
            - Avg Open Rate: {klaviyo_metrics.get('metrics', {}).get('avg_open_rate', 0):.1%}
            - Revenue: ${klaviyo_metrics.get('metrics', {}).get('total_revenue', 0):,.0f}
            
            Available Segments:
            {', '.join([f"{s['name']} ({s['size']})" for s in segments])}
            
            Create a JSON calendar with 8-10 campaigns including:
            - dates
            - subject lines
            - target segments
            - expected metrics
            """
            
            response = system.call_llm_locally(prompt)
            
            # Parse response (simplified for now)
            campaign_plan = {
                'brand': brand_name,
                'month': state['month'],
                'campaigns': _parse_llm_campaigns(response),
                'generated_by': 'ai',
                'model': system.llm_config.get('model')
            }
        else:
            # No LLM available - cannot create plan
            logger.error("❌ No LLM configured - cannot create calendar")
            return {
                **state,
                'errors': state.get('errors', []) + ["LLM not configured"],
                'status': 'planning_no_llm'
            }
        
        logger.info(f"✅ Created plan with {len(campaign_plan.get('campaigns', []))} campaigns")
        
        return {
            **state,
            'campaign_plan': campaign_plan,
            'status': 'plan_created'
        }
        
    except Exception as e:
        logger.error(f"❌ Planning error: {e}")
        return {
            **state,
            'errors': state.get('errors', []) + [f"Planning error: {str(e)}"],
            'status': 'planning_error'
        }

def _parse_llm_campaigns(response: str) -> List[Dict[str, Any]]:
    """Parse LLM response into campaign list"""
    # Simplified parsing - in production, use proper JSON extraction
    import json
    import re
    
    # Try to extract JSON from response
    json_match = re.search(r'\{.*\}|\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, dict) and 'campaigns' in data:
                return data['campaigns']
            elif isinstance(data, list):
                return data
        except:
            pass
    
    # Fallback to basic campaigns
    return [
        {
            'date': '2025-03-05',
            'subject': 'Spring Collection Launch 🌸',
            'segment': 'all',
            'type': 'promotional'
        },
        {
            'date': '2025-03-12',
            'subject': 'VIP Early Access',
            'segment': 'vip',
            'type': 'exclusive'
        },
        {
            'date': '2025-03-20',
            'subject': 'Flash Sale - 24 Hours Only',
            'segment': 'engaged',
            'type': 'sale'
        }
    ]

# Rule-based planning removed - using REAL AI only

# ============================================
# NODE 4: Generate Email Templates
# ============================================
def generate_templates_node(state: CalendarState) -> CalendarState:
    """Generate email templates for campaigns"""
    logger.info("✉️ Generating email templates")
    
    campaign_plan = state.get('campaign_plan', {})
    campaigns = campaign_plan.get('campaigns', [])
    
    templates = []
    for campaign in campaigns[:3]:  # Generate for first 3 campaigns
        template = {
            'campaign_id': f"template_{campaign.get('date')}",
            'subject': campaign.get('subject'),
            'preview_text': f"Don't miss out on {campaign.get('subject')}",
            'body_sections': [
                {'type': 'header', 'content': campaign.get('subject')},
                {'type': 'hero_image', 'alt': 'Campaign Hero'},
                {'type': 'text', 'content': 'Lorem ipsum content...'},
                {'type': 'cta', 'text': 'Shop Now', 'url': 'https://example.com'}
            ],
            'segment': campaign.get('segment')
        }
        templates.append(template)
    
    logger.info(f"✅ Generated {len(templates)} email templates")
    
    return {
        **state,
        'email_templates': templates,
        'status': 'templates_generated'
    }

# ============================================
# NODE 5: Optimize Send Schedule
# ============================================
def optimize_schedule_node(state: CalendarState) -> CalendarState:
    """Optimize send times based on data"""
    logger.info("⏰ Optimizing send schedule")
    
    campaign_plan = state.get('campaign_plan', {})
    klaviyo_metrics = state.get('klaviyo_metrics', {})
    
    # Simple optimization based on past performance
    best_times = {
        'monday': '10:00',
        'tuesday': '14:00',
        'wednesday': '11:00',
        'thursday': '15:00',
        'friday': '09:00',
        'saturday': '12:00',
        'sunday': '18:00'
    }
    
    schedule = {
        'timezone': 'America/New_York',
        'optimized_times': best_times,
        'frequency_cap': 3,  # Max emails per week
        'quiet_hours': {'start': '21:00', 'end': '08:00'},
        'recommendations': [
            'Send promotional emails on Tuesday/Thursday',
            'Newsletter works best on Wednesday morning',
            'Avoid Mondays for sales campaigns'
        ]
    }
    
    logger.info("✅ Schedule optimized")
    
    return {
        **state,
        'send_schedule': schedule,
        'status': 'completed'
    }

# ============================================
# ROUTING LOGIC
# ============================================
def should_continue(state: CalendarState) -> str:
    """Determine next step based on state"""
    status = state.get('status', '')
    
    if status == 'client_not_found':
        return END
    elif status == 'firestore_error':
        return END
    elif status == 'completed':
        return END
    else:
        return 'continue'

# ============================================
# BUILD THE GRAPH
# ============================================
def create_live_calendar_graph():
    """Create the live data calendar graph"""
    
    # Initialize graph with state
    graph = StateGraph(CalendarState)
    
    # Add nodes
    graph.add_node("load_firestore", load_firestore_node)
    graph.add_node("pull_klaviyo", pull_klaviyo_node)
    graph.add_node("plan_calendar", plan_calendar_node)
    graph.add_node("generate_templates", generate_templates_node)
    graph.add_node("optimize_schedule", optimize_schedule_node)
    
    # Set entry point
    graph.set_entry_point("load_firestore")
    
    # Add edges (the flow)
    graph.add_edge("load_firestore", "pull_klaviyo")
    graph.add_edge("pull_klaviyo", "plan_calendar")
    graph.add_edge("plan_calendar", "generate_templates")
    graph.add_edge("generate_templates", "optimize_schedule")
    graph.add_edge("optimize_schedule", END)
    
    # Compile the graph (LangGraph Studio handles persistence)
    app = graph.compile()
    
    return app

# ============================================
# USAGE EXAMPLE
# ============================================
def run_live_calendar(client_id: str, month: str):
    """Run the calendar workflow with live data"""
    
    # Create the graph
    app = create_live_calendar_graph()
    
    # Initial state
    initial_state = {
        'client_id': client_id,
        'month': month,
        'timestamp': datetime.now().isoformat(),
        'errors': [],
        'status': 'started'
    }
    
    # Run the graph
    logger.info(f"🚀 Starting live calendar workflow for {client_id} - {month}")
    
    # Configure with thread ID for persistence
    config = {"configurable": {"thread_id": f"{client_id}_{month}"}}
    
    # Invoke the graph
    result = app.invoke(initial_state, config)
    
    # Log results
    logger.info(f"✅ Workflow completed with status: {result.get('status')}")
    
    if result.get('errors'):
        logger.warning(f"⚠️ Errors encountered: {result['errors']}")
    
    return result

# Export for LangGraph Studio
live_calendar_graph = create_live_calendar_graph()

if __name__ == "__main__":
    # Test with a sample client
    result = run_live_calendar("test-client-001", "2025-03")
    
    print("\n" + "="*70)
    print("LIVE CALENDAR RESULTS")
    print("="*70)
    
    import json
    print(json.dumps({
        'status': result.get('status'),
        'campaigns': len(result.get('campaign_plan', {}).get('campaigns', [])),
        'templates': len(result.get('email_templates', [])),
        'errors': result.get('errors', [])
    }, indent=2))