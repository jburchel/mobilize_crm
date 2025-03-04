import requests
import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK if not already initialized
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)

# Get a custom token for the test user
user_id = os.getenv('FIREBASE_USER_ID', 'CVjBoi6rGMazZ3J6vAAtu1hra4H2')
custom_token = auth.create_custom_token(user_id).decode('utf-8')

# Make a request to the people endpoint with the JSON format parameter
base_url = 'http://localhost:5001'
endpoint = '/people'
params = {'format': 'json'}

# Create a session to maintain cookies
session = requests.Session()

# Set the token as a cookie
session.cookies.set('firebase_token', custom_token)

# Also set the token in the Authorization header as a backup
headers = {
    'Authorization': f'Bearer {custom_token}'
}

try:
    # First, make a request to the home page to set up the session
    session.get(f"{base_url}/")
    
    # Then make the request to the people endpoint
    response = session.get(f"{base_url}{endpoint}", params=params, headers=headers)
    
    # Print the response status and content
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"Response content (first 200 chars): {response.text[:200]}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Total people found: {data.get('count', 0)}")
            
            # Print the first few people
            people = data.get('people', [])
            if people:
                print("\nFirst few people:")
                for i, person in enumerate(people[:5]):  # Show up to 5 people
                    print(f"{i+1}. {person.get('first_name', '')} {person.get('last_name', '')} (ID: {person.get('id', '')})")
            else:
                print("No people found in the response.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    else:
        print(f"Error response: {response.text}")
except Exception as e:
    print(f"Error making request: {e}") 