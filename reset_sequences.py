#!/usr/bin/env python3
"""
Reset PostgreSQL sequences after data migration
This script helps reset the sequences for auto-incrementing IDs after data migration.
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text, inspect, MetaData, Table
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_connection(connection_string=None):
    """Set up connection to the database"""
    print("Setting up connection to database...")
    
    if connection_string:
        db_uri = connection_string
    else:
        # Check if we have a direct connection string
        db_uri = os.environ.get('DB_CONNECTION_STRING')
        if not db_uri:
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
            
            db_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            if 'supabase' in host:
                db_uri += "?sslmode=require"
    
    # Print connection info (without password)
    safe_uri = db_uri
    if ':' in db_uri and '@' in db_uri:
        parts = db_uri.split('@')
        user_pass_part = parts[0].split(':')
        if len(user_pass_part) > 2:  # If there's a password
            safe_uri = db_uri.replace(user_pass_part[2], '********')
    
    print(f"Database URI: {safe_uri}")
    
    # Create engine for database
    try:
        connect_args = {}
        if 'sslmode=require' in db_uri:
            connect_args = {"sslmode": "require"}
        
        engine = create_engine(db_uri, connect_args=connect_args)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Database connection successful!")
        return engine
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def get_tables_with_id_column(engine):
    """Get all tables that have an 'id' column"""
    inspector = inspect(engine)
    tables = []
    
    for table_name in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        if 'id' in columns:
            tables.append(table_name)
    
    return tables

def reset_sequence(engine, table_name):
    """Reset the sequence for a table"""
    sequence_name = f"{table_name}_id_seq"
    
    try:
        # Use a fresh connection for each sequence reset to avoid transaction issues
        with engine.connect() as conn:
            # Check if sequence exists
            result = conn.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM pg_sequences WHERE sequencename = '{sequence_name}')"
            ))
            sequence_exists = result.scalar()
            
            if not sequence_exists:
                print(f"Sequence {sequence_name} does not exist, skipping...")
                return False
            
            # Get the maximum ID from the table
            result = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}"))
            next_id = result.scalar()
            
            # Reset the sequence in a new transaction
            conn.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART WITH {next_id}"))
            
            print(f"Reset sequence {sequence_name} to {next_id}")
            return True
    except Exception as e:
        print(f"Error resetting sequence for {table_name}: {str(e)}")
        return False

def reset_all_sequences(engine, tables=None):
    """Reset all sequences in the database"""
    print("\nResetting sequences...")
    
    # Get all tables with ID column if not specified
    if not tables:
        tables = get_tables_with_id_column(engine)
    
    print(f"Tables to process: {', '.join(tables)}")
    
    # Reset sequence for each table
    success_count = 0
    for table_name in tables:
        if reset_sequence(engine, table_name):
            success_count += 1
    
    print(f"\nSuccessfully reset {success_count} out of {len(tables)} sequences.")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Reset PostgreSQL sequences after data migration')
    parser.add_argument('--connection', help='Database connection string')
    parser.add_argument('--tables', help='Comma-separated list of tables to process (default: all tables with id column)')
    return parser.parse_args()

if __name__ == "__main__":
    print("=" * 50)
    print("PostgreSQL Sequence Reset Tool")
    print("=" * 50)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup connection
    engine = setup_connection(args.connection)
    
    # Parse tables to process
    tables_to_process = None
    if args.tables:
        tables_to_process = [t.strip() for t in args.tables.split(',')]
    
    # Reset sequences
    reset_all_sequences(engine, tables_to_process)
    
    print("\n" + "=" * 50)
    print("Sequence reset completed.")
    print("=" * 50) 