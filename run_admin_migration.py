"""
Script to run the admin features migration.
"""
import os
import sys
from flask import Flask
from models import Base, Permission, Office, UserOffice, Church
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from migrations.admin_features import upgrade

def run_migration():
    """Run the admin features migration."""
    print("Starting admin features migration...")
    
    try:
        # Run the upgrade function from the migration
        upgrade()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration() 