#!/usr/bin/env python3
"""
CREATE YOUR FIRST CALENDAR - Ready to Run!
Just update the CLIENT_CONFIG below and run this script.
"""
import os
import json
from datetime import datetime
from graph.live_graph import create_live_calendar_graph

# ============================================
# STEP 1: Configure Your Client
# ============================================
CLIENT_CONFIG = {
    'client_id': 'test-fashion-001',  # Change this to your client ID
    'month': '2025-03',              # Change to your target month
    'brand_name': 'Fashion Brand',   # Optional: Brand display name
    'industry': 'fashion',           # Optional: Industry context
}

# ============================================
# STEP 2: Customize Prompts (Optional)
# ============================================
CUSTOM_PROMPTS = {
    'campaign_planner': """
You are planning email campaigns for {brand} in {month}.
Create 10-12 email campaigns including:
- Promotional campaigns (sales, discounts)
- Content campaigns (style guides, trends)
- Engagement campaigns (surveys, loyalty)

For each campaign provide:
- Date (specific day in {month})
- Subject line (compelling, 40-60 characters)
- Target segment (vip, new, engaged, all)
- Campaign type
- Key message

Focus on fashion industry best practices and {month} seasonal trends.
Format as JSON list of campaigns.
""",
    
    'copy_smith': """
Write email copy for {brand} that:
- Uses casual, friendly tone
- Includes emojis sparingly
- Has clear CTAs
- Mobile-optimized length
- Focuses on benefits over features
"""
}

# ============================================
# MAIN EXECUTION
# ============================================
def create_calendar():
    """Create a calendar with live data"""
    
    print("\n" + "="*70)
    print("📅 CALENDAR CREATION SYSTEM")
    print("="*70 + "\n")
    
    # Set up environment (if needed)
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'emailpilot-438321'
    
    # Optional: Apply custom prompts
    if CUSTOM_PROMPTS:
        print("📝 Loading custom prompts...")
        try:
            from integrated_calendar_system import IntegratedCalendarSystem
            system = IntegratedCalendarSystem()
            
            for agent_name, prompt in CUSTOM_PROMPTS.items():
                system.edit_agent_prompt(agent_name, prompt)
                print(f"   ✅ Updated {agent_name} prompt")
        except Exception as e:
            print(f"   ⚠️ Could not update prompts: {e}")
            print("   Continuing with default prompts...")
    
    # Create the graph
    print("\n🔧 Initializing calendar system...")
    app = create_live_calendar_graph()
    
    # Prepare initial state
    initial_state = {
        'client_id': CLIENT_CONFIG['client_id'],
        'month': CLIENT_CONFIG['month'],
        'timestamp': datetime.now().isoformat(),
        'errors': [],
        'status': 'started'
    }
    
    # Add optional context
    if 'brand_name' in CLIENT_CONFIG:
        initial_state['brand_name'] = CLIENT_CONFIG['brand_name']
    if 'industry' in CLIENT_CONFIG:
        initial_state['industry'] = CLIENT_CONFIG['industry']
    
    # Run the calendar creation
    print(f"\n🚀 Creating calendar for {CLIENT_CONFIG['client_id']} - {CLIENT_CONFIG['month']}")
    print("   This will:")
    print("   1. Check Firestore for client data")
    print("   2. Pull Klaviyo metrics (or use mock data)")
    print("   3. Generate calendar with AI")
    print("   4. Create email templates")
    print("   5. Optimize send schedule")
    print()
    
    # Configure with thread ID for persistence
    config = {
        "configurable": {
            "thread_id": f"{CLIENT_CONFIG['client_id']}_{CLIENT_CONFIG['month']}"
        }
    }
    
    # Execute!
    try:
        result = app.invoke(initial_state, config)
        
        # Process results
        status = result.get('status', 'unknown')
        errors = result.get('errors', [])
        
        print("="*70)
        print("📊 RESULTS")
        print("="*70 + "\n")
        
        print(f"Status: {status}")
        
        if errors:
            print(f"\n⚠️ Issues encountered:")
            for error in errors:
                print(f"   - {error}")
        
        # Show what was created
        if result.get('firestore_data'):
            client_data = result['firestore_data'].get('client', {})
            print(f"\n✅ Client Data:")
            print(f"   Name: {client_data.get('name', 'Not found')}")
            print(f"   Status: {'Found in Firestore' if client_data else 'Using defaults'}")
        
        if result.get('klaviyo_metrics'):
            metrics = result['klaviyo_metrics']
            print(f"\n✅ Klaviyo Metrics:")
            print(f"   Campaigns: {len(metrics.get('campaigns', []))}")
            print(f"   Segments: {len(metrics.get('segments', []))}")
            if metrics.get('mock_data'):
                print(f"   Note: Using mock data (no API key found)")
        
        if result.get('campaign_plan'):
            plan = result['campaign_plan']
            campaigns = plan.get('campaigns', [])
            print(f"\n✅ Campaign Calendar:")
            print(f"   Total campaigns: {len(campaigns)}")
            print(f"   Generated by: {plan.get('generated_by', 'unknown')}")
            
            if campaigns:
                print(f"\n   📅 First 5 Campaigns:")
                for i, campaign in enumerate(campaigns[:5], 1):
                    print(f"   {i}. {campaign.get('date', 'No date')} - {campaign.get('subject', 'No subject')}")
                    print(f"      Segment: {campaign.get('segment', 'all')}, Type: {campaign.get('type', 'general')}")
        
        if result.get('email_templates'):
            templates = result['email_templates']
            print(f"\n✅ Email Templates:")
            print(f"   Generated: {len(templates)} templates")
            
            if templates:
                print(f"\n   📧 Template Previews:")
                for i, template in enumerate(templates[:2], 1):
                    print(f"   {i}. {template.get('subject')}")
                    print(f"      Preview: {template.get('preview_text', 'No preview')}")
        
        if result.get('send_schedule'):
            schedule = result['send_schedule']
            print(f"\n✅ Send Schedule:")
            print(f"   Timezone: {schedule.get('timezone')}")
            print(f"   Frequency cap: {schedule.get('frequency_cap')} emails/week")
            
            if schedule.get('recommendations'):
                print(f"\n   💡 Recommendations:")
                for rec in schedule['recommendations'][:3]:
                    print(f"   - {rec}")
        
        # Save full results
        output_filename = f"calendar_{CLIENT_CONFIG['client_id']}_{CLIENT_CONFIG['month'].replace('-', '')}.json"
        with open(output_filename, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Full results saved to: {output_filename}")
        
        # Next steps
        print("\n" + "="*70)
        print("🎯 NEXT STEPS")
        print("="*70)
        print("""
1. Review the generated calendar in the JSON file
2. Tune prompts if needed (edit CUSTOM_PROMPTS above)
3. Test with different months and clients
4. Use Admin Dashboard for permanent prompt changes
5. Access LangGraph Studio for visual debugging

To edit prompts permanently:
- Open: http://localhost:8000/static/dist/index.html
- Go to Admin → Agent Prompts
- Edit and save

To see visual workflow:
- Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- Select 'live_calendar' graph
""")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error creating calendar: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Run the calendar creation
    result = create_calendar()
    
    # Quick summary
    if result and result.get('campaign_plan'):
        campaigns = result['campaign_plan'].get('campaigns', [])
        print(f"\n✨ Successfully created calendar with {len(campaigns)} campaigns!")
    else:
        print("\n⚠️ Calendar creation had issues. Check the logs above.")