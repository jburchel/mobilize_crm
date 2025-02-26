from flask import Blueprint, jsonify, current_app
import os

auth_api = Blueprint('auth_api', __name__)

@auth_api.route('/api/auth/config')
def get_oauth_config():
    """Return OAuth configuration including required scopes"""
    return jsonify({
        'clientId': os.getenv('GOOGLE_CLIENT_ID'),
        'scopes': [
            'https://www.googleapis.com/auth/contacts.readonly',
            'https://www.googleapis.com/auth/contacts.other.readonly',
            'profile',
            'email'
        ],
        'discoveryDocs': [
            'https://www.googleapis.com/discovery/v1/apis/people/v1/rest'
        ]
    })

@auth_api.route('/api/auth/status')
def get_auth_status():
    """Check authentication status and available scopes"""
    try:
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            return jsonify({
                'status': 'error',
                'message': 'Google OAuth credentials not configured',
                'details': 'Please ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in environment variables'
            }), 500
            
        return jsonify({
            'status': 'configured',
            'hasRequiredScopes': True,
            'message': 'OAuth configuration is valid'
        })
        
    except Exception as e:
        current_app.logger.error(f"Auth status check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to check authentication status',
            'error': str(e)
        }), 500
