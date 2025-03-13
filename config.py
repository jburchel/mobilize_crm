import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BaseConfig:
    """Base configuration with common settings"""
    # Flask
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_EMAIL = os.environ.get('SMTP_EMAIL')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    
    # Firebase
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')
    FIREBASE_MEASUREMENT_ID = os.environ.get('FIREBASE_MEASUREMENT_ID')

    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    LOG_FILE = 'logs/mobilize_crm.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10

    # CORS Settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # API Documentation
    SWAGGER_UI_DOC_EXPANSION = 'list'
    RESTX_MASK_SWAGGER = False
    
    # Session Configuration
    SESSION_TYPE = 'redis'
    SESSION_REDIS = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # Google OAuth2 settings
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    @staticmethod
    def init_logging(app):
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        formatter = logging.Formatter(BaseConfig.LOG_FORMAT)
        
        if BaseConfig.LOG_TO_STDOUT:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            app.logger.addHandler(stream_handler)
        else:
            file_handler = RotatingFileHandler(
                BaseConfig.LOG_FILE,
                maxBytes=BaseConfig.LOG_MAX_SIZE,
                backupCount=BaseConfig.LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(formatter)
            app.logger.addHandler(file_handler)
        
        app.logger.setLevel(getattr(logging, BaseConfig.LOG_LEVEL.upper()))


class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    DEBUG = True
    # Use absolute path to instance folder to ensure consistency
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), "instance", "mobilize_crm.db"))}'
    # Enable more detailed logging for development
    LOG_LEVEL = 'DEBUG'
    # Enable SQLAlchemy echo for query debugging
    SQLALCHEMY_ECHO = True


class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    # Check if a direct connection string is provided
    DB_CONNECTION_STRING = os.environ.get('DB_CONNECTION_STRING')
    
    if DB_CONNECTION_STRING:
        SQLALCHEMY_DATABASE_URI = DB_CONNECTION_STRING
    else:
        # Construct connection string from individual components
        DB_USER = os.environ.get('DB_USER')
        DB_PASSWORD = os.environ.get('DB_PASSWORD')
        DB_HOST = os.environ.get('DB_HOST')
        DB_PORT = os.environ.get('DB_PORT', '5432')
        DB_NAME = os.environ.get('DB_NAME')
        
        if all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
            SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        else:
            # Fallback to SQLite if no PostgreSQL configuration is provided
            SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/mobilize_crm.db'
    
    # Production-specific settings
    LOG_TO_STDOUT = True
    LOG_LEVEL = 'INFO'
    SQLALCHEMY_ECHO = False


class TestingConfig(BaseConfig):
    """Testing environment configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


def get_config():
    """Return the appropriate configuration class based on environment"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig


# For backward compatibility - this is what the app currently uses
Config = get_config()