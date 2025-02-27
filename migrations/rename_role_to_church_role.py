import sqlite3
import os

def run_migration():
    """
    Rename the 'role' column to 'church_role' in the people table
    """
    # Get the database path
    db_path = 'mobilize_crm.db'
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        conn.execute('BEGIN TRANSACTION')
        
        # Create a new table with the updated schema
        cursor.execute('''
        CREATE TABLE people_new (
            id INTEGER PRIMARY KEY,
            church_role TEXT,
            church_id INTEGER,
            spouse_first_name TEXT,
            spouse_last_name TEXT,
            virtuous BOOLEAN,
            title TEXT,
            home_country TEXT,
            marital_status TEXT,
            people_pipeline TEXT,
            priority TEXT,
            assigned_to TEXT,
            source TEXT,
            referred_by TEXT,
            info_given TEXT,
            desired_service TEXT,
            reason_closed TEXT,
            date_closed DATE,
            FOREIGN KEY (id) REFERENCES contacts(id) ON DELETE CASCADE,
            FOREIGN KEY (church_id) REFERENCES churches(id)
        )
        ''')
        
        # Copy data from the old table to the new table, renaming the column
        cursor.execute('''
        INSERT INTO people_new (
            id, church_role, church_id, spouse_first_name, spouse_last_name, 
            virtuous, title, home_country, marital_status, people_pipeline, 
            priority, assigned_to, source, referred_by, info_given, 
            desired_service, reason_closed, date_closed
        )
        SELECT 
            id, role, church_id, spouse_first_name, spouse_last_name, 
            virtuous, title, home_country, marital_status, people_pipeline, 
            priority, assigned_to, source, referred_by, info_given, 
            desired_service, reason_closed, date_closed
        FROM people
        ''')
        
        # Drop the old table
        cursor.execute('DROP TABLE people')
        
        # Rename the new table to the original name
        cursor.execute('ALTER TABLE people_new RENAME TO people')
        
        # Commit the transaction
        conn.commit()
        print("Migration successful: Renamed 'role' column to 'church_role' in people table")
        
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        print(f"Migration failed: {str(e)}")
        raise
    finally:
        # Close the connection
        conn.close()

if __name__ == "__main__":
    run_migration() 