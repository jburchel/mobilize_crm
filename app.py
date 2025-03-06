from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from config import get_config
from models import Base, engine
from database import db, init_db
import logging
from datetime import datetime
import sys
import firebase_admin
from firebase_admin import credentials, auth
import os
import base64
import json
import tempfile
import argparse

print("Script starting...")
print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("__name__ is:", __name__)

# Global variable to track if Firebase is initialized
firebase_initialized = False

try:
    # Create and configure the app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    
    print(f"Running in {os.environ.get('FLASK_ENV', 'production')} environment")
    
    # Enable CORS
    CORS(app, supports_credentials=True, resources={
        r"/*": {"origins": ["http://localhost:3000"], "supports_credentials": True}
    })
    
    # Initialize database
    init_db(app)
    
    # Initialize Firebase Admin SDK
    try:
        firebase_credentials_base64 = os.environ.get('FIREBASE_CREDENTIALS_BASE64')
        if firebase_credentials_base64:
            print(f"Found FIREBASE_CREDENTIALS_BASE64 environment variable, length: {len(firebase_credentials_base64)}")
            try:
                # Decode the base64 credentials
                firebase_credentials_json = base64.b64decode(firebase_credentials_base64).decode('utf-8')
                print("Successfully decoded base64 credentials")
                
                # Create a temporary file with the credentials
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                    temp_file.write(firebase_credentials_json.encode('utf-8'))
                    temp_file_path = temp_file.name
                    print(f"Created temporary credentials file at: {temp_file_path}")
                
                # Initialize Firebase with the temporary file
                cred = credentials.Certificate(temp_file_path)
                firebase_admin.initialize_app(cred)
                firebase_initialized = True
                print("Successfully initialized Firebase Admin SDK")
                
                # Clean up the temporary file
                os.unlink(temp_file_path)
                print("Cleaned up temporary credentials file")
            except Exception as e:
                print(f"Error processing Firebase credentials from environment: {e}")
                print("Falling back to file-based credentials")
                # Fall back to the file-based credentials
                try:
                    cred = credentials.Certificate('firebase-credentials.json')
                    firebase_admin.initialize_app(cred)
                    firebase_initialized = True
                except Exception as e:
                    print(f"Error initializing Firebase with file-based credentials: {e}")
        else:
            print("No FIREBASE_CREDENTIALS_BASE64 environment variable found")
            # Fall back to the file-based credentials
            try:
                cred = credentials.Certificate('firebase-credentials.json')
                firebase_admin.initialize_app(cred)
                firebase_initialized = True
            except Exception as e:
                print(f"Error initializing Firebase with file-based credentials: {e}")
    except Exception as e:
        print(f"Error during Firebase initialization: {e}")
        
    if not firebase_initialized:
        print("WARNING: Firebase was not initialized. Authentication features will not work.")
    
    # Initialize CORS with credentials support
    CORS(app, supports_credentials=True)
    
    # Import routes after app is created to avoid circular imports
    from routes.dashboard import dashboard_bp
    from routes.google_auth import google_auth_bp
    from routes.gmail_api import gmail_api
    from routes.people import people_bp
    from routes.churches import churches_bp
    from routes.tasks import tasks_bp
    from routes.communications import communications_bp
    from routes.api import api_bp
    
    # Register blueprints
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(google_auth_bp, url_prefix='/google')
    app.register_blueprint(gmail_api, url_prefix='/api/gmail')
    app.register_blueprint(people_bp, url_prefix='/people')
    app.register_blueprint(churches_bp, url_prefix='/churches')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(communications_bp, url_prefix='/communications')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Initialize background jobs
    from utils.background_jobs import init_background_jobs
    init_background_jobs(app)
    
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    @app.template_filter('now')
    def now_filter(format_string='%Y-%m-%d'):
        return datetime.now().strftime(format_string)
    
    @app.context_processor
    def utility_processor():
        def get_today():
            return datetime.now().strftime('%m/%d/%Y')
        return dict(today=get_today)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    def get_auth_token():
        # Check Authorization header first
        auth_header = request.headers.get('Authorization')
        if (auth_header and auth_header.startswith('Bearer ')):
            return auth_header.split('Bearer ')[1]
        # Then check for token in cookie/session
        return request.cookies.get('authToken')

    @app.route('/')
    def home():
        # Check if user is authenticated
        auth_header = request.headers.get('Authorization')
        token = None
        
        # Check Authorization header
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            
        # If no auth header, check cookie
        if not token:
            token = request.cookies.get('firebase_token')
            
        if token and firebase_initialized:
            try:
                decoded_token = auth.verify_id_token(token)
                app.logger.info("Valid token found, redirecting to dashboard")
                return redirect(url_for('dashboard_bp.dashboard'))
            except Exception as e:
                app.logger.warning(f"Token verification failed: {str(e)}")
                
        # If Firebase is not initialized or not authenticated or token invalid, show landing page
        return render_template('landing.html')

    if __name__ == '__main__':
        print('Entering main block...')
        
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Run the Mobilize CRM application')
        parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
        args = parser.parse_args()
        
        # Store the port in the app configuration for background jobs
        app.config['PORT'] = args.port
        
        print(f"Server starting at http://127.0.0.1:{args.port}")
        app.run(debug=True, port=args.port)
except Exception as e:
    print(f"Error during app initialization: {e}")
