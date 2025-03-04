import os
from dotenv import load_dotenv
import psycopg2
import json

# Load environment variables
load_dotenv()

# Get database connection details from environment variables
# First check for a direct connection string
db_connection_string = os.environ.get('DATABASE_URL')

if not db_connection_string:
    # For Supabase PostgreSQL using individual variables
    db_user = os.environ.get('DB_USER', 'postgres')
    db_pass = os.environ.get('DB_PASS')
    db_name = os.environ.get('DB_NAME', 'postgres')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '5432')
    
    # Construct the database URI
    db_connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# User ID to filter by
user_id = os.getenv('FIREBASE_USER_ID', 'CVjBoi6rGMazZ3J6vAAtu1hra4H2')

print(f"Using database connection string: {db_connection_string}")

# Connect to the database
try:
    conn = psycopg2.connect(db_connection_string)
    print("Successfully connected to the database")
except Exception as e:
    print(f"Error connecting to database: {e}")
    exit(1)

# Create a cursor
cur = conn.cursor()

# Query people
print(f"\n--- Querying people for user_id: {user_id} ---")
try:
    cur.execute("""
        SELECT p.id, c.first_name, c.last_name, c.email, c.type, p.user_id
        FROM people p
        JOIN contacts c ON p.id = c.id
        WHERE c.type = 'person' AND p.user_id = %s
        LIMIT 10
    """, (user_id,))

    people = cur.fetchall()
    print(f"Found {len(people)} people")

    if people:
        print("\nSample people:")
        for person in people[:5]:  # Show up to 5 people
            print(f"ID: {person[0]}, Name: {person[1]} {person[2]}, Email: {person[3]}, Type: {person[4]}, User ID: {person[5]}")
except Exception as e:
    print(f"Error querying people: {e}")

# Query churches
print(f"\n--- Querying churches ---")
try:
    cur.execute("""
        SELECT c.id, c.church_name, c.email, c.type, ch.church_pipeline
        FROM churches ch
        JOIN contacts c ON ch.id = c.id
        LIMIT 10
    """)

    churches = cur.fetchall()
    print(f"Found {len(churches)} churches")

    if churches:
        print("\nSample churches:")
        for church in churches[:5]:  # Show up to 5 churches
            print(f"ID: {church[0]}, Name: {church[1]}, Email: {church[2]}, Type: {church[3]}, Pipeline: {church[4]}")
except Exception as e:
    print(f"Error querying churches: {e}")

# Close the connection
cur.close()
conn.close() 