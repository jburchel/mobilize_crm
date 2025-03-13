import os
import sys
import requests
from bs4 import BeautifulSoup
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import json
import getpass
import time

# Load environment variables
load_dotenv()

class WebDisplayChecker:
    def __init__(self, base_url, db_uri):
        self.base_url = base_url
        self.db_uri = db_uri
        self.session = requests.Session()
        self.engine = create_engine(db_uri)
        self.authenticated = False
    
    def login(self, email=None, password=None):
        """Log in to the application"""
        if not email:
            email = input("Enter your email: ")
        if not password:
            password = getpass.getpass("Enter your password: ")
        
        login_url = f"{self.base_url}/login"
        
        try:
            # First get the login page to get any CSRF token
            response = self.session.get(login_url)
            
            # Extract CSRF token if it exists
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            # Prepare login data
            login_data = {
                'email': email,
                'password': password
            }
            
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            # Submit login form
            response = self.session.post(login_url, data=login_data, allow_redirects=True)
            
            # Check if login was successful
            if response.url != login_url and "dashboard" in response.url:
                print("✅ Successfully logged in")
                self.authenticated = True
                return True
            else:
                print("❌ Login failed")
                return False
        
        except Exception as e:
            print(f"❌ Error during login: {str(e)}")
            return False
    
    def check_page_content(self, endpoint, expected_content=None):
        """Check if a page contains expected content"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url)
            
            if response.status_code != 200:
                print(f"❌ Failed to access {url} - Status code: {response.status_code}")
                return False, None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for expected content if provided
            if expected_content:
                for content in expected_content:
                    if content not in response.text:
                        print(f"❌ Expected content '{content}' not found on {url}")
                        return False, soup
            
            print(f"✅ Successfully accessed {url}")
            return True, soup
        
        except Exception as e:
            print(f"❌ Error accessing {url}: {str(e)}")
            return False, None
    
    def get_database_records(self, query, params=None):
        """Get records from the database"""
        try:
            with self.engine.connect() as connection:
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))
                
                # Convert result rows to dictionaries
                records = []
                for row in result:
                    # Use _mapping attribute to convert row to dict
                    records.append(dict(row._mapping))
                
                return records
        
        except Exception as e:
            print(f"❌ Error executing database query: {str(e)}")
            return []
    
    def check_people_display(self):
        """Check if people data is properly displayed"""
        print("\n=== Checking People Display ===\n")
        
        # Get people data from database
        db_people = self.get_database_records("""
            SELECT p.id, c.first_name, c.last_name, c.email, c.phone
            FROM people p
            JOIN contacts c ON p.id = c.id
            WHERE c.type = 'person'
            LIMIT 10
        """)
        
        if not db_people:
            print("❌ No people data found in database")
            return False
        
        # Check people list page
        success, soup = self.check_page_content('/people')
        
        if not success or not soup:
            return False
        
        # Check if people from database appear on the page
        found_count = 0
        for person in db_people:
            full_name = f"{person['first_name']} {person['last_name']}"
            
            # Look for the person's name in the page
            if full_name in soup.text:
                found_count += 1
                print(f"✅ Found person in web page: {full_name}")
            else:
                print(f"❌ Person not found in web page: {full_name}")
        
        # Calculate percentage of people found
        percentage = (found_count / len(db_people)) * 100 if db_people else 0
        print(f"\nFound {found_count} out of {len(db_people)} people ({percentage:.2f}%)")
        
        return percentage >= 50  # Consider successful if at least 50% of people are found
    
    def check_churches_display(self):
        """Check if church data is properly displayed"""
        print("\n=== Checking Churches Display ===\n")
        
        # Get church data from database
        db_churches = self.get_database_records("""
            SELECT ch.id, c.church_name, c.email, c.phone
            FROM churches ch
            JOIN contacts c ON ch.id = c.id
            WHERE c.type = 'church'
            LIMIT 10
        """)
        
        if not db_churches:
            print("❌ No church data found in database")
            return False
        
        # Check churches list page
        success, soup = self.check_page_content('/churches')
        
        if not success or not soup:
            return False
        
        # Check if churches from database appear on the page
        found_count = 0
        for church in db_churches:
            church_name = church['church_name']
            
            # Look for the church name in the page
            if church_name in soup.text:
                found_count += 1
                print(f"✅ Found church in web page: {church_name}")
            else:
                print(f"❌ Church not found in web page: {church_name}")
        
        # Calculate percentage of churches found
        percentage = (found_count / len(db_churches)) * 100 if db_churches else 0
        print(f"\nFound {found_count} out of {len(db_churches)} churches ({percentage:.2f}%)")
        
        return percentage >= 50  # Consider successful if at least 50% of churches are found
    
    def check_individual_record_display(self, record_type, record_id):
        """Check if an individual record is properly displayed"""
        print(f"\n=== Checking {record_type.capitalize()} Record Display (ID: {record_id}) ===\n")
        
        # Get record data from database
        if record_type == 'person':
            query = """
                SELECT p.id, c.first_name, c.last_name, c.email, c.phone
                FROM people p
                JOIN contacts c ON p.id = c.id
                WHERE p.id = :id AND c.type = 'person'
            """
            # Correct endpoint for person detail
            endpoint = f"/people/{record_id}"
        else:  # church
            query = """
                SELECT ch.id, c.church_name, c.email, c.phone
                FROM churches ch
                JOIN contacts c ON ch.id = c.id
                WHERE ch.id = :id AND c.type = 'church'
            """
            # Correct endpoint for church detail
            endpoint = f"/churches/{record_id}"
        
        db_record = self.get_database_records(query, {'id': record_id})
        
        if not db_record:
            print(f"❌ No {record_type} record found in database with ID {record_id}")
            return False
        
        # Check record detail page
        success, soup = self.check_page_content(endpoint)
        
        if not success or not soup:
            return False
        
        # Check if record details appear on the page
        record = db_record[0]
        found_fields = 0
        total_fields = 0
        
        for field, value in record.items():
            if field == 'id':
                continue
            
            if value:
                total_fields += 1
                if str(value) in soup.text:
                    found_fields += 1
                    print(f"✅ Found field in web page: {field} = {value}")
                else:
                    print(f"❌ Field not found in web page: {field} = {value}")
        
        # Calculate percentage of fields found
        percentage = (found_fields / total_fields) * 100 if total_fields else 100
        print(f"\nFound {found_fields} out of {total_fields} fields ({percentage:.2f}%)")
        
        return percentage >= 50  # Consider successful if at least 50% of fields are found

def main():
    # Check if we're verifying local or production
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'production':
        # Production environment
        db_uri = os.environ.get('DB_CONNECTION_STRING')
        base_url = os.environ.get('PRODUCTION_URL', 'https://your-production-url.com')
        environment = "PRODUCTION"
    else:
        # Local environment
        db_uri = 'sqlite:///instance/mobilize_crm.db'
        base_url = 'http://localhost:8000'
        environment = "LOCAL"
    
    print(f"\n=== Checking Web Display in {environment} Environment ===\n")
    
    # Create checker instance
    checker = WebDisplayChecker(base_url, db_uri)
    
    # Login if needed
    if len(sys.argv) > 2 and sys.argv[2].lower() == 'login':
        if not checker.login():
            print("Login failed. Exiting.")
            return
    
    # Check people display
    people_success = checker.check_people_display()
    
    # Check churches display
    churches_success = checker.check_churches_display()
    
    # Check individual records if IDs are provided
    person_id = None
    church_id = None
    
    # Get a person ID from the database if not provided
    if not person_id:
        person_records = checker.get_database_records("""
            SELECT p.id FROM people p
            JOIN contacts c ON p.id = c.id
            WHERE c.type = 'person'
            LIMIT 1
        """)
        if person_records:
            person_id = person_records[0]['id']
    
    # Get a church ID from the database if not provided
    if not church_id:
        church_records = checker.get_database_records("""
            SELECT ch.id FROM churches ch
            JOIN contacts c ON ch.id = c.id
            WHERE c.type = 'church'
            LIMIT 1
        """)
        if church_records:
            church_id = church_records[0]['id']
    
    # Check individual person record
    person_record_success = False
    if person_id:
        person_record_success = checker.check_individual_record_display('person', person_id)
    
    # Check individual church record
    church_record_success = False
    if church_id:
        church_record_success = checker.check_individual_record_display('church', church_id)
    
    # Print summary
    print("\n=== Summary ===\n")
    print(f"Environment: {environment}")
    print(f"People List Display: {'✅ Success' if people_success else '❌ Failed'}")
    print(f"Churches List Display: {'✅ Success' if churches_success else '❌ Failed'}")
    
    if person_id:
        print(f"Individual Person Display: {'✅ Success' if person_record_success else '❌ Failed'}")
    
    if church_id:
        print(f"Individual Church Display: {'✅ Success' if church_record_success else '❌ Failed'}")
    
    # Overall assessment
    overall_success = people_success and churches_success
    if person_id:
        overall_success = overall_success and person_record_success
    if church_id:
        overall_success = overall_success and church_record_success
    
    print(f"\nOverall Assessment: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
    
    if not overall_success:
        print("\nRecommendations:")
        if not people_success:
            print("- Check the people route and template for issues")
        if not churches_success:
            print("- Check the churches route and template for issues")
        if person_id and not person_record_success:
            print("- Check the individual person detail route and template")
        if church_id and not church_record_success:
            print("- Check the individual church detail route and template")

if __name__ == "__main__":
    main() 