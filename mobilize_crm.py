from flask import Flask, render_template, request
from flask_restx import Api, Resource, fields
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_cors import CORS
from config import Config
from models import Base, engine
from routes.dashboard import dashboard_bp
from routes.people import people_bp
from routes.churches import churches_bp
from routes.tasks import tasks_bp
from routes.communications import communications_bp
from routes.health import health_bp
import firebase_admin
from firebase_admin import credentials
from functools import wraps
import logging

def create_app(config_class=Config):
    app = Flask(__name__,
        static_url_path='',
        static_folder='static')
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    app.logger.info('CORS initialized')
    
    # Initialize security headers
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Required for some inline scripts
            'https://apis.google.com',
            'https://www.gstatic.com',
            'https://www.google-analytics.com',
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Required for some inline styles
            'https://fonts.googleapis.com',
        ],
        'font-src': [
            "'self'",
            'https://fonts.gstatic.com',
        ],
        'img-src': ["'self'", 'data:', 'https:'],
        'frame-src': ["'self'", 'https://accounts.google.com'],
    }
    
    Talisman(app,
             content_security_policy=csp,
             content_security_policy_nonce_in=['script-src'],
             force_https=True,
             strict_transport_security=True,
             session_cookie_secure=True,
             session_cookie_http_only=True)
    
    app.logger.info('Security headers initialized')
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="redis://localhost:6379"
    )
    app.logger.info('Rate limiter initialized')
    
    # Initialize logging
    Config.init_logging(app)
    app.logger.info('Mobilize CRM startup')
    
    # Initialize database
    try:
        Base.metadata.create_all(engine)
        app.logger.info('Database initialized successfully')
    except Exception as e:
        app.logger.error(f'Database initialization failed: {e}')
        raise
    
    # Initialize Firebase Admin SDK
    if app.config['FIREBASE_PROJECT_ID']:
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
            app.logger.info('Firebase Admin SDK initialized successfully')
        except Exception as e:
            app.logger.error(f'Firebase Admin SDK initialization failed: {e}')
    
    # Initialize API documentation
    api = Api(app, version='1.0', title='Mobilize CRM API',
             description='API documentation for Mobilize CRM',
             doc='/api/docs')
    app.logger.info('API documentation initialized')
    
    # API models
    person_model = api.model('Person', {
        'id': fields.Integer(readonly=True),
        'name': fields.String(required=True),
        'email': fields.String(),
        'phone': fields.String(),
        'address': fields.String(),
        'role': fields.String(),
        'church_id': fields.Integer()
    })

    task_model = api.model('Task', {
        'id': fields.Integer(readonly=True),
        'title': fields.String(required=True),
        'description': fields.String(),
        'due_date': fields.Date(),
        'priority': fields.String(enum=['Low', 'Medium', 'High']),
        'status': fields.String(required=True, enum=['Not Started', 'In Progress', 'Completed']),
        'person_id': fields.Integer(),
        'church_id': fields.Integer()
    })
    
    # Register blueprints
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(people_bp, url_prefix='/people')
    app.register_blueprint(churches_bp, url_prefix='/churches')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(communications_bp, url_prefix='/communications')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.logger.info('All blueprints registered including health check')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f'Page not found: {request.url}')
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('500.html'), 500
    
    @limiter.request_filter
    def ip_whitelist():
        return request.remote_addr == "127.0.0.1"
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
