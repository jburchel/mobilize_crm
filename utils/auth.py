"""
Authentication utilities for the Mobilize CRM application.
"""
from functools import wraps
from flask import request, redirect, url_for, current_app, session
import firebase_admin
from firebase_admin import auth

def get_current_user_id():
    """
    Get the current user ID from the session or request headers.
    
    Returns:
        str: The user ID if authenticated, None otherwise.
    """
    # Check session first
    user_id = session.get('user_id')
    if user_id:
        return user_id
    
    # Check Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token.get('uid')
        except Exception as e:
            current_app.logger.warning(f"Token verification failed: {str(e)}")
    
    # Check cookie
    token = request.cookies.get('firebase_token')
    if token:
        try:
            decoded_token = auth.verify_id_token(token)
            return decoded_token.get('uid')
        except Exception as e:
            current_app.logger.warning(f"Cookie token verification failed: {str(e)}")
    
    return None

def auth_required(f):
    """
    Decorator to require authentication for a route.
    
    Args:
        f: The function to decorate.
        
    Returns:
        function: The decorated function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if this is an API request
        is_api_request = request.path.startswith('/api/')
        current_app.logger.debug(f"Auth check for path: {request.path}, is_api_request: {is_api_request}")
        
        # Get user ID
        user_id = get_current_user_id()
        
        if not user_id:
            if is_api_request:
                return {'error': 'Authentication required'}, 401
            else:
                return redirect(url_for('home'))
        
        # Store user ID in session for convenience
        session['user_id'] = user_id
        
        return f(*args, **kwargs)
    
    return decorated_function 