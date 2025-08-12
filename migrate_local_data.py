#!/usr/bin/env python3
"""
EmailPilot Data Migration Script

Migrates existing local client data, goals, and historical performance data 
to the EmailPilot web application database.

This script will:
1. Read local client configurations from account_configs.json
2. Import monthly-specific goals from monthly_specific_goals.json
3. Import base revenue goals from sales_goals.json
4. Import historical performance data from performance_cache/
5. Create corresponding database entries in EmailPilot

Usage:
python migrate_local_data.py
"""

import json
import sqlite3
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

def setup_database():
    """Initialize the EmailPilot SQLite database with all tables"""
    conn = sqlite3.connect('emailpilot.db')
    cursor = conn.cursor()
    
    # Create clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            api_key_encrypted TEXT,
            metric_id VARCHAR(255),
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create goals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            revenue_goal DECIMAL(10,2) NOT NULL,
            calculation_method VARCHAR(50) DEFAULT 'manual',
            notes TEXT,
            confidence VARCHAR(20) DEFAULT 'medium',
            human_override BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            UNIQUE(client_id, year, month)
        )
    ''')
    
    # Create performance_history table for historical data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            revenue DECIMAL(12,2),
            orders INTEGER,
            email_sent INTEGER,
            email_opened INTEGER,
            email_clicked INTEGER,
            campaigns_sent INTEGER,
            active_flows INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            UNIQUE(client_id, year, month)
        )
    ''')
    
    # Create reports table (for tracking generated reports)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            report_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            generated_at DATETIME,
            file_path TEXT,
            summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    return conn

def load_local_data():
    """Load all local data files"""
    base_path = Path(__file__).parent.parent
    
    # Load client configurations
    account_configs_path = base_path / 'account_configs.json'
    with open(account_configs_path, 'r') as f:
        account_configs = json.load(f)
    
    # Load sales goals
    sales_goals_path = base_path / 'sales_goals.json'
    with open(sales_goals_path, 'r') as f:
        sales_goals = json.load(f)
    
    # Load monthly specific goals
    monthly_goals_path = base_path / 'monthly_specific_goals.json'
    with open(monthly_goals_path, 'r') as f:
        monthly_goals = json.load(f)
    
    return account_configs, sales_goals, monthly_goals, base_path

def encrypt_api_key(api_key):
    """Simple encryption for API keys (in production, use proper encryption)"""
    # For now, just base64 encode it. In production, use proper encryption.
    import base64
    return base64.b64encode(api_key.encode()).decode()

def migrate_clients(conn, account_configs):
    """Migrate client data to the database"""
    cursor = conn.cursor()
    migrated_clients = {}
    
    print("Migrating clients...")
    
    for config in account_configs:
        if not config.get('active', True):
            continue
            
        name = config['account_name']
        encrypted_key = encrypt_api_key(config['api_key'])
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO clients 
                (name, api_key_encrypted, metric_id, description, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                name,
                encrypted_key,
                config['metric_id'],
                config.get('description', ''),
                config.get('active', True),
                datetime.utcnow().isoformat()
            ))
            
            client_id = cursor.lastrowid
            if cursor.rowcount == 0:  # If it was a replacement, get the existing ID
                cursor.execute('SELECT id FROM clients WHERE name = ?', (name,))
                client_id = cursor.fetchone()[0]
                
            migrated_clients[name] = client_id
            print(f"  ✓ Migrated client: {name} (ID: {client_id})")
            
        except Exception as e:
            print(f"  ✗ Error migrating client {name}: {e}")
    
    conn.commit()
    return migrated_clients

def migrate_goals(conn, migrated_clients, sales_goals, monthly_goals):
    """Migrate goal data to the database"""
    cursor = conn.cursor()
    
    print("\nMigrating goals...")
    
    # First, migrate base monthly goals from sales_goals.json
    for client_name, goal_data in sales_goals['goals'].items():
        if client_name not in migrated_clients:
            continue
            
        client_id = migrated_clients[client_name]
        
        # Create base goals for current year if no specific monthly goals exist
        current_year = datetime.now().year
        base_goal = goal_data['monthly_revenue_goal']
        
        print(f"  Base monthly goal for {client_name}: ${base_goal:,.2f}")
    
    # Then migrate specific monthly goals
    goals_count = 0
    for goal_key, goal_data in monthly_goals['monthly_goals'].items():
        client_name = goal_data['client_name']
        
        if client_name not in migrated_clients:
            print(f"  ⚠ Skipping goal for unknown client: {client_name}")
            continue
            
        client_id = migrated_clients[client_name]
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO goals
                (client_id, year, month, revenue_goal, calculation_method, 
                 notes, confidence, human_override, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_id,
                goal_data['year'],
                goal_data['month'],
                goal_data['revenue_goal'],
                goal_data.get('calculation_method', 'manual'),
                goal_data.get('notes', ''),
                goal_data.get('confidence', 'medium'),
                goal_data.get('human_override', False),
                datetime.fromisoformat(goal_data['last_updated'].replace('Z', '+00:00')).isoformat()
            ))
            goals_count += 1
            
        except Exception as e:
            print(f"  ✗ Error migrating goal {goal_key}: {e}")
    
    conn.commit()
    print(f"  ✓ Migrated {goals_count} monthly goals")

