#!/usr/bin/env python3
"""
Database migration script from Render PostgreSQL to new database
This script helps migrate your data from Render PostgreSQL to your new database.
"""

import os
import sys
import time
import argparse
from sqlalchemy import create_engine, inspect, MetaData, Table, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define table name mapping from source to target
TABLE_MAPPING = {
    'contacts_contact': 'contacts',
    'contacts_church': 'churches',
    'task_tracker_task': 'tasks',
    'com_log_comlog': 'communications',
    'contacts_people': 'people',
    # Add more mappings as needed
}

# Define column mapping for tables where column names differ
# Format: {source_table: {source_column: target_column}}
COLUMN_MAPPING = {
    'contacts_church': {
        'contact_ptr_id': 'id',  # Map contact_ptr_id to id
        # Add other column mappings as needed
    },
    'contacts_contact': {
        'id': 'id',  # Explicitly map ID columns
        # Add other column mappings as needed
    },
    'task_tracker_task': {
        'id': 'id',  # Explicitly map ID columns
        # Add other column mappings as needed
    },
    'com_log_comlog': {
        'id': 'id',  # Explicitly map ID columns
        # Add other column mappings as needed
    },
    'contacts_people': {
        'contact_ptr_id': 'id',  # Map contact_ptr_id to id
        'affiliated_church_id': 'church_id',  # Map affiliated_church_id to church_id
        # Add other column mappings as needed
    },
}

def setup_source_connection(connection_string=None):
    """Set up connection to the source Render PostgreSQL database"""
    print("Setting up connection to source Render PostgreSQL database...")
    
    if connection_string:
        source_uri = connection_string
    else:
        # Check for required environment variables
        source_uri = os.environ.get('SOURCE_DB_CONNECTION_STRING')
        if not source_uri:
            # Try to build from individual variables
            required_vars = ['SOURCE_DB_PASS', 'SOURCE_DB_HOST']
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            
            if missing_vars:
                print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
                print("Please set either SOURCE_DB_CONNECTION_STRING or the individual variables")
                sys.exit(1)
            
            # Get connection details
            user = os.environ.get('SOURCE_DB_USER', 'postgres')
            password = os.environ.get('SOURCE_DB_PASS', '')
            dbname = os.environ.get('SOURCE_DB_NAME', 'postgres')
            host = os.environ.get('SOURCE_DB_HOST', '')
            port = os.environ.get('SOURCE_DB_PORT', '5432')
            
            source_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    # Print connection info (without password)
    safe_uri = source_uri
    if ':' in source_uri and '@' in source_uri:
        parts = source_uri.split('@')
        user_pass_part = parts[0].split(':')
        if len(user_pass_part) > 2:  # If there's a password
            safe_uri = source_uri.replace(user_pass_part[2], '********')
    
    print(f"Source Database URI: {safe_uri}")
    
    # Create engine for source database
    try:
        source_engine = create_engine(source_uri)
        with source_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Source database connection successful!")
        return source_engine
    except Exception as e:
        print(f"Error connecting to source database: {str(e)}")
        sys.exit(1)

def setup_target_connection():
    """Set up connection to the target database"""
    print("Setting up connection to target database...")
    
    # Check if we have a direct connection string
    target_uri = os.environ.get('DB_CONNECTION_STRING')
    if not target_uri:
        # Try to build from individual variables
        required_vars = ['DB_PASS', 'DB_HOST']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
            print("Please set either DB_CONNECTION_STRING or the individual variables")
            sys.exit(1)
        
        # Get connection details
        user = os.environ.get('DB_USER', 'postgres')
        password = os.environ.get('DB_PASS', '')
        dbname = os.environ.get('DB_NAME', 'postgres')
        host = os.environ.get('DB_HOST', '')
        port = os.environ.get('DB_PORT', '5432')
        
        target_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        if 'supabase' in host:
            target_uri += "?sslmode=require"
    
    # Print connection info (without password)
    safe_uri = target_uri
    if ':' in target_uri and '@' in target_uri:
        parts = target_uri.split('@')
        user_pass_part = parts[0].split(':')
        if len(user_pass_part) > 2:  # If there's a password
            safe_uri = target_uri.replace(user_pass_part[2], '********')
    
    print(f"Target Database URI: {safe_uri}")
    
    # Create engine for target database
    try:
        connect_args = {}
        if 'sslmode=require' in target_uri:
            connect_args = {"sslmode": "require"}
        
        target_engine = create_engine(target_uri, connect_args=connect_args)
        with target_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Target database connection successful!")
        return target_engine
    except Exception as e:
        print(f"Error connecting to target database: {str(e)}")
        sys.exit(1)

