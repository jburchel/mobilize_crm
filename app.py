from flask import Flask, render_template
from flask_cors import CORS
from config import Config
from models import Base, engine
from routes.dashboard import dashboard_bp
from routes.people import people_bp
from routes.churches import churches_bp
from routes.tasks import tasks_bp
from routes.communications import communications_bp
from routes.health import health_bp
from routes.contacts_api import contacts_api
from routes.contacts import contacts_bp
from routes.auth_api import auth_api  # Add new import
import logging
from datetime import datetime
import sys
import firebase_admin
from firebase_admin import credentials

print("Script starting...")
print("Python version:", sys.version)
print("Current working directory:", sys.path[0])
print("__name__ is:", __name__)

try:
    app = Flask(__name__)
    app.config['DEBUG'] = True
    
    # Initialize Firebase Admin SDK
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)

    # Initialize CORS
    CORS(app)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(churches_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(communications_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(contacts_api)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(auth_api)  # Register new blueprint

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Add template filter for the {% now %} tag
    @app.template_filter('now')
    def now_filter(format_string):
        return datetime.now().strftime(format_string)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    @app.route('/')
    def home():
        return render_template('base.html')

    if __name__ == '__main__':
        print("Entering main block...")
        try:
            print("Server starting at http://127.0.0.1:5000")
            app.run(debug=True, host='127.0.0.1', port=5000)
        except Exception as e:
            print(f"Error in main block: {e}")
            raise
    else:
        print("Warning: Script was imported, not run directly")
except Exception as e:
    print("Error starting the application:", str(e))
    raise
