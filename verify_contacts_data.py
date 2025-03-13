import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_database_connection(db_uri):
    """Check if the database connection is working"""
    try:
        engine = create_engine(db_uri)
        connection = engine.connect()
        connection.close()
        print(f"✅ Successfully connected to database: {db_uri}")
        return engine
    except Exception as e:
        print(f"❌ Failed to connect to database: {db_uri}")
        print(f"Error: {str(e)}")
        return None

def count_records(engine, table_name):
    """Count the number of records in a table"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"✅ {table_name}: {count} records")
            return count
    except Exception as e:
        print(f"❌ Failed to count records in {table_name}")
        print(f"Error: {str(e)}")
        return 0

def check_contacts_data(engine):
    """Check if contacts data exists and can be accessed"""
    try:
        with engine.connect() as connection:
            # Check people data
            people_result = connection.execute(text("""
                SELECT p.id, c.first_name, c.last_name, c.email, c.phone
                FROM people p
                JOIN contacts c ON p.id = c.id
                WHERE c.type = 'person'
                LIMIT 5
            """))
            people_data = [dict(row._mapping) for row in people_result]
            
            if people_data:
                print(f"✅ Successfully retrieved people data:")
                for person in people_data:
                    print(f"   - ID: {person['id']}, Name: {person['first_name']} {person['last_name']}, Email: {person['email']}")
            else:
                print("❌ No people data found")
            
            # Check church data
            church_result = connection.execute(text("""
                SELECT ch.id, c.church_name, c.email, c.phone
                FROM churches ch
                JOIN contacts c ON ch.id = c.id
                WHERE c.type = 'church'
                LIMIT 5
            """))
            church_data = [dict(row._mapping) for row in church_result]
            
            if church_data:
                print(f"✅ Successfully retrieved church data:")
                for church in church_data:
                    print(f"   - ID: {church['id']}, Name: {church['church_name']}, Email: {church['email']}")
            else:
                print("❌ No church data found")
            
            return people_data, church_data
    except Exception as e:
        print(f"❌ Failed to check contacts data")
        print(f"Error: {str(e)}")
        return [], []

def check_web_endpoints(base_url, endpoints):
    """Check if web endpoints are accessible"""
    results = {}
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ Successfully accessed {url}")
                results[endpoint] = True
            else:
                print(f"❌ Failed to access {url} - Status code: {response.status_code}")
                results[endpoint] = False
        except Exception as e:
            print(f"❌ Failed to access {url}")
            print(f"Error: {str(e)}")
            results[endpoint] = False
    
    return results

def main():
    # Check if we're verifying local or production
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'production':
        # Production database
        db_uri = os.environ.get('DB_CONNECTION_STRING')
        base_url = os.environ.get('PRODUCTION_URL', 'https://your-production-url.com')
        environment = "PRODUCTION"
    else:
        # Local database
        db_uri = 'sqlite:///instance/mobilize_crm.db'
        base_url = 'http://localhost:8000'
        environment = "LOCAL"
    
    print(f"\n=== Verifying {environment} Environment ===\n")
    
    # Check database connection
    engine = check_database_connection(db_uri)
    if not engine:
        print("Database connection failed. Exiting.")
        return
    
    print("\n=== Counting Records ===\n")
    
    # Count records in main tables
    people_count = count_records(engine, 'people')
    churches_count = count_records(engine, 'churches')
    contacts_count = count_records(engine, 'contacts')
    communications_count = count_records(engine, 'communications')
    tasks_count = count_records(engine, 'tasks')
    
    print("\n=== Checking Contacts Data ===\n")
    
    # Check contacts data
    people_data, church_data = check_contacts_data(engine)
    
    print("\n=== Summary ===\n")
    print(f"Environment: {environment}")
    print(f"People: {people_count}")
    print(f"Churches: {churches_count}")
    print(f"Contacts: {contacts_count}")
    print(f"Communications: {communications_count}")
    print(f"Tasks: {tasks_count}")
    
    # Only check web endpoints if requested
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'check-web':
        print("\n=== Checking Web Endpoints ===\n")
        
        # Define endpoints to check
        endpoints = [
            '/dashboard',
            '/people',
            '/churches',
            '/tasks',
            '/communications'
        ]
        
        # Check web endpoints
        endpoint_results = check_web_endpoints(base_url, endpoints)
        
        print("\n=== Web Endpoints Summary ===\n")
        for endpoint, success in endpoint_results.items():
            status = "✅ Accessible" if success else "❌ Not accessible"
            print(f"{endpoint}: {status}")

if __name__ == "__main__":
    main() 