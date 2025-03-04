from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
from models import Person, Contacts

# Load environment variables
load_dotenv()

# Get database connection string from environment variables
db_connection_string = os.getenv('DATABASE_URL')
if not db_connection_string:
    print("DATABASE_URL not found in environment variables")
    exit(1)

# Create database engine
engine = create_engine(db_connection_string)
Session = sessionmaker(bind=engine)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def query_with_orm():
    """Query the database using SQLAlchemy's ORM"""
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"
    
    try:
        # Create a session
        session = Session()
        
        # Query people using the ORM
        people = session.query(Person).filter(
            Person.type == 'person',
            Person.user_id == user_id
        ).all()
        
        print(f"Found {len(people)} people for user_id: {user_id}")
        
        # Print the first 5 people
        for i, person in enumerate(people[:5]):
            print(f"{i+1}. {person.first_name} {person.last_name} (ID: {person.id}, Type: {person.type})")
        
        # Convert to dictionaries for JSON serialization
        people_dicts = []
        for person in people:
            people_dicts.append({
                'id': person.id,
                'first_name': person.first_name,
                'last_name': person.last_name,
                'email': person.email,
                'type': person.type,
                'user_id': person.user_id
            })
        
        # Save the results to a JSON file
        with open('orm_people_results.json', 'w') as f:
            json.dump(people_dicts, f, default=json_serial, indent=2)
            
        print(f"Saved results to orm_people_results.json")
        
        # Query contacts using the ORM
        contacts = session.query(Contacts).filter(
            Contacts.type == 'person'
        ).limit(10).all()
        
        print(f"\nFound {len(contacts)} contacts with type 'person' (limited to 10)")
        
        # Print the contacts
        for i, contact in enumerate(contacts):
            print(f"{i+1}. {contact.first_name} {contact.last_name} (ID: {contact.id}, Type: {contact.type})")
        
        # Close the session
        session.close()
        
    except Exception as e:
        print(f"Error querying database with ORM: {e}")

if __name__ == "__main__":
    query_with_orm() 