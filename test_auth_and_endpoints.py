import requests
import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth
import time

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

print(f"Generated custom token for user ID: {user_id}")
print(f"Token: {custom_token[:20]}...")

# Base URL for the Flask application
base_url = 'http://localhost:5001'

# Create a session to maintain cookies
session = requests.Session()

# Set the token as a cookie
session.cookies.set('firebase_token', custom_token)

# Also set the token in the Authorization header
headers = {
    'Authorization': f'Bearer {custom_token}'
}

# Test authentication by accessing the home page
print("\n--- Testing authentication ---")
try:
    response = session.get(f"{base_url}/", headers=headers)
    print(f"Home page status code: {response.status_code}")
    print(f"Redirected to: {response.url}")
except Exception as e:
    print(f"Error accessing home page: {e}")

# Wait a moment for any redirects to complete
time.sleep(1)

# Test the people endpoint
print("\n--- Testing people endpoint ---")
try:
    response = session.get(f"{base_url}/people", params={'format': 'json'}, headers=headers)
    print(f"People endpoint status code: {response.status_code}")
    
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
            print(f"Response content (first 200 chars): {response.text[:200]}")
    else:
        print(f"Error response: {response.text[:200]}")
except Exception as e:
    print(f"Error accessing people endpoint: {e}")

# Test the churches endpoint
print("\n--- Testing churches endpoint ---")
try:
    response = session.get(f"{base_url}/churches", params={'format': 'json'}, headers=headers)
    print(f"Churches endpoint status code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Total churches found: {data.get('count', 0)}")
            
            # Print the first few churches
            churches = data.get('churches', [])
            if churches:
                print("\nFirst few churches:")
                for i, church in enumerate(churches[:5]):  # Show up to 5 churches
                    print(f"{i+1}. {church.get('church_name', '')} (ID: {church.get('id', '')})")
                    print(f"   Location: {church.get('city', '')}, {church.get('state', '')}, {church.get('country', '')}")
                    print(f"   Pipeline: {church.get('pipeline', '')}")
            else:
                print("No churches found in the response.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print(f"Response content (first 200 chars): {response.text[:200]}")
    else:
        print(f"Error response: {response.text[:200]}")
except Exception as e:
    print(f"Error accessing churches endpoint: {e}") 