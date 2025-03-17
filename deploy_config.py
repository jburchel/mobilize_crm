import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from dotenv import load_dotenv

class DeploymentConfig:
    ENVIRONMENTS = ['development', 'staging', 'production']
    
    REQUIRED_ENV_VARS = {
        'base': [
            'FLASK_ENV',
            'SECRET_KEY',
            'DB_CONNECTION_STRING',
            'BASE_URL',
        ],
        'google': [
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET',
            'GOOGLE_REDIRECT_URI',
        ],
        'firebase': [
            'FIREBASE_API_KEY',
            'FIREBASE_AUTH_DOMAIN',
            'FIREBASE_PROJECT_ID',
            'FIREBASE_STORAGE_BUCKET',
            'FIREBASE_MESSAGING_SENDER_ID',
            'FIREBASE_APP_ID',
            'FIREBASE_MEASUREMENT_ID',
        ]
    }

    def __init__(self, environment: str):
        if environment not in self.ENVIRONMENTS:
            raise ValueError(f"Environment must be one of {self.ENVIRONMENTS}")
        
        self.environment = environment
        load_dotenv(f".env.{environment}")
        
    def verify_env_vars(self) -> List[str]:
        """Verify all required environment variables are set."""
        missing_vars = []
        
        for category, vars in self.REQUIRED_ENV_VARS.items():
            for var in vars:
                if not os.getenv(var):
                    missing_vars.append(var)
        
        return missing_vars

    def verify_database_connection(self) -> tuple[bool, Optional[str]]:
        """Verify database connection and schema."""
        try:
            conn = psycopg2.connect(os.getenv('DB_CONNECTION_STRING'))
            cur = conn.cursor()
            
            # Check if all required tables exist
            required_tables = ['users', 'churches', 'communications', 'tasks']
            for table in required_tables:
                cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                if not cur.fetchone()[0]:
                    return False, f"Missing required table: {table}"
            
            # Verify communications table schema
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'communications'
            """)
            columns = {row[0]: row[1] for row in cur.fetchall()}
            
            required_columns = {
                'id': 'integer',
                'date_sent': 'timestamp',
                'type': 'character varying',
                'message': 'text'
            }
            
            for col, dtype in required_columns.items():
                if col not in columns:
                    return False, f"Missing required column in communications table: {col}"
                if not columns[col].startswith(dtype):
                    return False, f"Incorrect data type for {col}: expected {dtype}, got {columns[col]}"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
        finally:
            if 'conn' in locals():
                conn.close()

    def get_environment_urls(self) -> Dict[str, str]:
        """Get URLs for different environments."""
        return {
            'development': 'http://localhost:5000',
            'staging': 'https://staging.mobilize-crm.org',
            'production': 'https://mobilize-crm.org'
        }

    def verify_routes(self) -> tuple[bool, Optional[str]]:
        """Verify all routes are properly configured."""
        try:
            # Import the Flask app without running it
            from app import app
            
            # Get all registered routes
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append(rule.endpoint)
            
            # Required routes to check
            required_routes = [
                'main.index',
                'auth.login',
                'churches_bp.list_churches',
                'people_bp.list_people',
                'tasks_bp.tasks',
                'communications_bp.communications_route'
            ]
            
            for route in required_routes:
                if route not in routes:
                    return False, f"Missing required route: {route}"
            
            return True, None
            
        except Exception as e:
            return False, str(e)

    def backup_database(self) -> tuple[bool, Optional[str]]:
        """Create a database backup before deployment."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"backup_{self.environment}_{timestamp}.sql"
            
            # Execute pg_dump
            os.system(f"pg_dump {os.getenv('DB_CONNECTION_STRING')} > {backup_file}")
            
            return True, backup_file
        except Exception as e:
            return False, str(e)

    def run_migrations(self, dry_run: bool = True) -> tuple[bool, Optional[str]]:
        """Run database migrations."""
        try:
            command = "flask db upgrade" if not dry_run else "flask db upgrade --sql"
            result = os.system(command)
            
            if result != 0:
                return False, "Migration failed"
            
            return True, None
        except Exception as e:
            return False, str(e) 