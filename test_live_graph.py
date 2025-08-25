#!/usr/bin/env python3
"""
Test the Live Data Calendar Graph
No datasets needed - just pass client_id and month!
"""
import sys
import json
from datetime import datetime

def test_live_graph():
    """Test the live graph with real data sources"""
    print("\n" + "="*70)
    print("LIVE DATA GRAPH TEST")
    print("="*70 + "\n")
    
    # Import the live graph
    from graph.live_graph import create_live_calendar_graph
    
    # Create the graph
    print("🔧 Creating live calendar graph...")
    app = create_live_calendar_graph()
    print("✅ Graph created\n")
    
    # Test cases - just need client_id and month
    test_cases = [
        {
            "client_id": "fashionbrand-001",
            "month": "2025-03",
            "description": "Fashion brand spring campaign"
        },
        {
            "client_id": "techstartup-002", 
            "month": "2025-04",
            "description": "Tech startup product launch"
        },
        {
            "client_id": "beautybrand-003",
            "month": "2025-05",
            "description": "Beauty brand Mother's Day"
        }
    ]
    
    print("📊 Running test cases:\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['description']}")
        print(f"  Client: {test['client_id']}")
        print(f"  Month: {test['month']}")
        
        # Initial state - minimal!
        initial_state = {
            'client_id': test['client_id'],
            'month': test['month'],
            'timestamp': datetime.now().isoformat(),
            'errors': [],
            'status': 'started'
        }
        
        # Run with thread ID for persistence
        config = {"configurable": {"thread_id": f"{test['client_id']}_{test['month']}"}}
        
        try:
            # Invoke the graph
            result = app.invoke(initial_state, config)
            
            # Check results
            status = result.get('status', 'unknown')
            errors = result.get('errors', [])
            
            if status == 'completed' and not errors:
                print(f"  ✅ Success!")
                
                # Show what was fetched/generated
                if result.get('firestore_data'):
                    print(f"     • Firestore: Client data loaded")
                if result.get('klaviyo_metrics'):
                    campaigns = result['klaviyo_metrics'].get('campaigns', [])
                    print(f"     • Klaviyo: {len(campaigns)} campaigns found")
                if result.get('campaign_plan'):
                    plan_campaigns = result['campaign_plan'].get('campaigns', [])
                    print(f"     • Plan: {len(plan_campaigns)} campaigns planned")
                if result.get('email_templates'):
                    print(f"     • Templates: {len(result['email_templates'])} generated")
                if result.get('send_schedule'):
                    print(f"     • Schedule: Optimized")
            else:
                print(f"  ⚠️ Status: {status}")
                if errors:
                    print(f"     Errors: {', '.join(errors[:2])}")
            
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
        
        print()
    
    # Show how to use in production
    print("="*70)
    print("PRODUCTION USAGE")
    print("="*70)
    print("""
# In your application, just pass the client_id and month:

from graph.live_graph import create_live_calendar_graph

app = create_live_calendar_graph()

# Run for any client
result = app.invoke({
    'client_id': 'your-client-id',
    'month': '2025-03',
    'timestamp': datetime.now().isoformat(),
    'errors': [],
    'status': 'started'
})

# The graph will:
# 1. Load client data from Firestore
# 2. Pull metrics from Klaviyo via MCP
# 3. Plan campaigns with AI
# 4. Generate email templates
# 5. Optimize send schedule

# No dataset files needed!
""")
    
    print("\n✨ The graph fetches everything it needs from live sources!")
    print("📁 Firestore → 📊 Klaviyo → 🤖 AI Planning → 📅 Calendar\n")

if __name__ == "__main__":
    test_live_graph()