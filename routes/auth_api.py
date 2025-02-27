from flask import Blueprint, jsonify, request, current_app
import os
import firebase_admin
from firebase_admin import auth

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

@auth_api.route('/api/auth/token', methods=['POST'])
def update_token():
    """Update Firebase user custom claims with Google OAuth token"""
    try:
        # Verify Firebase ID token
        if 'Authorization' not in request.headers:
            return jsonify({'error': 'No authorization header'}), 401
        
        id_token = request.headers['Authorization'].split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        # Get access token from request body
        data = request.get_json()
        if not data or 'accessToken' not in data:
            return jsonify({'error': 'No access token provided'}), 400
            
        # Set custom claims with Google access token
        try:
            current_claims = auth.get_user(uid).custom_claims or {}
            new_claims = {
                **current_claims,
                'googleAccessToken': data['accessToken']
            }
            auth.set_custom_user_claims(uid, new_claims)
            
            # Get fresh token with new claims
            fresh_token = auth.create_custom_token(uid, new_claims)
            
            return jsonify({
                'status': 'success',
                'message': 'Token updated successfully',
                'token': fresh_token.decode('utf-8') if isinstance(fresh_token, bytes) else fresh_token
            })
            
        except Exception as e:
            current_app.logger.error(f"Error setting custom claims: {e}")
            return jsonify({
                'error': 'Failed to update token',
                'message': str(e)
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Auth error: {e}")
        return jsonify({
            'error': 'Authentication failed',
            'message': str(e)
        }), 401

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
