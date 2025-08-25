#!/usr/bin/env python3
"""
CREATE REAL CALENDAR WITH REAL DATA
No mock data - connects to real Firestore and Klaviyo
Full visibility in LangGraph Studio
"""
import os
import json
import sys
from datetime import datetime
from graph.live_graph import create_live_calendar_graph

# Set up environment
os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'

def create_real_calendar(client_id: str = None, month: str = None):
    """Create a calendar with REAL data from Firestore and Klaviyo"""
    
    print("\n" + "="*70)
    print("📅 REAL CALENDAR CREATION (NO MOCK DATA)")
    print("="*70 + "\n")
    
    # If no client specified, list available clients
    if not client_id:
        from google.cloud import firestore
        db = firestore.Client(project='emailpilot-438321')
        
        print("📊 Available REAL clients in Firestore:\n")
        clients_ref = db.collection('clients')
        clients = list(clients_ref.stream())
        
        valid_clients = []
        for doc in clients:
            client_data = doc.to_dict()
            has_key = bool(client_data.get('klaviyo_api_key'))
            print(f"  • {doc.id}: {client_data.get('name', 'Unknown')}")
            if has_key:
                print(f"    ✅ Has Klaviyo API key")
                valid_clients.append(doc.id)
            else:
                print(f"    ⚠️ No Klaviyo key")
        
        if valid_clients:
            # Use first client with API key
            client_id = valid_clients[0]
            print(f"\n✅ Using client: {client_id}")
        else:
            print("\n❌ No clients with Klaviyo API keys found")
            print("\nTo add a Klaviyo key to a client:")
            print("  1. Go to Firestore console")
            print("  2. Edit client document")
            print("  3. Add 'klaviyo_api_key' field")
            return None
    
    if not month:
        month = "2025-03"  # Default to March 2025
    
    print(f"\n🎯 Creating calendar for:")
    print(f"   Client: {client_id}")
    print(f"   Month: {month}")
    
    # Create the graph
    print("\n🔧 Initializing live data graph...")
    app = create_live_calendar_graph()
    
    # Initial state - minimal, real data will be fetched
    initial_state = {
        'client_id': client_id,
        'month': month,
        'timestamp': datetime.now().isoformat(),
        'errors': [],
        'status': 'started'
    }
    
    # Configure with thread ID for LangGraph Studio visibility
    config = {
        "configurable": {
            "thread_id": f"{client_id}_{month}_{datetime.now().strftime('%H%M%S')}"
        }
    }
    
    print(f"\n📡 Thread ID for LangGraph Studio: {config['configurable']['thread_id']}")
    print("\n🚀 Executing workflow (check LangGraph Studio to see live progress)...")
    print("   URL: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024")
    print("\n   Steps:")
    print("   1. Loading client from Firestore...")
    
    try:
        # Execute the graph
        result = app.invoke(initial_state, config)
        
        # Process results
        status = result.get('status', 'unknown')
        errors = result.get('errors', [])
        
        print("\n" + "="*70)
        print("📊 RESULTS")
        print("="*70 + "\n")
        
        print(f"Status: {status}")
        
        if errors:
            print(f"\n⚠️ Issues:")
            for error in errors:
                print(f"   - {error}")
        
        # Show Firestore data
        if result.get('firestore_data'):
            client_data = result['firestore_data'].get('client', {})
            print(f"\n✅ Firestore Client Data:")
            print(f"   Name: {client_data.get('name', 'Unknown')}")
            print(f"   Industry: {client_data.get('industry', 'Not specified')}")
            
            # Check all possible API key fields
            has_api_key = (
                client_data.get('klaviyo_api_key') or
                client_data.get('klaviyo_private_key') or
                client_data.get('api_key_secret') or
                client_data.get('klaviyo_api_key_secret') or
                client_data.get('klaviyo_secret_name')
            )
            print(f"   Has API Key: {'Yes' if has_api_key else 'No'}")
            
            campaigns = result['firestore_data'].get('campaigns', [])
            if campaigns:
                print(f"   Existing campaigns in Firestore: {len(campaigns)}")
        
        # Show Klaviyo data
        if result.get('klaviyo_metrics'):
            metrics = result['klaviyo_metrics']
            print(f"\n✅ Klaviyo Data (REAL):")
            print(f"   Source: {metrics.get('source', 'unknown')}")
            print(f"   Campaigns: {len(metrics.get('campaigns', []))}")
            print(f"   Segments: {len(metrics.get('segments', []))}")
            print(f"   Metrics: {len(metrics.get('metrics', []))}")
            
            if metrics.get('campaigns'):
                print(f"\n   Recent Campaigns:")
                for camp in metrics['campaigns'][:3]:
                    if isinstance(camp, dict):
                        print(f"   - {camp.get('attributes', {}).get('name', camp.get('name', 'Unknown'))}")
        
        # Show AI-generated calendar
        if result.get('campaign_plan'):
            plan = result['campaign_plan']
            campaigns = plan.get('campaigns', [])
            print(f"\n✅ AI-Generated Calendar:")
            print(f"   Total campaigns: {len(campaigns)}")
            print(f"   Generated by: {plan.get('generated_by', 'unknown')}")
            print(f"   Model: {plan.get('model', 'unknown')}")
            
            if campaigns:
                print(f"\n   📅 Campaign Schedule:")
                for i, campaign in enumerate(campaigns[:8], 1):
                    print(f"   {i}. {campaign.get('date', 'No date')} - {campaign.get('subject', 'No subject')}")
                    if campaign.get('segment'):
                        print(f"      Target: {campaign.get('segment')}, Type: {campaign.get('type', 'general')}")
                    if campaign.get('expected_open_rate'):
                        print(f"      Expected open rate: {campaign.get('expected_open_rate', 0):.1%}")
        
        # Show email templates
        if result.get('email_templates'):
            templates = result['email_templates']
            print(f"\n✅ Email Templates Generated: {len(templates)}")
            
            for i, template in enumerate(templates[:2], 1):
                print(f"\n   Template {i}:")
                print(f"   Subject: {template.get('subject')}")
                print(f"   Preview: {template.get('preview_text', 'No preview')}")
                print(f"   Sections: {len(template.get('body_sections', []))}")
        
        # Show send schedule
        if result.get('send_schedule'):
            schedule = result['send_schedule']
            print(f"\n✅ Optimized Send Schedule:")
            print(f"   Timezone: {schedule.get('timezone')}")
            print(f"   Frequency cap: {schedule.get('frequency_cap')} emails/week")
            
            best_times = schedule.get('optimized_times', {})
            if best_times:
                print(f"\n   Best send times:")
                for day, time in list(best_times.items())[:3]:
                    print(f"   - {day.capitalize()}: {time}")
        
        # Save full results
        output_filename = f"real_calendar_{client_id}_{month.replace('-', '')}.json"
        with open(output_filename, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Full results saved to: {output_filename}")
        
        # LangGraph Studio instructions
        print("\n" + "="*70)
        print("🔍 VIEW IN LANGGRAPH STUDIO")
        print("="*70)
        print(f"""
1. Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
2. Select "live_calendar" graph
3. Find thread: {config['configurable']['thread_id']}
4. See the complete execution flow with all data

You can also re-run with this exact configuration:
{json.dumps(initial_state, indent=2)}
""")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main entry point"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Create real calendar with Firestore and Klaviyo data')
    parser.add_argument('--client', type=str, help='Client ID from Firestore')
    parser.add_argument('--month', type=str, help='Month (YYYY-MM format)', default='2025-03')
    args = parser.parse_args()
    
    # Create the calendar
    result = create_real_calendar(args.client, args.month)
    
    if result and result.get('status') == 'completed':
        print("\n✨ SUCCESS! Real calendar created with:")
        print(f"   • Real Firestore client data")
        print(f"   • Real Klaviyo metrics (if API key present)")
        print(f"   • AI-generated campaign plan")
        print(f"   • Optimized send schedule")
    else:
        print("\n⚠️ Calendar creation had issues. Check logs above.")

if __name__ == "__main__":
    main()