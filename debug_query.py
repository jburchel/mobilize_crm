#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
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

# Get user ID
user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
print(f"Querying for user_id: {user_id}")

# Direct SQL query to check data
result = session.execute(text("SELECT COUNT(*) FROM people WHERE user_id = :user_id"), {"user_id": user_id})
count = result.scalar()
print(f"SQL direct query - Number of people with user_id={user_id}: {count}")

result = session.execute(text("SELECT COUNT(*) FROM contacts WHERE type = 'person'"))
count = result.scalar()
print(f"SQL direct query - Number of contacts with type='person': {count}")

result = session.execute(text("SELECT COUNT(*) FROM people p JOIN contacts c ON p.id = c.id WHERE c.type = 'person' AND p.user_id = :user_id"), {"user_id": user_id})
count = result.scalar()
print(f"SQL direct query - Number of people with type='person' and user_id={user_id}: {count}")

# SQLAlchemy ORM query (the way your application queries)
try:
    people = session.query(Person).filter(
        Person.type == 'person',
        Person.user_id == user_id
    ).all()
    print(f"SQLAlchemy ORM query - Found {len(people)} people")
    
    # Print the first few people
    for i, person in enumerate(people[:5]):
        print(f"Person {i+1}: ID={person.id}, Name={person.first_name} {person.last_name}")
except Exception as e:
    print(f"Error with SQLAlchemy ORM query: {str(e)}")

# Close session
session.close() 