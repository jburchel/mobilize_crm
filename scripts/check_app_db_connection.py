import os
import sys
from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import text

# Add parent directory to path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app modules
from config import get_config
from database import db, init_db
from models import Person, Church, Contacts

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
        
        # Check contacts table
        contacts_count = db.session.query(Contacts).count()
        print(f"✅ Contacts table has {contacts_count} records")
        
        # Check contacts by type
        contacts_by_type = db.session.query(Contacts.type, db.func.count(Contacts.id)).group_by(Contacts.type).all()
        for type_name, count in contacts_by_type:
            print(f"  - {type_name}: {count} records")
        
        # Check people table
        people_count = db.session.query(Person).count()
        print(f"✅ People table has {people_count} records")
        
        # Get a sample person
        if people_count > 0:
            sample_person = db.session.query(Person).first()
            print(f"  - Sample person: {sample_person.first_name} {sample_person.last_name} (ID: {sample_person.id})")
        
        # Check churches table
        churches_count = db.session.query(Church).count()
        print(f"✅ Churches table has {churches_count} records")
        
        # Get a sample church
        if churches_count > 0:
            sample_church = db.session.query(Church).first()
            print(f"  - Sample church: {sample_church.church_name} (ID: {sample_church.id})")
        
        # Check the query used in the churches route
        churches_query = db.session.query(Church).filter(Church.type == 'church')
        churches_objects = churches_query.limit(100).all()
        print(f"✅ Churches query returned {len(churches_objects)} records")
        
        # Check the query used in the people route
        people_query = db.session.query(Person).filter(Person.type == 'person')
        people_objects = people_query.limit(100).all()
        print(f"✅ People query returned {len(people_objects)} records")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc()) 