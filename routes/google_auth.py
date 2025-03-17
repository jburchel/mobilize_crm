from flask import Blueprint, redirect, request, url_for, session, jsonify, current_app, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from firebase_admin import auth
import os
import json
from functools import wraps
import sqlite3
from datetime import datetime
import traceback

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
        # Get the base URL from the application config
        base_url = current_app.config.get('BASE_URL', 'http://localhost:8000')
        
        # Construct the redirect URI using the base URL
        redirect_uri = f"{base_url}/google/oauth2callback"
        
        # For Cloud Run, ensure we're using HTTPS
        if 'run.app' in redirect_uri:
            redirect_uri = redirect_uri.replace('http://', 'https://')
        
        current_app.logger.info(f"Creating client_secret.json with redirect URI: {redirect_uri}")
        
        client_secrets = {
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "redirect_uris": [redirect_uri]
            }
        }
        with open(CLIENT_SECRETS_FILE, 'w') as f:
            json.dump(client_secrets, f)

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_current_user_id():
    """Get the current user ID from the session or request.
    
    Returns:
        str: The user ID if available, None otherwise.
    """
    # First try to get from session
    if 'user_id' in session:
        return session['user_id']
    
    # Then try to get from request headers (for API calls)
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Verify the Firebase token
            try:
                decoded_token = auth.verify_id_token(token)
                return decoded_token['uid']
            except Exception as e:
                current_app.logger.error(f"Error verifying Firebase token: {str(e)}")
                return None
    except Exception as e:
        current_app.logger.error(f"Error getting user ID from request: {str(e)}")
        return None
    
    return None

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
        # Check if this is an API request
        is_api_request = request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json'
        current_app.logger.debug(f"Auth check for path: {request.path}, is_api_request: {is_api_request}")
        
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
        
        # Check for X-Google-Token header for Gmail API requests
        if 'X-Google-Token' in request.headers:
            current_app.logger.debug("Found X-Google-Token header, allowing request")
            return f(*args, **kwargs)
                
        # No valid authentication found
        if is_api_request:
            # Return JSON response for API requests
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
        else:
            # Redirect to home for web requests
            return redirect(url_for('home'))
            
    return decorated_function

