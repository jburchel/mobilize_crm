import requests
import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import auth, credentials

# Load environment variables
load_dotenv()

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)

# Get user ID from environment variable or use default
user_id = os.getenv('FIREBASE_USER_ID', 'CVjBoi6rGMazZ3J6vAAtu1hra4H2')
print(f"Using Firebase User ID: {user_id}")

# Generate a custom token for the user
custom_token = auth.create_custom_token(user_id).decode('utf-8')
print(f"Generated custom token: {custom_token[:20]}...")

# Exchange custom token for ID token
response = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={os.getenv('FIREBASE_API_KEY')}",
    json={"token": custom_token, "returnSecureToken": True}
)
id_token = response.json()['idToken']
print(f"Received ID token: {id_token[:20]}...")

# Make request to churches endpoint with JSON format
url = "http://localhost:5001/churches?format=json"
headers = {"Authorization": f"Bearer {id_token}"}

print(f"Making request to: {url}")
print(f"Headers: {headers}")

response = requests.get(url, headers=headers)

print(f"Response status code: {response.status_code}")
print(f"Response headers: {response.headers}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"Found {data['count']} churches")
        if data['count'] > 0:
            print("First few churches:")
            for church in data['churches'][:3]:  # Show first 3 churches
                print(f"  - {church['church_name']} ({church['id']})")
    except json.JSONDecodeError:
        print("Response is not valid JSON:")
        print(response.text[:500])  # Print first 500 chars of response
else:
    print(f"Error response: {response.text[:200]}") 