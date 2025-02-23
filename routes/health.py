from flask import Blueprint, jsonify
from datetime import datetime
import psutil
from models import engine
from sqlalchemy import text

health_bp = Blueprint('health_bp', __name__)

@health_bp.route('/health')
def health_check():
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': check_database(),
            'system': check_system_resources()
        }
    }
    return jsonify(health_status)

def check_database():
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return {'status': 'up', 'message': 'Database connection successful'}
    except Exception as e:
        return {'status': 'down', 'message': str(e)}

def check_system_resources():
    return {
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent
    }