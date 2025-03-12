import os
import sqlite3
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

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

# Check if users table already exists in SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if sqlite_cursor.fetchone():
    print("⚠️ Users table already exists in SQLite. Skipping creation.")
else:
    # Create users table in SQLite
    try:
        sqlite_cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            firebase_uid VARCHAR(128) UNIQUE,
            email VARCHAR(120) UNIQUE,
            created_at TIMESTAMP
        )
        ''')
        sqlite_conn.commit()
        print("✅ Users table created successfully in SQLite")
    except Exception as e:
        print(f"❌ Failed to create users table in SQLite: {e}")

# Close SQLite connection
sqlite_conn.close()
print("✅ SQLite connection closed") 