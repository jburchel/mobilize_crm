"""
Script to create default permissions in the permissions table.
"""
from flask import Flask
from models import Permission
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

def create_default_permissions():
    """Create default permissions in the permissions table."""
    print("Creating default permissions...")
    
    # Get database URI from environment or use default
    database_uri = os.environ.get('DATABASE_URL', 'sqlite:///mobilize_crm.db')
    
    # Create engine and session
    engine = create_engine(database_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        default_permissions = [
            {"name": "view_churches", "description": "Can view churches"},
            {"name": "add_church", "description": "Can add new churches"},
            {"name": "edit_church", "description": "Can edit existing churches"},
            {"name": "delete_church", "description": "Can delete churches"},
            {"name": "view_people", "description": "Can view people"},
            {"name": "add_person", "description": "Can add new people"},
            {"name": "edit_person", "description": "Can edit existing people"},
            {"name": "delete_person", "description": "Can delete people"},
            {"name": "view_communications", "description": "Can view communications"},
            {"name": "add_communication", "description": "Can add new communications"},
            {"name": "edit_communication", "description": "Can edit existing communications"},
            {"name": "delete_communication", "description": "Can delete communications"},
            {"name": "view_tasks", "description": "Can view tasks"},
            {"name": "add_task", "description": "Can add new tasks"},
            {"name": "edit_task", "description": "Can edit existing tasks"},
            {"name": "delete_task", "description": "Can delete tasks"},
            {"name": "manage_users", "description": "Can manage users"},
            {"name": "manage_offices", "description": "Can manage offices"},
            {"name": "manage_permissions", "description": "Can manage permissions"},
        ]
        
        for perm in default_permissions:
            # Check if permission already exists
            existing = session.query(Permission).filter_by(name=perm["name"]).first()
            if not existing:
                session.add(Permission(name=perm["name"], description=perm["description"]))
        
        session.commit()
        print("Default permissions created successfully")
    except Exception as e:
        session.rollback()
        print(f"Error creating permissions: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    create_default_permissions() 