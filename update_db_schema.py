"""
Database schema update script for Gmail integration
This script adds the new Gmail integration fields to the Communications table
"""
import sqlite3
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_communications_table():
    """Add Gmail integration fields to the Communications table"""
    try:
        # Connect to the database
        conn = sqlite3.connect('mobilize_crm.db')
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(communications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add gmail_message_id column if it doesn't exist
        if 'gmail_message_id' not in columns:
            logger.info("Adding gmail_message_id column to communications table")
            cursor.execute("ALTER TABLE communications ADD COLUMN gmail_message_id TEXT")
        
        # Add gmail_thread_id column if it doesn't exist
        if 'gmail_thread_id' not in columns:
            logger.info("Adding gmail_thread_id column to communications table")
            cursor.execute("ALTER TABLE communications ADD COLUMN gmail_thread_id TEXT")
        
        # Add email_status column if it doesn't exist
        if 'email_status' not in columns:
            logger.info("Adding email_status column to communications table")
            cursor.execute("ALTER TABLE communications ADD COLUMN email_status TEXT")
        
        # Add subject column if it doesn't exist
        if 'subject' not in columns:
            logger.info("Adding subject column to communications table")
            cursor.execute("ALTER TABLE communications ADD COLUMN subject TEXT")
        
        # Add attachments column if it doesn't exist
        if 'attachments' not in columns:
            logger.info("Adding attachments column to communications table")
            cursor.execute("ALTER TABLE communications ADD COLUMN attachments TEXT")
        
        # Add last_synced_at column if it doesn't exist
        if 'last_synced_at' not in columns:
            logger.info("Adding last_synced_at column to communications table")
            cursor.execute("ALTER TABLE communications ADD COLUMN last_synced_at TIMESTAMP")
        
        # Commit changes
        conn.commit()
        logger.info("Database schema updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
    finally:
        conn.close()

def update_schema():
    """Update the database schema to add new fields."""
    try:
        # Connect to the database
        conn = sqlite3.connect('mobilize_crm.db')
        cursor = conn.cursor()
        
        # Check if user_id column exists in people table
        cursor.execute("PRAGMA table_info(people)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Add user_id column if it doesn't exist
        if 'user_id' not in column_names:
            print("Adding user_id column to people table...")
            cursor.execute("ALTER TABLE people ADD COLUMN user_id TEXT")
            conn.commit()
            print("Added user_id column to people table.")
        else:
            print("user_id column already exists in people table.")
        
        # ... existing code ...
        
        conn.close()
        print("Database schema update completed successfully.")
        return True
    except Exception as e:
        print(f"Error updating database schema: {e}")
        return False

if __name__ == "__main__":
    update_communications_table()
    update_schema() 