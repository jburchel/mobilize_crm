from flask import Blueprint, redirect, request, url_for, session, jsonify, current_app, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from firebase_admin import auth
import os
import json
from functools import wraps

google_auth_bp = Blueprint('google_auth', __name__)

# This variable specifies the name of a file that contains the OAuth 2.0 information
# including client_id and client_secret
CLIENT_SECRETS_FILE = 'client_secret.json'

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection
SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/contacts.readonly',
          'https://www.googleapis.com/auth/contacts.other.readonly']

# Create client_secret.json file if it doesn't exist
def create_client_secrets_file():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        client_config = {
            "web": {
                "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost:5000/google/oauth2callback"]
            }
        }
        with open(CLIENT_SECRETS_FILE, 'w') as f:
            json.dump(client_config, f)

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_credentials():
    if 'credentials' not in session:
        return None
    
    # Load credentials from session
    return Credentials(
        token=session['credentials']['token'],
        refresh_token=session['credentials']['refresh_token'],
        token_uri=session['credentials']['token_uri'],
        client_id=session['credentials']['client_id'],
        client_secret=session['credentials']['client_secret'],
        scopes=session['credentials']['scopes']
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return redirect(url_for('google_auth.authorize'))
        return f(*args, **kwargs)
    return decorated_function

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split('Bearer ')[1]
                auth.verify_id_token(token)
                return f(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Bearer token verification failed: {str(e)}")

        # If no valid bearer token, check for session token
        if 'firebase_token' in request.cookies:
            try:
                auth.verify_id_token(request.cookies['firebase_token'])
                return f(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Cookie token verification failed: {str(e)}")
                
        # No valid authentication found, redirect to home
        return redirect(url_for('home'))
            
    return decorated_function

def get_access_token_from_header():
    """Extract Google access token from Authorization header"""
    if 'X-Google-Token' in request.headers:
        return request.headers.get('X-Google-Token')
    return None

def build_credentials(token):
    """Build Google credentials object from access token"""
    return Credentials(
        token=token,
        refresh_token=None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scopes=SCOPES
    )

@google_auth_bp.route('/google/authorize')
def authorize():
    # Create client_secrets.json file
    create_client_secrets_file()
    
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('google_auth.oauth2callback', _external=True)
    )
    
    # Generate URL for request to Google's OAuth 2.0 server
    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission
        access_type='offline',
        # Enable incremental authorization
        include_granted_scopes='true'
    )
    
    # Store the state so that the callback can verify the auth server response
    session['state'] = state
    
    return redirect(authorization_url)

@google_auth_bp.route('/google/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response
    state = session.get('state', None)
    
    # Create client_secrets.json file
    create_client_secrets_file()
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('google_auth.oauth2callback', _external=True)
    )
    
    # Use the authorization server's response to fetch the OAuth 2.0 tokens
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    # Store credentials in the session
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    
    return redirect(url_for('google_auth.google_settings'))

@google_auth_bp.route('/google/revoke')
def revoke():
    if 'credentials' not in session:
        return jsonify({'message': 'No credentials to revoke'}), 400
    
    credentials = get_credentials()
    
    if credentials:
        # Revoke access to the Google API
        revoke_url = f'https://oauth2.googleapis.com/revoke?token={credentials.token}'
        import requests
        requests.post(revoke_url)
    
    # Clear the session credentials
    del session['credentials']
    
    return jsonify({'message': 'Credentials successfully revoked'})

@google_auth_bp.route('/google/settings')
@auth_required
def google_settings_page():
    """Render the Google settings page"""
    return render_template('google_settings.html')

@google_auth_bp.route('/google/status')
@auth_required
def google_status():
    """Check if the current user has valid Google credentials"""
    token = get_access_token_from_header()
    if not token:
        return jsonify({
            'connected': False,
            'message': 'No Google token found'
        })
    
    # Try to use the token to verify it's valid
    try:
        credentials = build_credentials(token)
        # Try to access service to verify token works
        calendar_service = build('calendar', 'v3', credentials=credentials)
        calendar_list = calendar_service.calendarList().list(maxResults=1).execute()
        
        return jsonify({
            'connected': True,
            'message': 'Connected to Google account',
            'scopes': SCOPES
        })
    except Exception as e:
        current_app.logger.error(f"Error verifying Google token: {e}")
        return jsonify({
            'connected': False,
            'message': 'Invalid or expired Google token'
        })