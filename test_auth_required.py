from flask import Flask, request, jsonify
from functools import wraps
from firebase_admin import auth, credentials, initialize_app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK with explicit credentials
cred = credentials.Certificate('firebase-credentials.json')
try:
    app = initialize_app(cred)
except ValueError:
    # App already initialized
    pass

# Create a Flask app
flask_app = Flask(__name__)

# Define the auth_required decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split('Bearer ')[1]
                decoded_token = auth.verify_id_token(token)
                # Add user_id to request for use in the route
                request.user_id = decoded_token['uid']
                return f(*args, **kwargs)
            except Exception as e:
                print(f"Bearer token verification failed: {str(e)}")
                return jsonify({"error": f"Bearer token verification failed: {str(e)}"}), 401

        # If no valid bearer token, check for session token
        if 'firebase_token' in request.cookies:
            try:
                decoded_token = auth.verify_id_token(request.cookies['firebase_token'])
                # Add user_id to request for use in the route
                request.user_id = decoded_token['uid']
                return f(*args, **kwargs)
            except Exception as e:
                print(f"Cookie token verification failed: {str(e)}")
                return jsonify({"error": f"Cookie token verification failed: {str(e)}"}), 401
                
        # No valid authentication found
        return jsonify({"error": "Authentication required"}), 401
            
    return decorated_function

# Define a test route
@flask_app.route('/test')
@auth_required
def test_route():
    return jsonify({
        "message": "Authentication successful",
        "user_id": request.user_id
    })

# Run the app
if __name__ == '__main__':
    flask_app.run(debug=True, port=5002) 