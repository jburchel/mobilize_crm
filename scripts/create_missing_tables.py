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

# Tables to create
tables_to_create = {
    'email_signatures': '''
        CREATE TABLE email_signatures (
            id INTEGER PRIMARY KEY,
            user_id VARCHAR,
            name VARCHAR,
            content TEXT,
            logo_url VARCHAR,
            is_default BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''',
    'user_tokens': '''
        CREATE TABLE user_tokens (
            id INTEGER PRIMARY KEY,
            user_id VARCHAR(128),
            token_data TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''',
    'permissions': '''
        CREATE TABLE permissions (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100),
            description TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    '''
}

# Check if tables exist and create if they don't
for table_name, create_sql in tables_to_create.items():
    sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    if sqlite_cursor.fetchone():
        print(f"⚠️ {table_name} table already exists in SQLite. Skipping creation.")
    else:
        try:
            sqlite_cursor.execute(create_sql)
            sqlite_conn.commit()
            print(f"✅ {table_name} table created successfully in SQLite")
        except Exception as e:
            print(f"❌ Failed to create {table_name} table in SQLite: {e}")

# Close SQLite connection
sqlite_conn.close()
print("✅ SQLite connection closed") 