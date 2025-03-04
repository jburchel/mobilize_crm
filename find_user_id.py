from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
import json

# Load environment variables
load_dotenv()

# Get database connection string from environment variables
db_connection_string = os.getenv('DATABASE_URL')
if not db_connection_string:
    print("DATABASE_URL not found in environment variables")
    exit(1)

# Create database engine
engine = create_engine(db_connection_string)

# Query to find distinct user_ids in the people table
query = text("SELECT DISTINCT user_id FROM people")

try:
    # Connect to the database and execute the query
    with engine.connect() as connection:
        result = connection.execute(query)
        user_ids = [row[0] for row in result]
        
        print(f"Found {len(user_ids)} distinct user IDs in the people table:")
        for user_id in user_ids:
            print(f"  - {user_id}")
            
            # Count records for this user_id
            count_query = text("SELECT COUNT(*) FROM people WHERE user_id = :user_id")
            count_result = connection.execute(count_query, {"user_id": user_id}).scalar()
            print(f"    Records: {count_result}")
            
except Exception as e:
    print(f"Error querying database: {e}") 