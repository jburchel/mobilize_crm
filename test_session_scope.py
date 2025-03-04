from dotenv import load_dotenv
import os
import json
from datetime import datetime
from models import Person, session_scope as models_session_scope
from database import session_scope as database_session_scope
from flask import Flask

# Load environment variables
load_dotenv()

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def test_models_session_scope():
    """Test the session_scope from models.py"""
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"
    
    try:
        # Use the session_scope from models.py
        with models_session_scope() as session:
            # Query people using the ORM
            people = session.query(Person).filter(
                Person.type == 'person',
                Person.user_id == user_id
            ).all()
            
            print(f"Using models_session_scope: Found {len(people)} people for user_id: {user_id}")
            
            # Print the first 5 people
            for i, person in enumerate(people[:5]):
                print(f"{i+1}. {person.first_name} {person.last_name} (ID: {person.id}, Type: {person.type})")
            
    except Exception as e:
        print(f"Error using models_session_scope: {e}")

def test_database_session_scope():
    """Test the session_scope from database.py"""
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"
    
    try:
        # Create a Flask app context
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize the database with the app
        from database import init_db
        init_db(app)
        
        with app.app_context():
            # Use the session_scope from database.py
            with database_session_scope() as session:
                # Query people using the ORM
                people = session.query(Person).filter(
                    Person.type == 'person',
                    Person.user_id == user_id
                ).all()
                
                print(f"Using database_session_scope: Found {len(people)} people for user_id: {user_id}")
                
                # Print the first 5 people
                for i, person in enumerate(people[:5]):
                    print(f"{i+1}. {person.first_name} {person.last_name} (ID: {person.id}, Type: {person.type})")
            
    except Exception as e:
        print(f"Error using database_session_scope: {e}")

if __name__ == "__main__":
    print("Testing session_scope from models.py...")
    test_models_session_scope()
    
    print("\nTesting session_scope from database.py...")
    test_database_session_scope() 