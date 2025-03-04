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

def get_custom_token(uid):
    """Generate a custom token for the specified user ID"""
    try:
        custom_token = auth.create_custom_token(uid).decode('utf-8')
        return custom_token
    except Exception as e:
        print(f"Error creating custom token: {e}")
        return None

def main():
    # Use the user ID we found in the database
    user_id = "CVjBoi6rGMazZ3J6vAAtu1hra4H2"
    print(f"Using user_id: {user_id}")
    
    # Generate a custom token
    custom_token = get_custom_token(user_id)
    if not custom_token:
        return
    
    print(f"Generated custom token: {custom_token[:20]}...")
    
    # Make a request to the people endpoint with the token
    url = "http://localhost:5001/people?format=json"
    headers = {
        "Authorization": f"Bearer {custom_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Raw response: {response.text}")
        
        if response.status_code == 200 and response.text:
            try:
                data = response.json()
                print(f"People count: {data.get('count', 0)}")
                print("First few people:")
                for person in data.get('people', [])[:5]:
                    print(f"  - {person.get('first_name', '')} {person.get('last_name', '')}")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
        else:
            print("No content in response or non-200 status code")
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    main() 