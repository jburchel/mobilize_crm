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

print("Script starting...")
print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("__name__ is:", __name__)

try:
    # Get the appropriate configuration based on environment
    config_class = get_config()
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Print environment info
    env = os.environ.get('FLASK_ENV', 'development')
    print(f"Running in {env} environment")
    print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
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

    # Initialize CORS with credentials support
    CORS(app, supports_credentials=True)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Import blueprints after app is created to avoid circular imports
    from routes.dashboard import dashboard_bp
    from routes.people import people_bp
    from routes.churches import churches_bp
    from routes.tasks import tasks_bp
    from routes.communications import communications_bp
    from routes.health import health_bp
    from routes.contacts_api import contacts_api
    from routes.contacts import contacts_bp
    from routes.auth_api import auth_api
    from routes.google_auth import google_auth_bp
    from routes.calendar_api import calendar_api
    from routes.gmail_api import gmail_api
    from routes.import_csv import import_csv_bp
    from routes.offices_admin import offices_admin_bp
    from utils.background_jobs import start_background_jobs

    # Register blueprints
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(people_bp, url_prefix='/people')
    app.register_blueprint(churches_bp, url_prefix='/churches')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(communications_bp, url_prefix='/communications')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(contacts_api, url_prefix='/api/contacts')
    app.register_blueprint(contacts_bp, url_prefix='/contacts')
    app.register_blueprint(auth_api, url_prefix='/api/auth')
    app.register_blueprint(google_auth_bp, url_prefix='/google')
    app.register_blueprint(calendar_api, url_prefix='/api/calendar')
    app.register_blueprint(gmail_api, url_prefix='/api/gmail')
    app.register_blueprint(import_csv_bp, url_prefix='/import')
    app.register_blueprint(offices_admin_bp, url_prefix='/admin')

    # Initialize Flask-Migrate
    migrate = Migrate(app, Base)

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Start background jobs
    with app.app_context():
        start_background_jobs(app=app)

    # Add template filter for the {% now %} tag
    @app.template_filter('now')
    def now_filter(format_string='%Y-%m-%d'):
        return datetime.now().strftime(format_string)

    # Add nl2br filter to convert newlines to <br> tags
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        if text:
            return text.replace('\n', '<br>')
        return text

    # Add template global for current date
    @app.context_processor
    def utility_processor():
        def get_today():
            return datetime.now().strftime('%Y-%m-%d')
        return dict(get_today=get_today)
    
    @app.context_processor
    def inject_user_offices():
        """Inject user_offices into all templates."""
        def get_user_offices():
            # For now, return a simple list with hardcoded values to ensure the admin panel shows up
            return [
                {
                    'office': {'name': 'USA Office', 'id': 1},
                    'role': 'super_admin',
                    'office_id': 1
                }
            ]
        
        return dict(user_offices=get_user_offices())

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
            
        if token:
            try:
                decoded_token = auth.verify_id_token(token)
                app.logger.info("Valid token found, redirecting to dashboard")
                return redirect(url_for('dashboard_bp.dashboard'))
            except Exception as e:
                app.logger.warning(f"Token verification failed: {str(e)}")
                
        # If not authenticated or token invalid, show landing page
        return render_template('landing.html')

    if __name__ == '__main__':
        print('Entering main block...')
        print("Server starting at http://127.0.0.1:8000")
        app.run(debug=True, port=8000)
except Exception as e:
    print(f"Error during app initialization: {e}")
