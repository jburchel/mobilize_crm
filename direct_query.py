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

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def query_people():
    """Query the people table for the user ID we found"""
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"
    
    try:
        # Connect to the database and execute the query
        with engine.connect() as connection:
            # Query people table
            query = text("""
                SELECT id, user_id, type
                FROM people
                WHERE type = 'person' AND user_id = :user_id
            """)
            
            result = connection.execute(query, {"user_id": user_id})
            people = []
            for row in result:
                people.append({
                    'id': row[0],
                    'user_id': row[1],
                    'type': row[2]
                })
            
            print(f"Found {len(people)} people for user_id: {user_id}")
            
            # Print the first 5 people
            for i, person in enumerate(people[:5]):
                print(f"{i+1}. ID: {person['id']}, Type: {person['type']}")
            
            # Save the results to a JSON file
            with open('people_results.json', 'w') as f:
                json.dump(people, f, default=json_serial, indent=2)
                
            print(f"Saved results to people_results.json")
            
            # Now let's check the contacts table for these IDs
            if people:
                people_ids = [p['id'] for p in people]
                
                # If there's only one ID, we need to handle it differently
                if len(people_ids) == 1:
                    contacts_query = text("""
                        SELECT id, first_name, last_name, email, type
                        FROM contacts
                        WHERE id = :id
                    """)
                    contacts_result = connection.execute(contacts_query, {"id": people_ids[0]})
                else:
                    contacts_query = text("""
                        SELECT id, first_name, last_name, email, type
                        FROM contacts
                        WHERE id IN :ids
                    """)
                    contacts_result = connection.execute(contacts_query, {"ids": tuple(people_ids)})
                
                contacts = []
                for row in contacts_result:
                    contacts.append({
                        'id': row[0],
                        'first_name': row[1],
                        'last_name': row[2],
                        'email': row[3],
                        'type': row[4]
                    })
                
                print(f"\nFound {len(contacts)} matching contacts")
                
                # Print the first 5 contacts
                for i, contact in enumerate(contacts[:5]):
                    print(f"{i+1}. {contact['first_name']} {contact['last_name']} (ID: {contact['id']}, Type: {contact['type']})")
                
                # Save the results to a JSON file
                with open('contacts_results.json', 'w') as f:
                    json.dump(contacts, f, default=json_serial, indent=2)
                    
                print(f"Saved results to contacts_results.json")
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    query_people() 