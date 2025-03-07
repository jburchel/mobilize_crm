"""
Script to create a super admin user for the USA office.
"""
import sqlite3
import datetime

def create_super_admin():
    """Create a super admin user for the USA office."""
    print("Creating super admin user...")
    
    # Connect to the database
    conn = sqlite3.connect('mobilize_crm.db')
    cursor = conn.cursor()
    
    # Get current timestamp
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Super admin details
    admin_email = "j.burchel@crossoverglobal.net"
    admin_role = "super_admin"
    office_id = 1  # USA Office
    
    try:
        # First, check if we can find a user ID for this email in the contacts table
        # People table inherits from contacts, so we need to join them
        cursor.execute("""
            SELECT p.user_id 
            FROM people p 
            JOIN contacts c ON p.id = c.id 
            WHERE c.email = ? AND p.user_id IS NOT NULL 
            LIMIT 1
        """, (admin_email,))
        result = cursor.fetchone()
        
        user_id = None
        if result and result[0]:
            user_id = result[0]
            print(f"Found existing user ID: {user_id}")
        else:
            # If no user ID found, we'll create a placeholder ID
            # In a real system, this would be the Firebase user ID
            user_id = "admin_" + admin_email.replace('@', '_').replace('.', '_')
            print(f"Created placeholder user ID: {user_id}")
        
        # Check if this user is already a super admin
        cursor.execute("SELECT id FROM user_offices WHERE user_id = ? AND office_id = ? AND role = ?", 
                      (user_id, office_id, admin_role))
        existing = cursor.fetchone()
        
        if existing:
            print(f"User {admin_email} is already a super admin for office ID {office_id}")
        else:
            # Add the user as a super admin
            cursor.execute(
                "INSERT INTO user_offices (user_id, office_id, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, office_id, admin_role, now, now)
            )
            conn.commit()
            print(f"Successfully added {admin_email} as a super admin for office ID {office_id}")
    except Exception as e:
        conn.rollback()
        print(f"Error creating super admin: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_super_admin() 