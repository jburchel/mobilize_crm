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

# User ID to generate token for
user_id = os.getenv('FIREBASE_USER_ID', 'CVjBoi6rGMazZ3J6vAAtu1hra4H2')
print(f"Using user_id: {user_id}")

# For testing purposes, we'll use a hardcoded ID token
# In a real application, this would be obtained from Firebase Authentication
id_token = os.getenv('FIREBASE_ID_TOKEN')

if not id_token:
    print("Error: FIREBASE_ID_TOKEN environment variable not set")
    print("Please set this variable with a valid Firebase ID token")
    exit(1)

print(f"Using ID token: {id_token[:20]}...")

# Make a request to the people endpoint with the token in the header
headers = {
    'Authorization': f'Bearer {id_token}'
}

# Test the main Flask application people page with JSON format
response = requests.get('http://localhost:5001/people?format=json', headers=headers)
print(f"Status code: {response.status_code}")

# Pretty print the JSON response
if response.status_code == 200:
    try:
        json_response = response.json()
        print(f"People count: {json_response.get('count', 0)}")
        print("First few people:")
        for person in json_response.get('people', [])[:5]:  # Show first 5 people
            print(f"  - {person.get('first_name')} {person.get('last_name')} (ID: {person.get('id')}, User ID: {person.get('user_id')})")
    except json.JSONDecodeError:
        print("Response is not valid JSON")
        print(f"Response text: {response.text[:200]}...")  # Print first 200 chars
else:
    print(f"Error response: {response.text[:200]}...")  # Print first 200 chars

# Test with cookie
cookies = {
    'firebase_token': id_token
}
response_cookie = requests.get('http://localhost:5001/people?format=json', cookies=cookies)
print(f"\nStatus code with cookie: {response_cookie.status_code}")

# Pretty print the JSON response for cookie-based auth
if response_cookie.status_code == 200:
    try:
        json_response = response_cookie.json()
        print(f"People count (cookie auth): {json_response.get('count', 0)}")
        print("First few people (cookie auth):")
        for person in json_response.get('people', [])[:5]:  # Show first 5 people
            print(f"  - {person.get('first_name')} {person.get('last_name')} (ID: {person.get('id')}, User ID: {person.get('user_id')})")
    except json.JSONDecodeError:
        print("Response is not valid JSON")
        print(f"Response text: {response_cookie.text[:200]}...")  # Print first 200 chars
else:
    print(f"Error response: {response_cookie.text[:200]}...")