"""
Migration script to create the contacts table.
This is needed because the Contacts class is used as a base class for Person and Church,
but the table itself doesn't exist in the database.
"""

import sys
import os

# Add the parent directory to the path so we can import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer, String, Text, Date
from sqlalchemy.orm import sessionmaker
from models import Base, Contacts

def check_table_exists(engine, table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def upgrade():
    """
    Create the contacts table if it doesn't exist.
    """
    # Get database URI from environment or use default
    database_uri = os.environ.get('DATABASE_URL', 'sqlite:///instance/mobilize_crm.db')
    
    # Create engine
    engine = create_engine(database_uri)
    
    # Check if contacts table already exists
    if not check_table_exists(engine, 'contacts'):
        # Create the contacts table
        Base.metadata.create_all(engine, tables=[Contacts.__table__])
        
        print("Created contacts table")
    else:
        print("Contacts table already exists")

def downgrade():
    """
    Drop the contacts table.
    """
    # Get database URI from environment or use default
    database_uri = os.environ.get('DATABASE_URL', 'sqlite:///instance/mobilize_crm.db')
    
    # Create engine
    engine = create_engine(database_uri)
    
    # Check if contacts table exists
    if check_table_exists(engine, 'contacts'):
        # Drop the contacts table
        Base.metadata.drop_all(engine, tables=[Contacts.__table__])
        
        print("Dropped contacts table")
    else:
        print("Contacts table does not exist")

if __name__ == "__main__":
    upgrade() 