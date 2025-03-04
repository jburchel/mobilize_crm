from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text, inspect

# Load environment variables
load_dotenv()

# Get database connection string from environment variables
db_connection_string = os.getenv('DATABASE_URL')
if not db_connection_string:
    print("DATABASE_URL not found in environment variables")
    exit(1)

# Create database engine
engine = create_engine(db_connection_string)

def check_table_schema(table_name):
    """Check the schema of a table"""
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        
        print(f"Schema for table '{table_name}':")
        for column in columns:
            print(f"  - {column['name']}: {column['type']}")
            
    except Exception as e:
        print(f"Error checking schema: {e}")

def main():
    # Check the contacts table schema
    check_table_schema('contacts')
    
    # Also check the people table for comparison
    print("\n")
    check_table_schema('people')

if __name__ == "__main__":
    main() 