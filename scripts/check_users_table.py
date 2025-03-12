import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Load environment variables
load_dotenv()

# Get PostgreSQL connection string
pg_connection_string = os.environ.get('DB_CONNECTION_STRING')
if not pg_connection_string:
    print("❌ PostgreSQL connection string not found in environment variables")
    exit(1)

# Create engine for PostgreSQL
pg_engine = create_engine(pg_connection_string)
print("✅ Connected to PostgreSQL database")

# Get inspector
inspector = inspect(pg_engine)

# Check if users table exists
if 'users' in inspector.get_table_names():
    print("✅ Users table exists in PostgreSQL")
    
    # Get columns
    columns = inspector.get_columns('users')
    print(f"✅ Users table has {len(columns)} columns:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    # Get primary key
    pk = inspector.get_pk_constraint('users')
    print(f"✅ Primary key: {pk}")
    
    # Get foreign keys
    fks = inspector.get_foreign_keys('users')
    print(f"✅ Foreign keys: {fks}")
    
    # Get indexes
    indexes = inspector.get_indexes('users')
    print(f"✅ Indexes: {indexes}")
    
    # Get row count
    try:
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            row_count = result.scalar()
            print(f"✅ Users table has {row_count} rows")
    except Exception as e:
        print(f"❌ Error checking row count: {e}")
else:
    print("❌ Users table does not exist in PostgreSQL") 