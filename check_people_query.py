#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from models import Person, Contacts

# Load environment variables
load_dotenv()

# Get database connection string
db_uri = os.getenv('DB_CONNECTION_STRING')
print(f"Using database: {db_uri}")

# Create engine and session
engine = create_engine(db_uri)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Get user ID
    user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
    print(f"Querying for user_id: {user_id}")
    
    # First, let's check what's in the contacts table with type='person'
    contacts_query = session.query(Contacts).filter(
        Contacts.type == 'person'
    ).limit(5)
    
    print("\nSample contacts with type='person':")
    contacts_sample = contacts_query.all()
    print(f"Found {len(contacts_sample)} sample contacts")
    
    for contact in contacts_sample:
        print(f"Contact ID: {contact.id}, Name: {contact.first_name} {contact.last_name}, Type: {contact.type}")
    
    # Now check the people table with the same filter as the route
    people_query = session.query(Person).filter(
        Person.type == 'person',
        Person.user_id == user_id
    )
    
    # Print the SQL query for debugging
    print(f"\nSQL Query: {people_query}")
    
    # Execute the query
    people_list = people_query.all()
    print(f"Found {len(people_list)} people with the route filter")
    
    # Print a few sample people
    for person in people_list[:5]:
        print(f"Person ID: {person.id}, Name: {person.first_name} {person.last_name}, Type: {person.type}, User ID: {person.user_id}")
    
    # Now try without the type filter
    people_query_no_type = session.query(Person).filter(
        Person.user_id == user_id
    )
    
    people_list_no_type = people_query_no_type.all()
    print(f"\nFound {len(people_list_no_type)} people without type filter")
    
    # Check if there are any people with a different type
    if len(people_list_no_type) > 0:
        types = set(p.type for p in people_list_no_type)
        print(f"Types found in people table: {types}")
    
    # Check the contacts table directly
    contacts_count = session.query(Contacts).filter(
        Contacts.type == 'person'
    ).count()
    
    print(f"\nTotal contacts with type='person': {contacts_count}")
    
    # Check if there are any people with NULL type
    null_type_count = session.query(Person).filter(
        Person.type.is_(None),
        Person.user_id == user_id
    ).count()
    
    print(f"People with NULL type: {null_type_count}")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    session.close() 