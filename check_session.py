#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Person, Contacts, session_scope
import traceback

# Load environment variables
load_dotenv()

# Print environment info
env = os.environ.get('FLASK_ENV', 'development')
print(f"Running in {env} environment")
db_uri = os.environ.get('DB_CONNECTION_STRING')
print(f"Database URI: {db_uri}")

# Test 1: Using session_scope
print("\nTest 1: Using session_scope")
try:
    user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
    with session_scope() as session:
        query = session.query(Person).filter(
            Person.type == 'person',
            Person.user_id == user_id
        )
        people_list = query.all()
        print(f"Found {len(people_list)} people using session_scope")
        
        # Print a few sample people
        for person in people_list[:5]:
            print(f"Person ID: {person.id}, Name: {person.first_name} {person.last_name}, Type: {person.type}, User ID: {person.user_id}")
except Exception as e:
    print(f"Error using session_scope: {e}")
    traceback.print_exc()

# Test 2: Using direct connection
print("\nTest 2: Using direct connection")
try:
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
        query = session.query(Person).filter(
            Person.type == 'person',
            Person.user_id == user_id
        )
        people_list = query.all()
        print(f"Found {len(people_list)} people using direct connection")
        
        # Print a few sample people
        for person in people_list[:5]:
            print(f"Person ID: {person.id}, Name: {person.first_name} {person.last_name}, Type: {person.type}, User ID: {person.user_id}")
    finally:
        session.close()
except Exception as e:
    print(f"Error using direct connection: {e}")
    traceback.print_exc()

# Test 3: Check if get_current_user_id is working correctly
print("\nTest 3: Simulating get_current_user_id")
try:
    # This is what get_current_user_id does in the route
    user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'  # Hardcoded for testing
    print(f"get_current_user_id would return: {user_id}")
    
    with session_scope() as session:
        query = session.query(Person).filter(
            Person.type == 'person',
            Person.user_id == user_id
        )
        people_list = query.all()
        print(f"Found {len(people_list)} people with user_id from get_current_user_id")
except Exception as e:
    print(f"Error simulating get_current_user_id: {e}")
    traceback.print_exc() 