#!/usr/bin/env python3
"""
Verify database migration
This script helps verify that the migration was successful by comparing record counts
between the source and target databases.
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text, inspect, MetaData, Table, select, func
from dotenv import load_dotenv
from tabulate import tabulate

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

def setup_source_connection(connection_string=None):
    """Set up connection to the source database"""
    print("Setting up connection to source database...")
    
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

def get_record_count(engine, table_name):
    """Get the number of records in a table"""
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    
    with engine.connect() as conn:
        query = select(func.count()).select_from(table)
        result = conn.execute(query)
        return result.scalar()

def verify_migration(source_engine, target_engine, tables_to_verify=None):
    """Verify the migration by comparing record counts"""
    print("\nVerifying migration...")
    
    # Get all table names from source database
    source_tables = get_table_names(source_engine)
    
    # Get all table names from target database
    target_tables = get_table_names(target_engine)
    
    # Determine which tables to verify
    tables_to_process = []
    
    # If specific tables are requested
    if tables_to_verify:
        for source_table in tables_to_verify:
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
    
    print(f"Tables to verify: {', '.join([f'{s} → {t}' for s, t in tables_to_process])}")
    
    # Verify each table
    results = []
    for source_table, target_table in tables_to_process:
        source_count = get_record_count(source_engine, source_table)
        target_count = get_record_count(target_engine, target_table)
        match = source_count == target_count
        
        results.append([
            f"{source_table} → {target_table}",
            source_count,
            target_count,
            "✅" if match else "❌"
        ])
    
    # Print results in a table
    headers = ["Table", "Source Count", "Target Count", "Match"]
    print("\n" + tabulate(results, headers=headers, tablefmt="grid"))
    
    # Calculate summary
    total_tables = len(results)
    if total_tables > 0:
        matched_tables = sum(1 for r in results if r[3] == "✅")
        print(f"\nSummary: {matched_tables} out of {total_tables} tables match ({matched_tables/total_tables*100:.1f}%)")
        return matched_tables == total_tables
    else:
        print("\nNo matching tables found to verify.")
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Verify database migration')
    parser.add_argument('--source', help='Source database connection string')
    parser.add_argument('--tables', help='Comma-separated list of tables to verify (default: all matching tables)')
    return parser.parse_args()

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration Verification Tool")
    print("=" * 50)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup connections
    source_engine = setup_source_connection(args.source)
    target_engine = setup_target_connection()
    
    # Parse tables to verify
    tables_to_verify = None
    if args.tables:
        tables_to_verify = [t.strip() for t in args.tables.split(',')]
    
    # Verify migration
    success = verify_migration(source_engine, target_engine, tables_to_verify)
    
    print("\n" + "=" * 50)
    if success:
        print("Verification PASSED: All tables have matching record counts.")
    else:
        print("Verification FAILED: Some tables have different record counts.")
    print("=" * 50)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 