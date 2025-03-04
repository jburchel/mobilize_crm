import firebase_admin
from firebase_admin import credentials, auth
import os
from dotenv import load_dotenv
import requests
import json

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

# Generate a custom token
custom_token = auth.create_custom_token(user_id).decode('utf-8')
print(f"Generated custom token: {custom_token[:20]}...")

# Exchange custom token for ID token using Firebase Auth REST API
api_key = os.getenv('FIREBASE_API_KEY')
if not api_key:
    print("Error: FIREBASE_API_KEY environment variable not set")
    print("Please set this variable with your Firebase Web API Key")
    exit(1)

url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
payload = {
    "token": custom_token,
    "returnSecureToken": True
}

try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        id_token = response.json().get('idToken')
        print(f"Successfully obtained ID token: {id_token[:20]}...")
        print("\nAdd this to your .env file:")
        print(f"FIREBASE_ID_TOKEN={id_token}")
    else:
        print(f"Error exchanging custom token for ID token: {response.text}")
except Exception as e:
    print(f"Error: {str(e)}") 