def get_table_names(engine):
    """Get all table names from the database"""
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_table_data(engine, table_name):
    """Get all data from a table"""
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    
    with engine.connect() as conn:
        query = select(table)
        result = conn.execute(query)
        return result.fetchall(), [col.name for col in table.columns]

def get_target_columns(engine, table_name):
    """Get column names for the target table"""
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    return [col.name for col in table.columns]

def get_target_table_structure(engine, table_name):
    """Get detailed structure of the target table"""
    inspector = inspect(engine)
    return inspector.get_columns(table_name)

def map_data_to_target(source_data, source_columns, target_columns, source_table, target_table_structure):
    """Map data from source columns to target columns"""
    # Get column mapping for this table
    column_map = COLUMN_MAPPING.get(source_table, {})
    
    # Create a list of dictionaries for each row
    mapped_rows = []
    
    # Find the ID column in the target table structure
    id_column = next((col for col in target_table_structure if col['name'] == 'id'), None)
    
    # Find the source ID column based on mapping
    source_id_column = None
    for source_col, target_col in column_map.items():
        if target_col == 'id':
            source_id_column = source_col
            break
    
    # If no explicit mapping for ID, use 'id' as the source column
    if not source_id_column:
        source_id_column = 'id'
    
    # Get the index of the source ID column
    source_id_index = None
    for i, col in enumerate(source_columns):
        if col == source_id_column:
            source_id_index = i
            break
    
    # Generate a counter for new IDs if needed
    next_id = 1
    
    for row_num, row in enumerate(source_data):
        row_dict = {}
        
        # Handle ID column specially
        if source_id_index is not None and row[source_id_index] is not None:
            # Use the ID from the source data
            row_dict['id'] = row[source_id_index]
        elif id_column is not None and not id_column.get('nullable', False):
            # Generate a new ID if the target requires a non-null ID
            row_dict['id'] = row_num + 1
            print(f"Generated ID {row_dict['id']} for row in {source_table}")
        
        # Map the rest of the columns
        for i, col in enumerate(source_columns):
            if col == source_id_column:
                continue  # Already handled above
                
            # Map the column name if it exists in the mapping
            target_col = column_map.get(col)
            
            # If no mapping exists, use the original column name
            if not target_col:
                target_col = col
            
            # Only include the column if it exists in the target table
            if target_col in target_columns:
                row_dict[target_col] = row[i]
        
        mapped_rows.append(row_dict)
    
    return mapped_rows

