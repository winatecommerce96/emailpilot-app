#!/usr/bin/env python3
"""
Fix database schema - add missing seasonal_multiplier column to goals table
"""

import sqlite3
import os
from pathlib import Path

def fix_database_schema():
    """Add missing seasonal_multiplier column to goals table"""
    
    # Find the database file
    db_path = Path(__file__).parent / "emailpilot.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if seasonal_multiplier column exists
        cursor.execute("PRAGMA table_info(goals)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'seasonal_multiplier' not in column_names:
            print("Adding seasonal_multiplier column to goals table...")
            cursor.execute("ALTER TABLE goals ADD COLUMN seasonal_multiplier REAL")
            conn.commit()
            print("✅ Column added successfully!")
        else:
            print("✅ seasonal_multiplier column already exists")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(goals)")
        columns = cursor.fetchall()
        print(f"\nGoals table columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        print("\n🎉 Database schema is now up to date!")
        
    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")

if __name__ == "__main__":
    fix_database_schema()