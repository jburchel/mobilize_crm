from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Get database connection string from environment variables
db_connection_string = os.getenv('DATABASE_URL')
if not db_connection_string:
    print("DATABASE_URL not found in environment variables")
    exit(1)

# Create database engine
engine = create_engine(db_connection_string)

def check_ids():
    """Check the relationship between people and contacts IDs"""
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"
    
    try:
        # Connect to the database and execute the query
        with engine.connect() as connection:
            # Get all people IDs for the user
            people_query = text("""
                SELECT id
                FROM people
                WHERE type = 'person' AND user_id = :user_id
                LIMIT 10
            """)
            
            people_result = connection.execute(people_query, {"user_id": user_id})
            people_ids = [row[0] for row in people_result]
            
            print(f"First 10 people IDs: {people_ids}")
            
            # Check if these IDs exist in the contacts table
            for people_id in people_ids:
                contacts_query = text("""
                    SELECT id, first_name, last_name, type
                    FROM contacts
                    WHERE id = :id
                """)
                
                contacts_result = connection.execute(contacts_query, {"id": people_id})
                contacts = [dict(zip(['id', 'first_name', 'last_name', 'type'], row)) for row in contacts_result]
                
                if contacts:
                    print(f"People ID {people_id} exists in contacts table: {contacts[0]}")
                else:
                    print(f"People ID {people_id} does NOT exist in contacts table")
            
            # Now let's check the other way around
            print("\nChecking contacts table for people IDs...")
            
            contacts_query = text("""
                SELECT id, first_name, last_name, type
                FROM contacts
                WHERE type = 'person'
                LIMIT 10
            """)
            
            contacts_result = connection.execute(contacts_query)
            contacts = [dict(zip(['id', 'first_name', 'last_name', 'type'], row)) for row in contacts_result]
            
            print(f"First 10 contacts: {contacts}")
            
            # Check if these IDs exist in the people table
            for contact in contacts:
                people_query = text("""
                    SELECT id, user_id, type
                    FROM people
                    WHERE id = :id
                """)
                
                people_result = connection.execute(people_query, {"id": contact['id']})
                people = [dict(zip(['id', 'user_id', 'type'], row)) for row in people_result]
                
                if people:
                    print(f"Contact ID {contact['id']} exists in people table: {people[0]}")
                else:
                    print(f"Contact ID {contact['id']} does NOT exist in people table")
            
    except Exception as e:
        print(f"Error checking IDs: {e}")

if __name__ == "__main__":
    check_ids() 