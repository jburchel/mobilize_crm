#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth
import tempfile
import base64
import json

# Load environment variables
load_dotenv()

# Print environment info
env = os.environ.get('FLASK_ENV', 'development')
print(f"Running in {env} environment")
db_uri = os.environ.get('DB_CONNECTION_STRING')
print(f"Database URI: {db_uri}")

# Initialize Firebase Admin SDK
try:
    firebase_credentials_base64 = os.environ.get('FIREBASE_CREDENTIALS_BASE64')
    if firebase_credentials_base64:
        print(f"Found FIREBASE_CREDENTIALS_BASE64 environment variable")
        try:
            # Decode the base64 credentials
            firebase_credentials_json = base64.b64decode(firebase_credentials_base64).decode('utf-8')
            print("Successfully decoded base64 credentials")
            
            # Create a temporary file with the credentials
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                temp_file.write(firebase_credentials_json.encode('utf-8'))
                temp_file_path = temp_file.name
                print(f"Created temporary credentials file")
            
            # Initialize Firebase with the temporary file
            cred = credentials.Certificate(temp_file_path)
            firebase_admin.initialize_app(cred)
            print("Successfully initialized Firebase Admin SDK")
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            print("Cleaned up temporary credentials file")
        except Exception as e:
            print(f"Error processing Firebase credentials from environment: {e}")
            print("Falling back to file-based credentials")
            # Fall back to the file-based credentials
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
    else:
        print("No FIREBASE_CREDENTIALS_BASE64 environment variable found")
        # Fall back to the file-based credentials
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Error during Firebase initialization: {e}")
    raise

# List all Firebase users
try:
    print("Fetching Firebase users...")
    # Get the first 100 users
    users = auth.list_users().iterate_all()
    user_list = []
    
    for user in users:
        user_list.append({
            'uid': user.uid,
            'email': user.email,
            'display_name': user.display_name
        })
    
    print(f"Found {len(user_list)} Firebase users:")
    for user in user_list:
        print(f"UID: {user['uid']}, Email: {user['email']}, Name: {user['display_name']}")
    
    # Check if the user ID we're using in our queries exists
    target_uid = 'CVjBoi6rGMazZ3J6vAAtu1hra4H2'
    found = False
    for user in user_list:
        if user['uid'] == target_uid:
            found = True
            print(f"\nTarget user found: {user}")
            break
    
    if not found:
        print(f"\nWARNING: Target user ID '{target_uid}' not found in Firebase users!")
        
except Exception as e:
    print(f"Error fetching Firebase users: {e}") 