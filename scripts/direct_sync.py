#!/usr/bin/env python3

import os
import sqlite3
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_pg_connection():
    """Get a connection to the PostgreSQL database"""
    pg_connection_string = os.environ.get('DB_CONNECTION_STRING')
    if not pg_connection_string:
        print("❌ PostgreSQL connection string not found in environment variables")
        return None
    
    try:
        conn = psycopg2.connect(pg_connection_string)
        print("✅ Connected to PostgreSQL database")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL database: {str(e)}")
        return None

def get_sqlite_connection():
    """Get a connection to the SQLite database"""
    try:
        conn = sqlite3.connect('mobilize_crm.db')
        print("✅ Connected to SQLite database")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to SQLite database: {str(e)}")
        return None

def sync_table(pg_conn, sqlite_conn, table_name):
    """Sync a table from PostgreSQL to SQLite"""
    print(f"\n=== Syncing {table_name} from PostgreSQL to SQLite ===\n")
    
    try:
        # Get data from PostgreSQL
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute(f"SELECT * FROM {table_name}")
        rows = pg_cursor.fetchall()
        
        if not rows:
            print(f"❌ No data found in PostgreSQL {table_name}")
            return False
        
        print(f"✅ Retrieved {len(rows)} records from PostgreSQL {table_name}")
        
        # Get column names from PostgreSQL
        pg_cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position")
        columns = [col[0] for col in pg_cursor.fetchall()]
        
        print(f"✅ Retrieved {len(columns)} columns for {table_name}: {columns}")
        
        # Clear existing data in SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"DELETE FROM {table_name}")
        
        # Insert data into SQLite
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        
        for row in rows:
            # Convert any None values to NULL
            row_values = []
            for value in row:
                if value is None:
                    row_values.append(None)
                else:
                    row_values.append(str(value))
            
            # Insert the row
            sqlite_cursor.execute(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})", row_values)
        
        # Commit the changes
        sqlite_conn.commit()
        
        # Get the count of rows in SQLite
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = sqlite_cursor.fetchone()[0]
        
        print(f"✅ Inserted {count} records into SQLite {table_name}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error syncing {table_name}: {str(e)}")
        return False

def main():
    """Main function"""
    print("\n=== Direct PostgreSQL to SQLite Sync Tool ===\n")
    
    # Get connections
    pg_conn = get_pg_connection()
    sqlite_conn = get_sqlite_connection()
    
    if not pg_conn or not sqlite_conn:
        print("❌ Failed to connect to databases. Exiting.")
        return
    
    # Tables to sync
    tables = ['people', 'churches', 'contacts', 'communications', 'tasks', 'offices', 'user_offices', 'users', 'email_signatures', 'user_tokens', 'permissions']
    
    # Sync each table
    success = True
    for table in tables:
        table_success = sync_table(pg_conn, sqlite_conn, table)
        success = success and table_success
    
    # Close connections
    pg_conn.close()
    sqlite_conn.close()
    
    # Print summary
    print("\n=== Sync Summary ===\n")
    print(f"Tables synced: {', '.join(tables)}")
    print(f"Overall Status: {'✅ SUCCESS' if success else '❌ FAILED'}")

if __name__ == "__main__":
    main() 