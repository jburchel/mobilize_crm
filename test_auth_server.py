import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the ID token from environment variables
id_token = os.getenv('FIREBASE_ID_TOKEN')
if not id_token:
    print("Error: FIREBASE_ID_TOKEN environment variable not set")
    exit(1)

print(f"Using ID token: {id_token[:20]}...")

# Make a request to the test endpoint with the token in the header
headers = {
    'Authorization': f'Bearer {id_token}'
}

# Test the auth server
response = requests.get('http://localhost:5002/test', headers=headers)
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")

# Test with cookie
cookies = {
    'firebase_token': id_token
}
response_cookie = requests.get('http://localhost:5002/test', cookies=cookies)
print(f"\nStatus code with cookie: {response_cookie.status_code}")
print(f"Response with cookie: {response_cookie.text}") 