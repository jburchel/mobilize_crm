"""
Script to add Google Calendar fields to the Task model
"""
import sqlite3
import os
import sys
from datetime import datetime

def add_google_calendar_fields():
    print("Adding Google Calendar fields to tasks table...")
    
    # Path to the database
    db_path = 'mobilize_crm.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        return False
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Add columns if they don't exist
        if 'google_calendar_event_id' not in column_names:
            cursor.execute("ALTER TABLE tasks ADD COLUMN google_calendar_event_id TEXT")
            print("Added google_calendar_event_id column")
        
        if 'google_calendar_sync_enabled' not in column_names:
            cursor.execute("ALTER TABLE tasks ADD COLUMN google_calendar_sync_enabled BOOLEAN DEFAULT 0")
            print("Added google_calendar_sync_enabled column")
        
        if 'last_synced_at' not in column_names:
            cursor.execute("ALTER TABLE tasks ADD COLUMN last_synced_at TIMESTAMP")
            print("Added last_synced_at column")
        
        # We can't add a unique index in SQLite ALTER TABLE, so we need to check if it exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_tasks_google_calendar_event_id'")
        if not cursor.fetchone():
            cursor.execute("CREATE UNIQUE INDEX ix_tasks_google_calendar_event_id ON tasks (google_calendar_event_id)")
            print("Created unique index on google_calendar_event_id")
        
        conn.commit()
        print("Migration completed successfully!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error applying migration: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = add_google_calendar_fields()
    if success:
        print("Google Calendar fields have been added to the tasks table")
    else:
        print("Failed to apply migration")
        sys.exit(1)