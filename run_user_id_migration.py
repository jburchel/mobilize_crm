import sqlite3
import os
import sys
from update_db_schema import update_schema

def assign_default_user_to_existing_records():
    """
    Assign a default user ID to existing Person records.
    This is a one-time migration to ensure existing records have a user_id.
    """
    try:
        # First ensure the user_id column exists
        update_schema()
        
        # Connect to the database
        conn = sqlite3.connect('mobilize_crm.db')
        cursor = conn.cursor()
        
        # Get a list of admin users from Firebase (in a real implementation)
        # For now, we'll use a default admin user ID
        default_admin_user_id = "admin_user_123"  # Replace with a real admin user ID
        
        # Update all Person records that don't have a user_id
        print("Assigning default user ID to existing Person records...")
        cursor.execute("""
            UPDATE people 
            SET user_id = ? 
            WHERE user_id IS NULL OR user_id = ''
        """, (default_admin_user_id,))
        
        # Commit the changes
        conn.commit()
        
        # Get count of updated records
        updated_count = cursor.rowcount
        print(f"Updated {updated_count} Person records with default user ID.")
        
        conn.close()
        print("Migration completed successfully.")
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    assign_default_user_to_existing_records() 