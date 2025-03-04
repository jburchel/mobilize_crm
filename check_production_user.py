import os
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK if not already initialized
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)

# Get email from environment or use default
email = os.getenv('USER_EMAIL', 'j.burchel@crossoverglobal.net')
print(f"Checking user ID for email: {email}")

# Try to get the user by email
try:
    user = auth.get_user_by_email(email)
    print(f"Firebase User ID: {user.uid}")
    print(f"Display Name: {user.display_name}")
    print(f"Email: {user.email}")
    print(f"Email Verified: {user.email_verified}")
    
    # Store the user ID for database queries
    user_id = user.uid
except Exception as e:
    print(f"Error getting Firebase user: {str(e)}")
    exit(1)

# Get database connection string from environment variables
db_connection_string = os.getenv('DATABASE_URL')
if not db_connection_string:
    print("DATABASE_URL not found in environment variables")
    exit(1)

print(f"\nConnecting to database: {db_connection_string[:20]}...")

# Create database engine
engine = create_engine(db_connection_string)

# First, let's check the schema of the tables
print("\nChecking database schema:")
with engine.connect() as conn:
    # Check people table schema
    query = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'people'
    """)
    result = conn.execute(query)
    print("\nPeople table schema:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
    
    # Check contacts table schema
    query = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'contacts'
    """)
    result = conn.execute(query)
    print("\nContacts table schema:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
    
    # Check churches table schema
    query = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'churches'
    """)
    result = conn.execute(query)
    print("\nChurches table schema:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")

# Check people records
print("\nChecking people records:")
with engine.connect() as conn:
    # Query to count people with this user_id
    query = text("SELECT COUNT(*) FROM people WHERE user_id = :user_id")
    result = conn.execute(query, {"user_id": user_id})
    count = result.scalar()
    print(f"Found {count} people records with user_id: {user_id}")
    
    # Query to get a sample of people with this user_id
    if count > 0:
        query = text("SELECT id FROM people WHERE user_id = :user_id LIMIT 5")
        result = conn.execute(query, {"user_id": user_id})
        print("\nSample people IDs:")
        for row in result:
            print(f"  ID: {row[0]}")
    
    # Check if there are people with NULL user_id
    query = text("SELECT COUNT(*) FROM people WHERE user_id IS NULL")
    result = conn.execute(query)
    null_count = result.scalar()
    print(f"\nFound {null_count} people records with NULL user_id")

# Check contacts table for people data
print("\nChecking contacts table for people data:")
with engine.connect() as conn:
    # Join people and contacts to get people information
    query = text("""
        SELECT c.id, c.first_name, c.last_name, p.user_id
        FROM contacts c
        JOIN people p ON c.id = p.id
        WHERE p.user_id = :user_id AND c.type = 'person'
        LIMIT 5
    """)
    result = conn.execute(query, {"user_id": user_id})
    print("\nSample people from contacts join:")
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"  ID: {row[0]}, Name: {row[1]} {row[2]}, User ID: {row[3]}")
    else:
        print("  No results found")

# Check churches records
print("\nChecking churches records:")
with engine.connect() as conn:
    # Count all churches
    query = text("SELECT COUNT(*) FROM churches")
    result = conn.execute(query)
    total_count = result.scalar()
    print(f"Total churches in database: {total_count}")
    
    # Get a sample of churches
    query = text("""
        SELECT c.id, c.church_name, ch.id
        FROM contacts c
        JOIN churches ch ON c.id = ch.id
        WHERE c.type = 'church'
        LIMIT 5
    """)
    result = conn.execute(query)
    print("\nSample churches records:")
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"  ID: {row[0]}, Name: {row[1]}")
    else:
        print("  No results found")
    
    # Check if any churches are associated with people that have this user_id
    query = text("""
        SELECT c.id, c.church_name, p.id, p.user_id
        FROM contacts c
        JOIN churches ch ON c.id = ch.id
        JOIN people p ON ch.id = p.church_id
        WHERE p.user_id = :user_id
        LIMIT 5
    """)
    result = conn.execute(query, {"user_id": user_id})
    print("\nChurches associated with your people records:")
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"  Church ID: {row[0]}, Name: {row[1]}, Person ID: {row[2]}, User ID: {row[3]}")
    else:
        print("  No results found") 