from models import Person
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# User ID to check
user_id = os.getenv('FIREBASE_USER_ID', 'CVjBoi6rGMazZ3J6vAAtu1hra4H2')
print(f"Checking people data for user_id: {user_id}")

# Get the database URI from environment variables
database_uri = os.getenv('DATABASE_URL')
if not database_uri:
    print("Error: DATABASE_URL environment variable not set")
    exit(1)

print(f"Using database URI: {database_uri[:20]}...")

# Create a new engine and session
engine = create_engine(database_uri)
Session = sessionmaker(bind=engine)
session = Session()

try:
    query = session.query(Person).filter(
        Person.type == 'person',
        Person.user_id == user_id
    )
    people_list = query.all()
    print(f"Found {len(people_list)} people")
    
    # Print the first 5 people
    for i, person in enumerate(people_list[:5]):
        print(f"  {i+1}. {person.first_name} {person.last_name} (ID: {person.id}, User ID: {person.user_id})")
finally:
    session.close() 