def get_access_token_from_header():
    """Extract Google access token from Authorization header"""
    current_app.logger.debug("Attempting to extract Google access token")
    
    # First check for X-Google-Token header
    if 'X-Google-Token' in request.headers:
        token = request.headers.get('X-Google-Token')
        current_app.logger.info(f"Found token in X-Google-Token header: {token[:10]}...")
        return token
    
    # Then check for Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ')[1]
        current_app.logger.info(f"Found token in Authorization header: {token[:10]}...")
        return token
    
    # Finally check session
    if 'credentials' in session and 'token' in session['credentials']:
        token = session['credentials']['token']
        current_app.logger.info(f"Found token in session: {token[:10]}...")
        return token
    
    # Log all headers for debugging
    current_app.logger.debug(f"All request headers: {dict(request.headers)}")
    current_app.logger.debug(f"Session keys: {session.keys() if session else 'No session'}")
    
    # Try to get tokens from database as a last resort
    try:
        conn = sqlite3.connect('instance/mobilize_crm.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT token FROM google_tokens 
            ORDER BY updated_at DESC LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            token = result[0]
            current_app.logger.info(f"Found token in database: {token[:10]}...")
            return token
        else:
            current_app.logger.debug("No token found in database")
    except Exception as e:
        current_app.logger.error(f"Error checking database for tokens: {e}")
    
    current_app.logger.warning("No Google token found in headers, session, or database")
    return None

def get_user_tokens():
    """
    Get Google tokens for background jobs
    This function retrieves tokens from the database for use in background jobs
    where there is no active request context
    
    Returns:
        dict: Dictionary containing token information or None if no tokens found
    """
    try:
        # First check if we're in a request context and have credentials in session
        try:
            if 'credentials' in session:
                current_app.logger.info("Found Google credentials in session")
                return session['credentials']
        except RuntimeError:
            # Not in request context
            current_app.logger.debug("Not in request context, cannot access session")
            pass
            
        # Connect to the database
        current_app.logger.debug("Attempting to retrieve Google tokens from database")
        conn = sqlite3.connect('instance/mobilize_crm.db')
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR NOT NULL,
                access_token VARCHAR NOT NULL,
                refresh_token VARCHAR,
                token_uri VARCHAR,
                client_id VARCHAR,
                client_secret VARCHAR,
                scopes VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if the table has any records
        cursor.execute("SELECT COUNT(*) FROM google_tokens")
        count = cursor.fetchone()[0]
        current_app.logger.debug(f"Found {count} token records in database")
        
        # Query for the most recently used token
        cursor.execute("""
            SELECT token, refresh_token, token_uri, client_id, client_secret, scopes
            FROM google_tokens
            ORDER BY updated_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            current_app.logger.debug("No tokens found in database")
            current_app.logger.error("No Google tokens found in database or session")
            return None
            
        # Format the result as a dictionary
        token_data = {
            'token': result[0],  # This is the token column
            'refresh_token': result[1],
            'token_uri': result[2],
            'client_id': result[3],
            'client_secret': result[4],
            'scopes': result[5].split(',') if result[5] else []
        }
        
        current_app.logger.debug(f"Retrieved token from database: {token_data['token'][:10]}...")
        return token_data
        
    except Exception as e:
        try:
            current_app.logger.error(f"Error retrieving Google tokens: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        except RuntimeError:
            # Not in application context
            print(f"Error retrieving Google tokens: {e}")
        return None

def save_user_tokens(token_data):
    """
    Save Google tokens to the database
    
    Args:
        token_data (dict): Dictionary containing token information
    """
    try:
        current_app.logger.info("Saving Google tokens to database")
        if not token_data:
            current_app.logger.error("Cannot save tokens: token_data is None or empty")
            return
            
        current_app.logger.debug(f"Token data keys: {token_data.keys()}")
        current_app.logger.debug(f"Token preview: {token_data.get('token', '')[:10]}...")
        
        # Get the user ID and email
        user_id = get_current_user_id()
        user_email = session.get('user_email')
        
        if not user_id:
            current_app.logger.error("Cannot save tokens: No user_id available")
            return
            
        current_app.logger.info(f"Saving tokens for user_id: {user_id}, email: {user_email}")
        
        # Connect to the database
        conn = sqlite3.connect('instance/mobilize_crm.db')
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR NOT NULL,
                user_email VARCHAR,
                access_token VARCHAR NOT NULL,
                refresh_token VARCHAR,
                token_uri VARCHAR,
                client_id VARCHAR,
                client_secret VARCHAR,
                scopes VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if we need to add the user_email column
        try:
            cursor.execute("SELECT user_email FROM google_tokens LIMIT 1")
        except sqlite3.OperationalError:
            current_app.logger.info("Adding user_email column to google_tokens table")
            cursor.execute("ALTER TABLE google_tokens ADD COLUMN user_email VARCHAR")
        
        # Insert or update the token
        cursor.execute("""
            INSERT INTO google_tokens 
            (user_id, user_email, token, refresh_token, token_uri, client_id, client_secret, scopes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            user_email,
            token_data['token'],
            token_data.get('refresh_token'),
            token_data['token_uri'],
            token_data['client_id'],
            token_data['client_secret'],
            ','.join(token_data['scopes']) if token_data.get('scopes') else None,
            datetime.now()
        ))
        
        conn.commit()
        
        # Verify the token was saved
        cursor.execute("SELECT id FROM google_tokens WHERE token = ? ORDER BY updated_at DESC LIMIT 1", 
                      (token_data['token'],))
        result = cursor.fetchone()
        if result:
            current_app.logger.info(f"Google token saved successfully with ID: {result[0]}")
        else:
            current_app.logger.error("Failed to save Google token: No record found after insert")
            
        conn.close()
        
    except Exception as e:
        current_app.logger.error(f"Error saving Google tokens: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")

def build_credentials(token):
    """Build Google credentials object from access token"""
    # Try to get refresh token from the database
    refresh_token = None
    user_id = get_current_user_id()
    
    if user_id:
        try:
            conn = sqlite3.connect('instance/mobilize_crm.db')
            cursor = conn.cursor()
            
            # Query for refresh token
            cursor.execute("""
                SELECT refresh_token FROM google_tokens 
                WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1
            """, (user_id,))
            
            result = cursor.fetchone()
            if result and result[0]:
                refresh_token = result[0]
                current_app.logger.info(f"Found refresh token for user {user_id}")
            else:
                current_app.logger.warning(f"No refresh token found for user {user_id}")
                
            conn.close()
        except Exception as e:
            current_app.logger.error(f"Error retrieving refresh token: {e}")
    
    return Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scopes=SCOPES
    )

