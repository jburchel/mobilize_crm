from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
import json
import firebase_admin
from firebase_admin import credentials, auth
import requests

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK if not already initialized
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)

# Get database connection string from environment variables
db_connection_string = os.getenv('DATABASE_URL')
if not db_connection_string:
    print("DATABASE_URL not found in environment variables")
    exit(1)

# Create database engine
engine = create_engine(db_connection_string)

def check_database():
    """Check the database for user IDs and people records"""
    try:
        # Connect to the database and execute the query
        with engine.connect() as connection:
            # Check user IDs in people table
            user_query = text("SELECT DISTINCT user_id FROM people")
            user_result = connection.execute(user_query)
            user_ids = [row[0] for row in user_result]
            
            print(f"Found {len(user_ids)} distinct user IDs in the people table:")
            for user_id in user_ids:
                print(f"  - {user_id}")
                
                # Count records for this user_id
                count_query = text("SELECT COUNT(*) FROM people WHERE user_id = :user_id AND type = 'person'")
                count_result = connection.execute(count_query, {"user_id": user_id}).scalar()
                print(f"    People records: {count_result}")
                
                # Check if this user_id exists in the contacts table
                contacts_query = text("SELECT COUNT(*) FROM contacts WHERE user_id = :user_id")
                contacts_result = connection.execute(contacts_query, {"user_id": user_id}).scalar()
                print(f"    Contacts records: {contacts_result}")
                
    except Exception as e:
        print(f"Error querying database: {e}")

def check_auth_token(user_id):
    """Check if we can create a valid token for the user"""
    try:
        # Create a custom token
        custom_token = auth.create_custom_token(user_id).decode('utf-8')
        print(f"Successfully created custom token for user_id: {user_id}")
        print(f"Custom token (first 20 chars): {custom_token[:20]}...")
        
        # Note: In a real application, this custom token would be sent to the client
        # and exchanged for an ID token using the Firebase Authentication SDK
        print("\nNote: This custom token cannot be used directly with the API.")
        print("It needs to be exchanged for an ID token using the Firebase Authentication SDK.")
        
    except Exception as e:
        print(f"Error creating custom token: {e}")

def check_session_scope():
    """Check if session_scope is correctly imported in routes"""
    try:
        # Check people.py
        with open('routes/people.py', 'r') as f:
            people_content = f.read()
            if 'from database import db, session_scope' in people_content:
                print("✅ routes/people.py correctly imports session_scope from database")
            else:
                print("❌ routes/people.py does not import session_scope from database")
        
        # Check dashboard.py
        with open('routes/dashboard.py', 'r') as f:
            dashboard_content = f.read()
            if 'from database import db, session_scope' in dashboard_content:
                print("✅ routes/dashboard.py correctly imports session_scope from database")
            else:
                print("❌ routes/dashboard.py does not import session_scope from database")
                
    except Exception as e:
        print(f"Error checking session_scope imports: {e}")

def main():
    print("=== Database Check ===")
    check_database()
    
    print("\n=== Authentication Check ===")
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"  # The user ID we found in the database
    check_auth_token(user_id)
    
    print("\n=== Session Scope Check ===")
    check_session_scope()

if __name__ == "__main__":
    main() 