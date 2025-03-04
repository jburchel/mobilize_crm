#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Person, Contacts
import json

# Load environment variables
load_dotenv()

# Get database connection string
db_uri = os.getenv('DB_CONNECTION_STRING')
print(f"Using database: {db_uri}")

# Create engine and session
engine = create_engine(db_uri)
Session = sessionmaker(bind=engine)
session = Session()

# Get user ID
user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
print(f"Querying for user_id: {user_id}")

# SQLAlchemy ORM query (the way your application queries)
try:
    people = session.query(Person).filter(
        Person.type == 'person',
        Person.user_id == user_id
    ).all()
    print(f"SQLAlchemy ORM query - Found {len(people)} people")
    
    # Dump people data to a file
    people_data = []
    for person in people:
        people_data.append({
            'id': person.id,
            'first_name': person.first_name,
            'last_name': person.last_name,
            'email': person.email,
            'type': getattr(person, 'type', None),
            'user_id': person.user_id,
            'church_id': person.church_id
        })
    
    with open('people_dump.json', 'w') as f:
        json.dump(people_data, f, indent=2)
    print(f"Dumped {len(people_data)} people to people_dump.json")
    
except Exception as e:
    print(f"Error with SQLAlchemy ORM query: {str(e)}")

# Close session
session.close() 