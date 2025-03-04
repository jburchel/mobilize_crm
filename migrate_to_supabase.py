#!/usr/bin/env python3
"""
Database migration script for Supabase
This script helps migrate your local SQLite database to Supabase PostgreSQL.
"""

import os
import sys
import time
import subprocess
from sqlalchemy import create_engine, text
from app import app
from config import ProductionConfig

def setup_production_config():
    """Set up the production configuration for migration"""
    print("Setting up production configuration...")
    
    print("IMPORTANT: For Supabase connection, you need to get the correct connection string from your Supabase dashboard.")
    print("1. Go to your Supabase project dashboard")
    print("2. Navigate to Project Settings > Database")
    print("3. Under 'Connection string', you'll see different connection options:")
    print("   - Direct connection (default)")
    print("   - Connection pooling (session mode)")
    print("   - Connection pooling (transaction mode)")
    print("\nFor this script, we recommend using the 'Connection pooling (session mode)'.")
    print("Copy the connection string and set it as DB_CONNECTION_STRING environment variable.")
    print("Example: export DB_CONNECTION_STRING='postgres://postgres.fwnitauuyzxnsvgsbrzr:your-password@aws-0-us-west-1.pooler.supabase.com:5432/postgres'")
    
    # Check if we have a direct connection string
    connection_string = os.environ.get('DB_CONNECTION_STRING')
    if connection_string:
        print("\nUsing provided DB_CONNECTION_STRING environment variable.")
        app.config['SQLALCHEMY_DATABASE_URI'] = connection_string
        
        # Print connection info (without password)
        safe_uri = connection_string
        if ':' in connection_string:
            parts = connection_string.split(':')
            if '@' in parts[2]:
                user_pass = parts[1].lstrip('/')
                if user_pass:  # If there's a password
                    safe_uri = connection_string.replace(user_pass, '********')
        
        print(f"Database URI: {safe_uri}")
        return True
    
    # If no connection string is provided, try to build one from individual variables
    print("\nNo DB_CONNECTION_STRING found. Trying to build connection string from individual variables...")
    
    # Check for required environment variables
    required_vars = ['DB_PASS', 'DB_HOST']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set either DB_CONNECTION_STRING or the individual variables (DB_USER, DB_PASS, DB_HOST, etc.)")
        sys.exit(1)
    
    # Get connection details
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASS', '')
    dbname = os.environ.get('DB_NAME', 'postgres')
    host = os.environ.get('DB_HOST', '')
    port = os.environ.get('DB_PORT', '5432')
    
    # Use the exact host provided in environment variables
    direct_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require"
    app.config['SQLALCHEMY_DATABASE_URI'] = direct_uri
    
    # Print connection info (without password)
    safe_uri = direct_uri.replace(password, '********')
    print(f"Database URI: {safe_uri}")
    
    return True

def create_tables():
    """Create all tables in the database"""
    print("Creating tables in Supabase...")
    try:
        from app import Base
        
        # Create engine with the production URI and SSL mode
        connect_args = {"sslmode": "require"}
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], connect_args=connect_args)
        
        # Create all tables
        with app.app_context():
            Base.metadata.create_all(engine)
            
        print("Tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        return False

def test_connection():
    """Test the database connection"""
    print("Testing database connection...")
    try:
        # Create engine with the production URI and SSL mode
        connect_args = {"sslmode": "require"}
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], connect_args=connect_args)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Connection successful!")
        return True
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("Supabase Database Migration Tool")
    print("=" * 50)
    
    # Setup production config
    if not setup_production_config():
        return
    
    # Test connection
    if not test_connection():
        return
    
    # Confirm before proceeding
    print("\nWarning: This will create/update tables in your Supabase PostgreSQL database.")
    confirm = input("Do you want to proceed? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        return
    
    # Create tables
    start_time = time.time()
    success = create_tables()
    end_time = time.time()
    
    if success:
        print(f"\nMigration completed in {end_time - start_time:.2f} seconds.")
        print("\nNext steps:")
        print("1. Verify your tables in the Supabase dashboard")
        print("2. Update your deployment environment variables")
        print("3. Deploy your application to Cloud Run")
    else:
        print("\nMigration failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 