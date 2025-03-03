from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from models import Base, engine
from database import db, init_db
import logging
from datetime import datetime
import sys
import firebase_admin
from firebase_admin import credentials, auth
import os

print("Script starting...")
print("Python version:", sys.version)
print("Current working directory:", sys.path[0])
print("__name__ is:", __name__)

try:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key')
    app.config['DATABASE'] = os.environ.get('DATABASE', 'mobilize_crm.db')
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:8000')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mobilize_crm.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    init_db(app)
    
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)

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
    from utils.background_jobs import start_background_jobs

    # Register blueprints
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(people_bp)
    app.register_blueprint(churches_bp)
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(communications_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(contacts_api)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(auth_api)
    app.register_blueprint(google_auth_bp)
    app.register_blueprint(calendar_api)
    app.register_blueprint(gmail_api)
    app.register_blueprint(import_csv_bp)

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

    # Add template global for current date
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
