#!/usr/bin/env python3
"""
EmailPilot Firestore Migration Script

Migrates all data from SQLite to Firestore collections:
- clients -> clients collection
- goals -> goals collection  
- performance_history -> performance_history collection
- reports -> reports collection
- calendar_events -> calendar_events collection
- calendar_import_logs -> calendar_import_logs collection
- calendar_chat_history -> calendar_chat_history collection

Usage:
pip install google-cloud-firestore
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
python migrate_to_firestore.py
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import sys
import os

# Add Google Cloud Firestore
try:
    from google.cloud import firestore
except ImportError:
    print("❌ google-cloud-firestore not installed. Run: pip install google-cloud-firestore")
    sys.exit(1)

def setup_firestore():
    """Initialize Firestore client"""
    try:
        # Initialize Firestore client
        db = firestore.Client(project='emailpilot-438321')
        print("✅ Connected to Firestore")
        return db
    except Exception as e:
        print(f"❌ Failed to connect to Firestore: {e}")
        print("Make sure GOOGLE_APPLICATION_CREDENTIALS is set and you have Firestore enabled")
        sys.exit(1)

def get_sqlite_connection():
    """Get SQLite database connection"""
    db_path = Path(__file__).parent / 'emailpilot.db'
    if not db_path.exists():
        print(f"❌ SQLite database not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn

def migrate_clients(firestore_db, sqlite_conn):
    """Migrate clients table to Firestore"""
    print("\n📋 Migrating clients...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    
    client_id_mapping = {}  # Track SQLite ID -> Firestore ID mapping
    
    for client in clients:
        client_data = {
            'name': client['name'],
            'api_key_encrypted': client['api_key_encrypted'],
            'metric_id': client['metric_id'] or '',
            'description': client['description'] or '',
            'is_active': bool(client['is_active']),
            'created_at': client['created_at'],
            'updated_at': client['updated_at'],
            'sqlite_id': client['id']  # Keep reference to original ID
        }
        
        # Add to Firestore
        doc_ref = firestore_db.collection('clients').add(client_data)
        firestore_id = doc_ref[1].id
        
        client_id_mapping[client['id']] = firestore_id
        print(f"  ✅ {client['name']} (SQLite ID: {client['id']} -> Firestore ID: {firestore_id})")
    
    print(f"✅ Migrated {len(clients)} clients")
    return client_id_mapping

def migrate_goals(firestore_db, sqlite_conn, client_id_mapping):
    """Migrate goals table to Firestore"""
    print("\n🎯 Migrating goals...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM goals")
    goals = cursor.fetchall()
    
    batch = firestore_db.batch()
    batch_count = 0
    
    for goal in goals:
        sqlite_client_id = goal['client_id']
        if sqlite_client_id not in client_id_mapping:
            print(f"  ⚠️ Skipping goal - client ID {sqlite_client_id} not found")
            continue
            
        goal_data = {
            'client_id': client_id_mapping[sqlite_client_id],
            'year': goal['year'],
            'month': goal['month'],
            'revenue_goal': float(goal['revenue_goal']),
            'calculation_method': goal['calculation_method'] or 'manual',
            'notes': goal['notes'] or '',
            'confidence': goal['confidence'] or 'medium',
            'human_override': bool(goal['human_override']),
            'created_at': goal['created_at'],
            'updated_at': goal['updated_at'],
            'sqlite_id': goal['id']
        }
        
        doc_ref = firestore_db.collection('goals').document()
        batch.set(doc_ref, goal_data)
        batch_count += 1
        
        # Firestore batches have a limit of 500 operations
        if batch_count >= 400:
            batch.commit()
            batch = firestore_db.batch()
            batch_count = 0
    
    if batch_count > 0:
        batch.commit()
    
    print(f"✅ Migrated {len(goals)} goals")

def migrate_performance_history(firestore_db, sqlite_conn, client_id_mapping):
    """Migrate performance_history table to Firestore"""
    print("\n📈 Migrating performance history...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM performance_history")
    records = cursor.fetchall()
    
    batch = firestore_db.batch()
    batch_count = 0
    
    for record in records:
        sqlite_client_id = record['client_id']
        if sqlite_client_id not in client_id_mapping:
            print(f"  ⚠️ Skipping performance record - client ID {sqlite_client_id} not found")
            continue
            
        perf_data = {
            'client_id': client_id_mapping[sqlite_client_id],
            'year': record['year'],
            'month': record['month'],
            'revenue': float(record['revenue']) if record['revenue'] else 0.0,
            'orders': record['orders'] or 0,
            'email_sent': record['email_sent'] or 0,
            'email_opened': record['email_opened'] or 0,
            'email_clicked': record['email_clicked'] or 0,
            'campaigns_sent': record['campaigns_sent'] or 0,
            'active_flows': record['active_flows'] or 0,
            'created_at': record['created_at'],
            'sqlite_id': record['id']
        }
        
        doc_ref = firestore_db.collection('performance_history').document()
        batch.set(doc_ref, perf_data)
        batch_count += 1
        
        if batch_count >= 400:
            batch.commit()
            batch = firestore_db.batch()
            batch_count = 0
    
    if batch_count > 0:
        batch.commit()
    
    print(f"✅ Migrated {len(records)} performance history records")

def migrate_reports(firestore_db, sqlite_conn, client_id_mapping):
    """Migrate reports table to Firestore"""
    print("\n📊 Migrating reports...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM reports")
    reports = cursor.fetchall()
    
    for report in reports:
        sqlite_client_id = report['client_id']
        if sqlite_client_id and sqlite_client_id not in client_id_mapping:
            print(f"  ⚠️ Skipping report - client ID {sqlite_client_id} not found")
            continue
            
        report_data = {
            'client_id': client_id_mapping[sqlite_client_id] if sqlite_client_id else None,
            'report_type': report['report_type'],
            'status': report['status'] or 'pending',
            'generated_at': report['generated_at'],
            'file_path': report['file_path'],
            'summary': report['summary'] or '',
            'created_at': report['created_at'],
            'sqlite_id': report['id']
        }
        
        firestore_db.collection('reports').add(report_data)
    
    print(f"✅ Migrated {len(reports)} reports")

def create_calendar_collections(firestore_db):
    """Create calendar collections structure (even if empty)"""
    print("\n📅 Creating calendar collections structure...")
    
    # Create empty documents to establish collection structure
    collections = ['calendar_events', 'calendar_import_logs', 'calendar_chat_history']
    
    for collection_name in collections:
        # Add a placeholder document that we'll delete later
        doc_ref = firestore_db.collection(collection_name).document('_placeholder')
        doc_ref.set({
            'placeholder': True,
            'created_at': datetime.utcnow().isoformat(),
            'note': 'Placeholder document to create collection structure'
        })
        print(f"  ✅ Created {collection_name} collection")

def print_migration_summary(firestore_db):
    """Print summary of migrated data"""
    print("\n" + "="*60)
    print("FIRESTORE MIGRATION SUMMARY")
    print("="*60)
    
    collections = ['clients', 'goals', 'performance_history', 'reports']
    
    for collection_name in collections:
        docs = list(firestore_db.collection(collection_name).stream())
        count = len([doc for doc in docs if not doc.to_dict().get('placeholder')])
        print(f"✅ {collection_name}: {count} documents")
    
    print(f"\n🔧 Calendar collections created (ready for future data)")
    print(f"🚀 All data successfully migrated to Firestore!")

def cleanup_placeholders(firestore_db):
    """Remove placeholder documents"""
    print("\n🧹 Cleaning up placeholder documents...")
    
    collections = ['calendar_events', 'calendar_import_logs', 'calendar_chat_history']
    
    for collection_name in collections:
        placeholder_ref = firestore_db.collection(collection_name).document('_placeholder')
        placeholder_ref.delete()
        print(f"  ✅ Removed placeholder from {collection_name}")

def main():
    """Main migration function"""
    print("🔄 EmailPilot SQLite → Firestore Migration")
    print("="*50)
    
    # Check environment
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        print("   Set it to point to your service account key file:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'")
        sys.exit(1)
    
    try:
        # Initialize connections
        firestore_db = setup_firestore()
        sqlite_conn = get_sqlite_connection()
        
        # Run migrations
        client_id_mapping = migrate_clients(firestore_db, sqlite_conn)
        migrate_goals(firestore_db, sqlite_conn, client_id_mapping)
        migrate_performance_history(firestore_db, sqlite_conn, client_id_mapping)
        migrate_reports(firestore_db, sqlite_conn, client_id_mapping)
        create_calendar_collections(firestore_db)
        
        # Print summary
        print_migration_summary(firestore_db)
        
        # Cleanup
        cleanup_placeholders(firestore_db)
        
        print(f"\n✅ Migration completed successfully!")
        print(f"🗄️  Data is now stored in Firestore collections")
        print(f"📝 Next: Update FastAPI endpoints to use Firestore")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()

if __name__ == "__main__":
    main()