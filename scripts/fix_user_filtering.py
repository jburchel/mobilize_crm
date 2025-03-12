import os
import sys
import sqlite3
from dotenv import load_dotenv

# Add parent directory to path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# SQLite database path
sqlite_db_path = 'mobilize_crm.db'

# Connect to SQLite database
try:
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_cursor = sqlite_conn.cursor()
    print(f"✅ Connected to SQLite database at {sqlite_db_path}")
except Exception as e:
    print(f"❌ Failed to connect to SQLite database: {e}")
    exit(1)

# Create a backup of the database
try:
    import shutil
    backup_path = f"{sqlite_db_path}.user_fix.backup"
    shutil.copy2(sqlite_db_path, backup_path)
    print(f"✅ Created backup of database at {backup_path}")
except Exception as e:
    print(f"❌ Failed to create backup: {e}")
    exit(1)

# Check if there's a user_id in the user_offices table
sqlite_cursor.execute("SELECT user_id FROM user_offices LIMIT 1")
user_id_result = sqlite_cursor.fetchone()

if user_id_result:
    user_id = user_id_result[0]
    print(f"✅ Found user_id in user_offices: {user_id}")
    
    # Update all people records to have this user_id
    try:
        sqlite_cursor.execute(f"UPDATE people SET user_id = ?", (user_id,))
        print(f"✅ Updated {sqlite_cursor.rowcount} people records with user_id: {user_id}")
    except Exception as e:
        print(f"❌ Failed to update people records: {e}")
    
    # Check if there are any churches with NULL office_id
    sqlite_cursor.execute("SELECT COUNT(*) FROM churches WHERE office_id IS NULL")
    null_office_count = sqlite_cursor.fetchone()[0]
    
    if null_office_count > 0:
        # Get the office_id from user_offices
        sqlite_cursor.execute("SELECT office_id FROM user_offices LIMIT 1")
        office_id_result = sqlite_cursor.fetchone()
        
        if office_id_result:
            office_id = office_id_result[0]
            print(f"✅ Found office_id in user_offices: {office_id}")
            
            # Update churches with NULL office_id
            try:
                sqlite_cursor.execute(f"UPDATE churches SET office_id = ? WHERE office_id IS NULL", (office_id,))
                print(f"✅ Updated {sqlite_cursor.rowcount} churches records with office_id: {office_id}")
            except Exception as e:
                print(f"❌ Failed to update churches records: {e}")
        else:
            print("❌ No office_id found in user_offices")
    else:
        print("✅ All churches have an office_id")
else:
    print("❌ No user_id found in user_offices")

# Commit changes
sqlite_conn.commit()
print("✅ Committed changes to database")

# Close connection
sqlite_conn.close()
print("✅ Closed database connection")

print("\n✅ User filtering fix complete. Please restart the application and check if people and churches are now displayed.") 