def migrate_performance_history(conn, migrated_clients, base_path):
    """Migrate historical performance data from performance_cache/"""
    cursor = conn.cursor()
    performance_cache_path = base_path / 'performance_cache'
    
    if not performance_cache_path.exists():
        print("\n⚠ No performance_cache directory found")
        return
    
    print("\nMigrating performance history...")
    
    history_count = 0
    for json_file in performance_cache_path.glob('*.json'):
        if json_file.name == 'performance_history.db':
            continue
            
        # Parse filename: "Client Name_YYYY_MM.json"
        filename = json_file.stem
        if '_' not in filename:
            continue
            
        # Extract client name, year, and month from filename
        parts = filename.rsplit('_', 2)
        if len(parts) != 3:
            continue
            
        client_name, year_str, month_str = parts
        
        try:
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            continue
            
        if client_name not in migrated_clients:
            continue
            
        client_id = migrated_clients[client_name]
        
        try:
            with open(json_file, 'r') as f:
                perf_data = json.load(f)
            
            cursor.execute('''
                INSERT OR REPLACE INTO performance_history
                (client_id, year, month, revenue, orders, email_sent, 
                 email_opened, email_clicked, campaigns_sent, active_flows)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_id,
                year,
                month,
                perf_data.get('revenue'),
                perf_data.get('orders'),
                perf_data.get('email_sent'),
                perf_data.get('email_opened'),
                perf_data.get('email_clicked'),
                perf_data.get('campaigns_sent'),
                perf_data.get('active_flows')
            ))
            
            history_count += 1
            
        except Exception as e:
            print(f"  ✗ Error migrating {json_file.name}: {e}")
    
    conn.commit()
    print(f"  ✓ Migrated {history_count} performance history records")

def create_summary_reports(conn, migrated_clients):
    """Create summary report entries for migrated data"""
    cursor = conn.cursor()
    
    print("\nCreating summary reports...")
    
    for client_name, client_id in migrated_clients.items():
        try:
            cursor.execute('''
                INSERT INTO reports
                (client_id, report_type, status, summary, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                client_id,
                'migration',
                'completed',
                f'Data migration completed for {client_name}. Historical data and goals imported.',
                datetime.utcnow().isoformat()
            ))
        except Exception as e:
            print(f"  ✗ Error creating report for {client_name}: {e}")
    
    conn.commit()
    print(f"  ✓ Created migration reports for {len(migrated_clients)} clients")

def print_migration_summary(conn, migrated_clients):
    """Print a summary of migrated data"""
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    
    # Count clients
    cursor.execute('SELECT COUNT(*) FROM clients WHERE is_active = 1')
    active_clients = cursor.fetchone()[0]
    
    # Count goals
    cursor.execute('SELECT COUNT(*) FROM goals')
    total_goals = cursor.fetchone()[0]
    
    # Count performance records
    cursor.execute('SELECT COUNT(*) FROM performance_history')
    total_history = cursor.fetchone()[0]
    
    print(f"✓ Active Clients: {active_clients}")
    print(f"✓ Monthly Goals: {total_goals}")
    print(f"✓ Performance Records: {total_history}")
    
    print("\nClients by Revenue Goal (from latest goals):")
    cursor.execute('''
        SELECT c.name, AVG(g.revenue_goal) as avg_goal
        FROM clients c
        JOIN goals g ON c.id = g.client_id
        WHERE c.is_active = 1
        GROUP BY c.id, c.name
        ORDER BY avg_goal DESC
    ''')
    
    for name, avg_goal in cursor.fetchall():
        print(f"  • {name}: ${avg_goal:,.2f}/month")
    
    print("\nHistorical Performance (last 6 months average):")
    cursor.execute('''
        SELECT c.name, AVG(ph.revenue) as avg_revenue, COUNT(*) as months
        FROM clients c
        JOIN performance_history ph ON c.id = ph.client_id
        WHERE c.is_active = 1 
        AND ph.year >= 2024
        GROUP BY c.id, c.name
        ORDER BY avg_revenue DESC
    ''')
    
    for name, avg_revenue, months in cursor.fetchall():
        print(f"  • {name}: ${avg_revenue:,.2f}/month ({months} months data)")

def main():
    """Main migration function"""
    print("EmailPilot Data Migration Tool")
    print("="*50)
    
    try:
        # Setup database
        print("Setting up database...")
        conn = setup_database()
        
        # Load local data
        print("Loading local data files...")
        account_configs, sales_goals, monthly_goals, base_path = load_local_data()
        
        # Migrate clients
        migrated_clients = migrate_clients(conn, account_configs)
        
        if not migrated_clients:
            print("No clients migrated. Exiting.")
            return
        
        # Migrate goals
        migrate_goals(conn, migrated_clients, sales_goals, monthly_goals)
        
        # Migrate performance history
        migrate_performance_history(conn, migrated_clients, base_path)
        
        # Create summary reports
        create_summary_reports(conn, migrated_clients)
        
        # Print summary
        print_migration_summary(conn, migrated_clients)
        
        print(f"\n✅ Migration completed successfully!")
        print(f"📁 Database saved as: emailpilot.db")
        print(f"🚀 You can now deploy this database to your EmailPilot application")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()