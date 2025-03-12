import os
import sys
from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

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
        
        # Get the database URI
        print(f"✅ Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Create a direct engine and session
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()
        
        # Check if we can connect to the database directly
        result = session.execute(text("SELECT 1")).scalar()
        print(f"✅ Direct database connection successful: {result}")
        
        # Check contacts table directly
        result = session.execute(text("SELECT COUNT(*) FROM contacts")).scalar()
        print(f"✅ Direct query: Contacts table has {result} records")
        
        # Check people table directly
        result = session.execute(text("SELECT COUNT(*) FROM people")).scalar()
        print(f"✅ Direct query: People table has {result} records")
        
        # Check churches table directly
        result = session.execute(text("SELECT COUNT(*) FROM churches")).scalar()
        print(f"✅ Direct query: Churches table has {result} records")
        
        # Check contacts by type directly
        result = session.execute(text("SELECT type, COUNT(*) FROM contacts GROUP BY type")).fetchall()
        for type_name, count in result:
            print(f"  - {type_name}: {count} records")
        
        # Check if we can query using ORM
        contacts_count = session.query(Contacts).count()
        print(f"✅ ORM query: Contacts table has {contacts_count} records")
        
        # Check contacts by type using ORM
        contacts_by_type = session.query(Contacts.type, db.func.count(Contacts.id)).group_by(Contacts.type).all()
        for type_name, count in contacts_by_type:
            print(f"  - {type_name}: {count} records")
        
        # Check people table using ORM
        people_count = session.query(Person).count()
        print(f"✅ ORM query: People table has {people_count} records")
        
        # Check churches table using ORM
        churches_count = session.query(Church).count()
        print(f"✅ ORM query: Churches table has {churches_count} records")
        
        # Check the query used in the churches route
        churches_query = session.query(Church).filter(Church.type == 'church')
        churches_objects = churches_query.limit(100).all()
        print(f"✅ Churches query returned {len(churches_objects)} records")
        
        # Check the query used in the people route
        people_query = session.query(Person).filter(Person.type == 'person')
        people_objects = people_query.limit(100).all()
        print(f"✅ People query returned {len(people_objects)} records")
        
        # Close the session
        session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc()) 