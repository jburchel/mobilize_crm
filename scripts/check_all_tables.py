import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Load environment variables
load_dotenv()

# Connect to PostgreSQL database
try:
    pg_engine = create_engine(os.environ.get('DB_CONNECTION_STRING'))
    print("✅ Connected to PostgreSQL database")
except Exception as e:
    print(f"❌ Failed to connect to PostgreSQL database: {e}")
    exit(1)

# Get all tables in PostgreSQL
inspector = inspect(pg_engine)
tables = inspector.get_table_names()
print(f"✅ Found {len(tables)} tables in PostgreSQL:")

# Get row count for each table
with pg_engine.connect() as conn:
    for table in tables:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  - {table}: {count} rows")
        except Exception as e:
            print(f"  - {table}: Error getting row count - {e}")

print("\n=== Table Details ===\n")

# Get column details for each table
for table in tables:
    print(f"\nTable: {table}")
    columns = inspector.get_columns(table)
    print(f"  Columns ({len(columns)}):")
    for col in columns:
        print(f"    - {col['name']}: {col['type']}")
    
    # Get primary key
    pk = inspector.get_pk_constraint(table)
    print(f"  Primary Key: {pk}")
    
    # Get foreign keys
    fks = inspector.get_foreign_keys(table)
    print(f"  Foreign Keys: {fks}") 