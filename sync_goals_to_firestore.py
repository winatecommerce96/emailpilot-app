#!/usr/bin/env python3
"""
Sync Goals to Firestore
Syncs local JSON goal files to the EmailPilot Firestore database
"""

import json
import os
import sys
from datetime import datetime
from google.cloud import firestore

def load_local_goals():
    """Load goals from local JSON files"""
    base_path = "/Users/Damon/klaviyo/klaviyo-audit-automation"
    
    # Load base goals
    sales_goals_file = os.path.join(base_path, "sales_goals.json")
    monthly_goals_file = os.path.join(base_path, "monthly_specific_goals.json")
    
    base_goals = {}
    monthly_goals = {}
    
    if os.path.exists(sales_goals_file):
        with open(sales_goals_file, 'r') as f:
            base_goals = json.load(f)
            print(f"✅ Loaded base goals: {len(base_goals.get('goals', {}))} clients")
    else:
        print("❌ sales_goals.json not found")
    
    if os.path.exists(monthly_goals_file):
        with open(monthly_goals_file, 'r') as f:
            monthly_goals = json.load(f)
            print(f"✅ Loaded monthly goals: {len(monthly_goals.get('monthly_goals', {}))} records")
    else:
        print("❌ monthly_specific_goals.json not found")
    
    return base_goals, monthly_goals

def sync_to_firestore(base_goals, monthly_goals):
    """Sync goals to Firestore"""
    try:
        # Initialize Firestore
        db = firestore.Client(project='emailpilot-438321')
        print("✅ Connected to Firestore")
        
        synced_count = 0
        
        # Sync base goals (as fallback/default goals)
        base_client_goals = base_goals.get('goals', {})
        for client_name, goal_data in base_client_goals.items():
            # Create a default goal for current year if no monthly goals exist
            current_year = datetime.now().year
            
            # Check if this client already has monthly goals for current year
            has_current_year_goals = False
            monthly_client_goals = monthly_goals.get('monthly_goals', {})
            
            for monthly_key in monthly_client_goals.keys():
                if monthly_key.startswith(f"{client_name}_{current_year}"):
                    has_current_year_goals = True
                    break
            
            # If no monthly goals for current year, create default ones
            if not has_current_year_goals:
                for month in range(1, 13):
                    doc_ref = db.collection('goals').document()
                    goal_doc = {
                        'client_id': client_name,
                        'client_name': client_name,
                        'year': current_year,
                        'month': month,
                        'revenue_goal': goal_data.get('monthly_revenue_goal', 10000),
                        'calculation_method': goal_data.get('calculation_method', 'ai_suggested'),
                        'notes': f"Synced from sales_goals.json: {goal_data.get('notes', '')}",
                        'confidence': goal_data.get('confidence', 'medium'),
                        'human_override': False,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'synced_from': 'sales_goals.json'
                    }
                    doc_ref.set(goal_doc)
                    synced_count += 1
                
                print(f"  ✅ {client_name}: Created 12 monthly goals for {current_year}")
        
        # Sync specific monthly goals
        monthly_client_goals = monthly_goals.get('monthly_goals', {})
        for monthly_key, goal_data in monthly_client_goals.items():
            # Parse the monthly key: client_name_year_month
            parts = monthly_key.rsplit('_', 2)  # Split from right to handle client names with underscores
            if len(parts) == 3:
                client_name = parts[0]
                try:
                    year = int(parts[1])
                    month = int(parts[2])
                except ValueError:
                    print(f"❌ Invalid key format: {monthly_key}")
                    continue
                
                # Check if this goal already exists in Firestore
                existing_query = db.collection('goals').where('client_id', '==', client_name).where('year', '==', year).where('month', '==', month)
                existing_docs = list(existing_query.stream())
                
                goal_doc = {
                    'client_id': client_name,
                    'client_name': goal_data.get('client_name', client_name),
                    'year': year,
                    'month': month,
                    'revenue_goal': goal_data.get('revenue_goal', 10000),
                    'calculation_method': goal_data.get('calculation_method', 'ai_suggested'),
                    'notes': goal_data.get('notes', ''),
                    'confidence': goal_data.get('confidence', 'medium'),
                    'human_override': goal_data.get('human_override', False),
                    'updated_at': datetime.now().isoformat(),
                    'synced_from': 'monthly_specific_goals.json'
                }
                
                if existing_docs:
                    # Update existing
                    existing_docs[0].reference.update(goal_doc)
                    print(f"  🔄 Updated: {client_name} {year}-{month:02d}")
                else:
                    # Create new
                    goal_doc['created_at'] = datetime.now().isoformat()
                    db.collection('goals').document().set(goal_doc)
                    print(f"  ✅ Created: {client_name} {year}-{month:02d}")
                
                synced_count += 1
        
        print(f"\n🎉 Sync completed! {synced_count} goals synced to Firestore")
        
        # Verify the sync
        total_goals = len(list(db.collection('goals').stream()))
        print(f"📊 Total goals in Firestore: {total_goals}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error syncing to Firestore: {e}")
        return False

def main():
    """Main sync process"""
    print("🔄 GOALS TO FIRESTORE SYNC")
    print("=" * 40)
    
    # Load local goals
    base_goals, monthly_goals = load_local_goals()
    
    if not base_goals.get('goals') and not monthly_goals.get('monthly_goals'):
        print("❌ No local goal data found. Run resumable_goal_generator.py first.")
        sys.exit(1)
    
    # Confirm sync
    base_count = len(base_goals.get('goals', {}))
    monthly_count = len(monthly_goals.get('monthly_goals', {}))
    
    print(f"\n📋 Ready to sync:")
    print(f"   • Base goals: {base_count} clients")
    print(f"   • Monthly goals: {monthly_count} specific goals")
    
    confirm = input("\nProceed with sync? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Sync cancelled.")
        sys.exit(0)
    
    # Perform sync
    success = sync_to_firestore(base_goals, monthly_goals)
    
    if success:
        print("\n✅ Goals successfully synced to Firestore!")
        print("   The EmailPilot Goals dashboard should now have accurate data.")
    else:
        print("\n❌ Sync failed. Check error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()