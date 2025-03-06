from flask import Blueprint, jsonify

# Create a blueprint for API routes
api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/status')
def status():
    """Return the API status"""
    return jsonify({
        'status': 'ok',
        'message': 'API is running'
    }) 