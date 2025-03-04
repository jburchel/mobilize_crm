#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from flask import Flask
from models import Person
from database import init_db, session_scope
import traceback

# Load environment variables
load_dotenv()

# Print environment info
env = os.environ.get('FLASK_ENV', 'development')
print(f"Running in {env} environment")

# Create a Flask app with the correct configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_CONNECTION_STRING')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Initialize the database with the app
init_db(app)

# Test the fix
with app.app_context():
    try:
        user_id = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
        with session_scope() as session:
            query = session.query(Person).filter(
                Person.type == 'person',
                Person.user_id == user_id
            )
            people_list = query.all()
            print(f"Found {len(people_list)} people using fixed session_scope")
            
            # Print a few sample people
            for person in people_list[:5]:
                print(f"Person ID: {person.id}, Name: {person.first_name} {person.last_name}, Type: {person.type}, User ID: {person.user_id}")
    except Exception as e:
        print(f"Error using fixed session_scope: {e}")
        traceback.print_exc() 