def insert_table_data(engine, table_name, data, columns, source_table):
    """Insert data into a table"""
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    
    # Get target table columns and structure
    target_columns = get_target_columns(engine, table_name)
    target_table_structure = get_target_table_structure(engine, table_name)
    
    # Map data to target columns
    mapped_data = map_data_to_target(data, columns, target_columns, source_table, target_table_structure)
    
    # Clear existing data if requested - this should be in its own transaction
    if args.clear_target_tables:
        with engine.connect() as conn:
            with conn.begin():
                try:
                    conn.execute(text(f"DELETE FROM {table_name}"))
                    print(f"Cleared existing data from {table_name}")
                except Exception as e:
                    print(f"Error clearing data from {table_name}: {str(e)}")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
                    return
    
    # Insert data
    if mapped_data:
        # Insert data in batches to avoid memory issues
        batch_size = 100
        success_count = 0
        error_count = 0
        
        for i in range(0, len(mapped_data), batch_size):
            batch = mapped_data[i:i+batch_size]
            if batch:
                # Process each row in its own transaction
                for row in batch:
                    with engine.connect() as conn:
                        try:
                            # Begin a transaction for this row
                            with conn.begin():
                                # Build column and value lists
                                columns_str = ', '.join(row.keys())
                                placeholders = ', '.join([f":{col}" for col in row.keys()])
                                
                                # Execute insert
                                insert_stmt = text(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})")
                                conn.execute(insert_stmt, row)
                                success_count += 1
                        except IntegrityError as e:
                            error_count += 1
                            if args.verbose:
                                print(f"Error inserting row with ID {row.get('id')}: {str(e)}")
                        except Exception as e:
                            error_count += 1
                            if args.verbose:
                                print(f"Unexpected error inserting row with ID {row.get('id')}: {str(e)}")
                                import traceback
                                traceback.print_exc()
        
        print(f"Inserted {success_count} rows into {table_name}")
        if error_count > 0:
            print(f"Failed to insert {error_count} rows due to errors")
    else:
        print(f"No data to insert for {table_name}")

def migrate_data(source_engine, target_engine, tables_to_migrate=None):
    """Migrate data from source to target database"""
    print("\nStarting data migration...")
    
    # Get all table names from source database
    source_tables = get_table_names(source_engine)
    print(f"Source database tables: {', '.join(source_tables)}")
    
    # Get all table names from target database
    target_tables = get_table_names(target_engine)
    print(f"Target database tables: {', '.join(target_tables)}")
    
    # Determine which tables to migrate
    tables_to_process = []
    
    # If specific tables are requested
    if tables_to_migrate:
        for source_table in tables_to_migrate:
            # Check if it's in the mapping
            target_table = TABLE_MAPPING.get(source_table)
            if target_table and target_table in target_tables:
                tables_to_process.append((source_table, target_table))
            # Check if it's a direct match
            elif source_table in target_tables:
                tables_to_process.append((source_table, source_table))
    else:
        # Process all tables based on mapping
        for source_table in source_tables:
            # Check if it's in the mapping
            target_table = TABLE_MAPPING.get(source_table)
            if target_table and target_table in target_tables:
                tables_to_process.append((source_table, target_table))
    
    print(f"\nTables to migrate: {', '.join([f'{s} → {t}' for s, t in tables_to_process])}")
    
    # Migrate each table
    for source_table, target_table in tables_to_process:
        print(f"\nMigrating table: {source_table} → {target_table}")
        
        # Get data from source table
        data, columns = get_table_data(source_engine, source_table)
        print(f"Retrieved {len(data)} rows from {source_table}")
        
        # Insert data into target table
        insert_table_data(target_engine, target_table, data, columns, source_table)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Migrate data from Render PostgreSQL to new database')
    parser.add_argument('--source', help='Source database connection string')
    parser.add_argument('--tables', help='Comma-separated list of tables to migrate (default: all matching tables)')
    parser.add_argument('--clear-target-tables', action='store_true', help='Clear target tables before inserting data')
    parser.add_argument('--verbose', action='store_true', help='Show detailed error messages')
    return parser.parse_args()

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration Tool: Render PostgreSQL to New Database")
    print("=" * 50)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup connections
    source_engine = setup_source_connection(args.source)
    target_engine = setup_target_connection()
    
    # Confirm before proceeding
    print("\nWarning: This will migrate data from your Render PostgreSQL database to your new database.")
    if args.clear_target_tables:
        print("WARNING: This will DELETE ALL EXISTING DATA in the target tables before migration!")
    
    confirm = input("Do you want to proceed? (y/n): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Parse tables to migrate
    tables_to_migrate = None
    if args.tables:
        tables_to_migrate = [t.strip() for t in args.tables.split(',')]
    
    # Migrate data
    start_time = time.time()
    migrate_data(source_engine, target_engine, tables_to_migrate)
    end_time = time.time()
    
    print("\n" + "=" * 50)
    print(f"Migration completed in {end_time - start_time:.2f} seconds.")
    print("=" * 50) 