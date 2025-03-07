"""
Script to directly add the office_id column to the churches table.
"""
import sqlite3
import os

def add_office_id_column():
    """Add office_id column to churches table."""
    print("Adding office_id column to churches table...")
    
    # Connect to the database
    conn = sqlite3.connect('mobilize_crm.db')
    cursor = conn.cursor()
    
    try:
        # Check if office_id column exists
        cursor.execute("PRAGMA table_info(churches)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'office_id' not in columns:
            print("office_id column does not exist, creating it...")
            
            # Create a backup of the churches table
            cursor.execute("CREATE TABLE churches_backup AS SELECT * FROM churches")
            conn.commit()
            
            # Create a new churches table with the office_id column
            cursor.execute("""
            CREATE TABLE churches_new (
                id INTEGER NOT NULL, 
                location VARCHAR, 
                main_contact_id INTEGER, 
                virtuous BOOLEAN, 
                senior_pastor_first_name VARCHAR(100), 
                senior_pastor_last_name VARCHAR(100), 
                senior_pastor_phone VARCHAR(50), 
                senior_pastor_email VARCHAR, 
                missions_pastor_first_name VARCHAR(100), 
                missions_pastor_last_name VARCHAR(100), 
                mission_pastor_phone VARCHAR(50), 
                mission_pastor_email VARCHAR, 
                primary_contact_first_name VARCHAR(100), 
                primary_contact_last_name VARCHAR(100), 
                primary_contact_phone VARCHAR(50), 
                primary_contact_email VARCHAR, 
                website VARCHAR, 
                denomination VARCHAR(100), 
                congregation_size INTEGER, 
                church_pipeline VARCHAR(100), 
                priority VARCHAR(100), 
                assigned_to VARCHAR(100), 
                source VARCHAR(100), 
                referred_by VARCHAR(100), 
                info_given TEXT, 
                reason_closed TEXT, 
                year_founded INTEGER, 
                date_closed DATE,
                office_id INTEGER,
                PRIMARY KEY (id), 
                FOREIGN KEY(id) REFERENCES contacts (id) ON DELETE CASCADE, 
                FOREIGN KEY(main_contact_id) REFERENCES people (id),
                FOREIGN KEY(office_id) REFERENCES offices (id)
            )
            """)
            
            # Copy data from the backup table to the new table
            cursor.execute("""
            INSERT INTO churches_new (
                id, location, main_contact_id, virtuous, 
                senior_pastor_first_name, senior_pastor_last_name, 
                senior_pastor_phone, senior_pastor_email, 
                missions_pastor_first_name, missions_pastor_last_name, 
                mission_pastor_phone, mission_pastor_email, 
                primary_contact_first_name, primary_contact_last_name, 
                primary_contact_phone, primary_contact_email, 
                website, denomination, congregation_size, 
                church_pipeline, priority, assigned_to, 
                source, referred_by, info_given, 
                reason_closed, year_founded, date_closed
            )
            SELECT 
                id, location, main_contact_id, virtuous, 
                senior_pastor_first_name, senior_pastor_last_name, 
                senior_pastor_phone, senior_pastor_email, 
                missions_pastor_first_name, missions_pastor_last_name, 
                mission_pastor_phone, mission_pastor_email, 
                primary_contact_first_name, primary_contact_last_name, 
                primary_contact_phone, primary_contact_email, 
                website, denomination, congregation_size, 
                church_pipeline, priority, assigned_to, 
                source, referred_by, info_given, 
                reason_closed, year_founded, date_closed
            FROM churches_backup
            """)
            
            # Drop the old table
            cursor.execute("DROP TABLE churches")
            
            # Rename the new table to the old table name
            cursor.execute("ALTER TABLE churches_new RENAME TO churches")
            
            # Set office_id to 1 (default office) for all churches
            cursor.execute("UPDATE churches SET office_id = 1")
            
            # Drop the backup table
            cursor.execute("DROP TABLE churches_backup")
            
            conn.commit()
            print("Successfully added office_id column to churches table")
        else:
            print("office_id column already exists")
    
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_office_id_column() 