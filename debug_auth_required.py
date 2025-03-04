from dotenv import load_dotenv
import os
import json
from datetime import datetime
from flask import Flask, request, redirect, url_for
from functools import wraps
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

def auth_required_debug(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("=== auth_required_debug ===")
        
        # First check Authorization header
        auth_header = request.headers.get('Authorization')
        print(f"Authorization header: {auth_header}")
        
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split('Bearer ')[1]
                print(f"Token from header: {token[:20]}...")
                
                # Verify the token
                decoded_token = auth.verify_id_token(token)
                print(f"Token verified successfully: {decoded_token}")
                
                return f(*args, **kwargs)
            except Exception as e:
                print(f"Bearer token verification failed: {str(e)}")

        # If no valid bearer token, check for session token
        if 'firebase_token' in request.cookies:
            try:
                token = request.cookies['firebase_token']
                print(f"Token from cookie: {token[:20]}...")
                
                # Verify the token
                decoded_token = auth.verify_id_token(token)
                print(f"Token verified successfully: {decoded_token}")
                
                return f(*args, **kwargs)
            except Exception as e:
                print(f"Cookie token verification failed: {str(e)}")
                
        # No valid authentication found, redirect to home
        print("No valid authentication found, redirecting to home")
        return redirect(url_for('home'))
            
    return decorated_function

def create_test_app():
    """Create a test Flask app with the auth_required_debug decorator"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "Home page"
    
    @app.route('/test')
    @auth_required_debug
    def test():
        return "Test page - You are authenticated!"
    
    return app

def main():
    """Test the auth_required_debug decorator"""
    # Create a test app
    app = create_test_app()
    
    # Run the app
    app.run(debug=True, port=5002)

if __name__ == "__main__":
    main() 