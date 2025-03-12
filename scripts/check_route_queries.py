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
        
        # Get the user_id from user_offices
        user_id_result = db.session.execute(text("SELECT user_id FROM user_offices LIMIT 1")).fetchone()
        if user_id_result:
            user_id = user_id_result[0]
            print(f"✅ Found user_id in user_offices: {user_id}")
            
            # Check the people query with user_id filter
            people_query = db.session.query(Person).filter(
                Person.type == 'person',
                Person.user_id == user_id
            )
            people_objects = people_query.limit(100).all()
            print(f"✅ People query with user_id filter returned {len(people_objects)} records")
            
            # Check the people query without user_id filter
            people_query = db.session.query(Person).filter(
                Person.type == 'person'
            )
            people_objects = people_query.limit(100).all()
            print(f"✅ People query without user_id filter returned {len(people_objects)} records")
            
            # Get the office_id from user_offices
            office_id_result = db.session.execute(text("SELECT office_id FROM user_offices LIMIT 1")).fetchone()
            if office_id_result:
                office_id = office_id_result[0]
                print(f"✅ Found office_id in user_offices: {office_id}")
                
                # Check the churches query with office_id filter
                churches_query = db.session.query(Church).filter(
                    Church.type == 'church',
                    Church.office_id == office_id
                )
                churches_objects = churches_query.limit(100).all()
                print(f"✅ Churches query with office_id filter returned {len(churches_objects)} records")
                
                # Check the churches query without office_id filter
                churches_query = db.session.query(Church).filter(
                    Church.type == 'church'
                )
                churches_objects = churches_query.limit(100).all()
                print(f"✅ Churches query without office_id filter returned {len(churches_objects)} records")
            else:
                print("❌ No office_id found in user_offices")
        else:
            print("❌ No user_id found in user_offices")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc()) 