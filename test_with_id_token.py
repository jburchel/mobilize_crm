import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the Firebase ID token from environment variables
id_token = os.getenv('FIREBASE_ID_TOKEN')
if not id_token:
    print("Error: FIREBASE_ID_TOKEN environment variable not set")
    print("You need to set this with a valid Firebase ID token")
    print("This is different from a custom token - it's the token returned after signing in")
    exit(1)

print(f"Using ID token: {id_token[:20]}...")

# Base URL for the Flask application
base_url = 'http://localhost:5001'

# Create a session to maintain cookies
session = requests.Session()

# Set the token as a cookie
session.cookies.set('firebase_token', id_token)

# Also set the token in the Authorization header
headers = {
    'Authorization': f'Bearer {id_token}'
}

# Test authentication by accessing the home page
print("\n--- Testing authentication ---")
try:
    response = session.get(f"{base_url}/", headers=headers)
    print(f"Home page status code: {response.status_code}")
    print(f"Redirected to: {response.url}")
except Exception as e:
    print(f"Error accessing home page: {e}")

# Test the people endpoint
print("\n--- Testing people endpoint ---")
try:
    response = session.get(f"{base_url}/people", params={'format': 'json'}, headers=headers)
    print(f"People endpoint status code: {response.status_code}")
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