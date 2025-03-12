import os
import sqlite3
from dotenv import load_dotenv

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
    backup_path = f"{sqlite_db_path}.id_fix.backup"
    shutil.copy2(sqlite_db_path, backup_path)
    print(f"✅ Created backup of database at {backup_path}")
except Exception as e:
    print(f"❌ Failed to create backup: {e}")
    exit(1)

# Check the user_id in user_offices
sqlite_cursor.execute("SELECT user_id FROM user_offices LIMIT 1")
user_offices_id = sqlite_cursor.fetchone()[0]
print(f"✅ User ID in user_offices: {user_offices_id}")

# Check the user_id in people
sqlite_cursor.execute("SELECT DISTINCT user_id FROM people LIMIT 1")
people_id = sqlite_cursor.fetchone()[0]
print(f"✅ User ID in people: {people_id}")

# Fix the mismatch
if user_offices_id != people_id:
    print(f"⚠️ User ID mismatch detected. Fixing...")
    
    # Option 1: Update user_offices to match people
    try:
        sqlite_cursor.execute("UPDATE user_offices SET user_id = ?", (people_id,))
        print(f"✅ Updated user_offices with user_id: {people_id}")
    except Exception as e:
        print(f"❌ Failed to update user_offices: {e}")
        
        # Option 2: If option 1 fails, update people to match user_offices
        try:
            sqlite_cursor.execute("UPDATE people SET user_id = ?", (user_offices_id,))
            print(f"✅ Updated people with user_id: {user_offices_id}")
        except Exception as e:
            print(f"❌ Failed to update people: {e}")
else:
    print("✅ User IDs match. No fix needed.")

# Commit changes
sqlite_conn.commit()
print("✅ Committed changes to database")

# Close connection
sqlite_conn.close()
print("✅ Closed database connection")

print("\n✅ User ID mismatch fix complete. Please restart the application and check if people and churches are now displayed.") 