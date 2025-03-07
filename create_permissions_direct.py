"""
Script to directly add permissions using SQLite.
"""
import sqlite3
import datetime

def create_permissions():
    """Create permissions directly using SQLite."""
    print("Creating permissions directly...")
    
    # Connect to the database
    conn = sqlite3.connect('mobilize_crm.db')
    cursor = conn.cursor()
    
    # Get current timestamp
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Define default permissions
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
    
    try:
        # Insert permissions
        for i, perm in enumerate(default_permissions, start=1):
            cursor.execute(
                "INSERT INTO permissions (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (i, perm["name"], perm["description"], now, now)
            )
        
        # Commit changes
        conn.commit()
        print(f"Successfully created {len(default_permissions)} permissions")
    except Exception as e:
        conn.rollback()
        print(f"Error creating permissions: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_permissions() 