@google_auth_bp.route('/google/authorize')
def authorize():
    # Create client_secrets.json file
    create_client_secrets_file()
    
    # Get the referrer page to redirect back after authorization
    referrer = request.referrer or url_for('communications_bp.communications_route')
    session['oauth_referrer'] = referrer
    
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
    
    # Get user information from Google
    try:
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        # Get the user's email from Google
        google_email = user_info.get('email')
        
        if not google_email:
            current_app.logger.error("Failed to get user email from Google")
            from flask import flash
            flash('Failed to get user email from Google. Please try again.', 'danger')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        current_app.logger.info(f"User authenticated with Google email: {google_email}")
        
        # Store the user's email in the session
        session['user_email'] = google_email
        
        # Ensure we have a user_id in the session (from Firebase auth)
        user_id = session.get('user_id')
        
        if not user_id:
            current_app.logger.warning(f"No Firebase user_id in session for Google email: {google_email}")
            from flask import flash
            flash('Please sign in with Firebase first before connecting Google.', 'warning')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        current_app.logger.info(f"Associating Google credentials with Firebase user_id: {user_id}")
    except Exception as e:
        current_app.logger.error(f"Error getting user info from Google: {str(e)}")
        current_app.logger.error(traceback.format_exc())
    
    # Also save to database for background jobs
    save_user_tokens(credentials_to_dict(credentials))
    
    # Get the referrer page to redirect back
    referrer = session.pop('oauth_referrer', url_for('communications_bp.communications_route'))
    
    # Add a flash message to indicate successful connection
    from flask import flash
    flash('Google account connected successfully!', 'success')
    
    return redirect(referrer)

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

def get_all_user_tokens():
    """
    Get Google tokens for all users
    This function retrieves tokens from the database for all users
    
    Returns:
        dict: Dictionary mapping user IDs to token information
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('mobilize_crm.db')
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist (should already exist)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR NOT NULL,
                user_email VARCHAR,
                access_token VARCHAR NOT NULL,
                refresh_token VARCHAR,
                token_uri VARCHAR,
                client_id VARCHAR,
                client_secret VARCHAR,
                scopes VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if we need to add the user_email column
        try:
            cursor.execute("SELECT user_email FROM google_tokens LIMIT 1")
        except sqlite3.OperationalError:
            current_app.logger.info("Adding user_email column to google_tokens table")
            cursor.execute("ALTER TABLE google_tokens ADD COLUMN user_email VARCHAR")
        
        # Query for all tokens
        cursor.execute("""
            SELECT user_id, user_email, token, refresh_token, token_uri, client_id, client_secret, scopes
            FROM google_tokens
            WHERE token IS NOT NULL
            GROUP BY user_id
            HAVING MAX(updated_at)
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        tokens = {}
        for row in results:
            user_id = row[0] or 'default'
            tokens[user_id] = {
                'user_email': row[1],
                'token': row[2],
                'refresh_token': row[3],
                'token_uri': row[4],
                'client_id': row[5],
                'client_secret': row[6],
                'scopes': row[7].split(' ') if row[7] else []
            }
        
        current_app.logger.info(f"Retrieved tokens for {len(tokens)} users")
        for user_id, token_data in tokens.items():
            current_app.logger.debug(f"User {user_id} has email: {token_data.get('user_email')}")
        
        return tokens
    except Exception as e:
        current_app.logger.error(f"Error getting all user tokens: {str(e)}")
        return {}

@google_auth_bp.route('/google/store-token', methods=['POST'])
@auth_required
def store_token():
    """Store Google access token from client-side in server-side session"""
    try:
        data = request.json
        if not data or 'token' not in data:
            current_app.logger.error("No token provided in request")
            return jsonify({
                'success': False,
                'message': 'No token provided'
            }), 400
            
        token = data['token']
        current_app.logger.info(f"Received Google access token from client: {token[:10]}...")
        
        # Build credentials object
        credentials = build_credentials(token)
        
        # Store in session
        session['credentials'] = credentials_to_dict(credentials)
        current_app.logger.info("Stored Google credentials in session")
        
        # Also save to database for background jobs
        save_user_tokens(credentials_to_dict(credentials))
        current_app.logger.info("Saved Google credentials to database")
        
        return jsonify({
            'success': True,
            'message': 'Google token stored successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error storing Google token: {e}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500