import os
import sys
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def check_production_database():
    """Check if the production database is working"""
    print("\n=== Checking Production Database ===\n")
    
    # Get production database URI
    db_uri = os.environ.get('DB_CONNECTION_STRING')
    if not db_uri:
        print("❌ Production database URI not found in environment variables")
        return False
    
    try:
        # Connect to the database
        engine = create_engine(db_uri)
        connection = engine.connect()
        
        # Check if tables exist
        tables = ['people', 'churches', 'contacts', 'communications', 'tasks', 'offices']
        for table in tables:
            result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"✅ {table}: {count} records")
        
        connection.close()
        return True
    except Exception as e:
        print(f"❌ Error connecting to production database: {str(e)}")
        return False

def check_production_api():
    """Check if the production API is working"""
    print("\n=== Checking Production API ===\n")
    
    # Get production URL
    production_url = os.environ.get('PRODUCTION_URL')
    if not production_url:
        print("❌ Production URL not found in environment variables")
        return False
    
    try:
        # Check health endpoint
        response = requests.get(f"{production_url}/health")
        if response.status_code == 200:
            print(f"✅ Health endpoint: {response.status_code}")
        else:
            print(f"❌ Health endpoint: {response.status_code}")
            return False
        
        # Check API endpoints
        endpoints = [
            '/api/churches',
            '/api/people'
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{production_url}{endpoint}")
            if response.status_code == 200:
                print(f"✅ {endpoint}: {response.status_code}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Error checking production API: {str(e)}")
        return False

def check_production_web():
    """Check if the production web application is working"""
    print("\n=== Checking Production Web Application ===\n")
    
    # Get production URL
    production_url = os.environ.get('PRODUCTION_URL')
    if not production_url:
        print("❌ Production URL not found in environment variables")
        return False
    
    try:
        # Check web endpoints
        endpoints = [
            '/',
            '/login',
            '/dashboard',
            '/people',
            '/churches'
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{production_url}{endpoint}")
            if response.status_code == 200:
                print(f"✅ {endpoint}: {response.status_code}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Error checking production web application: {str(e)}")
        return False

def main():
    print("\n=== Production Verification Tool ===\n")
    
    # Check if PRODUCTION_URL is set
    production_url = os.environ.get('PRODUCTION_URL')
    if not production_url:
        print("❌ PRODUCTION_URL environment variable not set")
        print("Please set PRODUCTION_URL to the URL of your production environment")
        return
    
    # Check production database
    db_success = check_production_database()
    
    # Check production API
    api_success = check_production_api()
    
    # Check production web application
    web_success = check_production_web()
    
    # Print summary
    print("\n=== Summary ===\n")
    print(f"Production Database: {'✅ Success' if db_success else '❌ Failed'}")
    print(f"Production API: {'✅ Success' if api_success else '❌ Failed'}")
    print(f"Production Web Application: {'✅ Success' if web_success else '❌ Failed'}")
    
    # Overall assessment
    overall_success = db_success and api_success and web_success
    print(f"\nOverall Assessment: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
    
    # Recommendations
    if not overall_success:
        print("\nRecommendations:")
        if not db_success:
            print("- Check the production database connection")
        if not api_success:
            print("- Check the production API endpoints")
        if not web_success:
            print("- Check the production web application")

if __name__ == "__main__":
    main() 