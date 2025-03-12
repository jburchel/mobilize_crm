import os
import sys
from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import text, inspect
from sqlalchemy.orm.relationships import RelationshipProperty

# Add parent directory to path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app modules
from config import get_config
from database import db, init_db
from models import Base, Person, Church, Contacts

# Load environment variables
load_dotenv()

# Create a minimal Flask app for testing
app = Flask(__name__)
app.config.from_object(get_config())

# Initialize database
init_db(app)

# Test database connection
with app.app_context():
    try:
        # Check if we can connect to the database
        result = db.session.execute(text("SELECT 1")).scalar()
        print(f"✅ Database connection successful: {result}")
        
        # Check the Person model
        print("\n=== Person Model ===")
        person_mapper = inspect(Person)
        print(f"✅ Person model has {len(person_mapper.attrs)} attributes")
        
        # Print column attributes
        print("\nColumn Attributes:")
        for key, column in person_mapper.columns.items():
            print(f"  - {key}: {column.type}")
        
        # Print relationship attributes
        print("\nRelationship Attributes:")
        for key, rel in person_mapper.relationships.items():
            print(f"  - {key}: {rel.target}")
        
        # Check the Church model
        print("\n=== Church Model ===")
        church_mapper = inspect(Church)
        print(f"✅ Church model has {len(church_mapper.attrs)} attributes")
        
        # Print column attributes
        print("\nColumn Attributes:")
        for key, column in church_mapper.columns.items():
            print(f"  - {key}: {column.type}")
        
        # Print relationship attributes
        print("\nRelationship Attributes:")
        for key, rel in church_mapper.relationships.items():
            print(f"  - {key}: {rel.target}")
        
        # Check the Contacts model
        print("\n=== Contacts Model ===")
        contacts_mapper = inspect(Contacts)
        print(f"✅ Contacts model has {len(contacts_mapper.attrs)} attributes")
        
        # Print column attributes
        print("\nColumn Attributes:")
        for key, column in contacts_mapper.columns.items():
            print(f"  - {key}: {column.type}")
        
        # Print relationship attributes
        print("\nRelationship Attributes:")
        for key, rel in contacts_mapper.relationships.items():
            print(f"  - {key}: {rel.target}")
        
        # Try a direct SQL query for people
        print("\n=== Direct SQL Query for People ===")
        result = db.session.execute(text("""
            SELECT p.id, c.first_name, c.last_name, p.user_id
            FROM people p
            JOIN contacts c ON p.id = c.id
            WHERE c.type = 'person'
            LIMIT 5
        """)).fetchall()
        print(f"✅ Direct SQL query returned {len(result)} records")
        for row in result:
            print(f"  - ID: {row[0]}, Name: {row[1]} {row[2]}, User ID: {row[3]}")
        
        # Try a direct SQL query for churches
        print("\n=== Direct SQL Query for Churches ===")
        result = db.session.execute(text("""
            SELECT ch.id, c.church_name, ch.office_id
            FROM churches ch
            JOIN contacts c ON ch.id = c.id
            WHERE c.type = 'church'
            LIMIT 5
        """)).fetchall()
        print(f"✅ Direct SQL query returned {len(result)} records")
        for row in result:
            print(f"  - ID: {row[0]}, Name: {row[1]}, Office ID: {row[2]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc()) 