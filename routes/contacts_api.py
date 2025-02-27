from flask import Blueprint, jsonify, request, current_app
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import firebase_admin
from firebase_admin import auth
from sqlalchemy import or_
from models import Person, Church, Contacts, session_scope
import os
import traceback

contacts_api = Blueprint('contacts_api', __name__)

def verify_firebase_token(request):
    if 'Authorization' not in request.headers:
        return None
    
    token = request.headers['Authorization'].split('Bearer ')[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        current_app.logger.error(f"Token verification error: {e}")
        return None

@contacts_api.route('/api/contacts/check-import/<resource_name>', methods=['GET'])
def check_import_status(resource_name):
    token_data = verify_firebase_token(request)
    if not token_data:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        with session_scope() as session:
            # Check if contact already exists in either table
            existing_contact = session.query(Contacts).filter(
                Contacts.google_resource_name == resource_name
            ).first()

            if existing_contact:
                return jsonify({
                    'imported': True,
                    'contact': {
                        'id': existing_contact.id,
                        'name': existing_contact.get_name(),
                        'type': existing_contact.type
                    }
                })

            return jsonify({'imported': False})
            
    except Exception as e:
        current_app.logger.error(f"Error checking import status: {e}")
        return jsonify({'error': str(e)}), 500

@contacts_api.route('/api/contacts/list', methods=['POST'])
def list_contacts():
    """List Google contacts"""
    token_data = verify_firebase_token(request)
    if not token_data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get access token from request body
        request_data = request.get_json()
        if not request_data or 'access_token' not in request_data:
            current_app.logger.error("No access token provided in request")
            return jsonify({'error': 'No access token provided'}), 400
        
        access_token = request_data['access_token']
        current_app.logger.info("Received access token, creating Google credentials")
        
        # Create Google credentials with the access token
        google_credentials = Credentials(
            token=access_token,
            refresh_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=[
                "https://www.googleapis.com/auth/contacts.readonly",
                "https://www.googleapis.com/auth/contacts.other.readonly"
            ]
        )

        current_app.logger.info("Building People API service")
        service = build('people', 'v1', credentials=google_credentials)
        
        try:
            current_app.logger.info("Fetching contact groups")
            # First fetch contact groups
            groups_result = service.contactGroups().list(pageSize=100).execute()
            groups = groups_result.get('contactGroups', [])
            processed_groups = []
            
            # Create a map of group IDs to their resourceNames for quick lookup
            group_map = {}
            for group in groups:
                if group.get('resourceName') and group.get('name'):
                    processed_groups.append({
                        'resourceName': group.get('resourceName'),
                        'name': group.get('name')
                    })
                    group_map[group.get('resourceName')] = group.get('name')
            
            current_app.logger.info("Fetching contacts")
            # Then fetch contacts with their memberships
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses,phoneNumbers,addresses,memberships'
            ).execute()
            
            connections = results.get('connections', [])
            processed_contacts = []
            
            current_app.logger.info(f"Processing {len(connections)} contacts")
            for person in connections:
                names = person.get('names', [])
                name = names[0].get('displayName') if names else 'No Name'
                contact = {
                    'resource_name': person.get('resourceName'),
                    'names': name,
                    'email_addresses': [email.get('value') for email in person.get('emailAddresses', [])],
                    'phone_numbers': [phone.get('value') for phone in person.get('phoneNumbers', [])],
                    'addresses': [addr.get('formattedValue') for addr in person.get('addresses', [])],
                    'groups': []
                }
                
                # Extract group memberships
                memberships = person.get('memberships', [])
                for membership in memberships:
                    if 'contactGroupMembership' in membership:
                        group_resource_name = membership['contactGroupMembership'].get('contactGroupResourceName')
                        if group_resource_name:
                            contact['groups'].append(group_resource_name)
                
                processed_contacts.append(contact)
            
            current_app.logger.info(f"Found {len(processed_groups)} groups and {len(processed_contacts)} contacts")
            return jsonify({
                'contacts': processed_contacts,
                'groups': processed_groups
            })
            
        except HttpError as e:
            current_app.logger.error(f"Google API error: {e}")
            if e.resp.status == 403:
                return jsonify({'error': 'Access to contacts denied. Please check permissions.'}), 403
            elif e.resp.status == 401:
                return jsonify({'error': 'Authentication failed. Please sign in again.'}), 401
            raise
            
    except Exception as e:
        current_app.logger.error(f"Error listing contacts: {e}", exc_info=True)
        return jsonify({'error': 'Failed to access contacts. Please try signing out and in again.'}), 500

@contacts_api.route('/api/contacts/import', methods=['POST'])
def import_contact():
    """Import a Google contact as either a person or church"""
    token_data = verify_firebase_token(request)
    if not token_data:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        resource_name = data.get('resource_name')
        names = data.get('names', '')
        email_addresses = data.get('email_addresses', [])
        phone_numbers = data.get('phone_numbers', [])
        addresses = data.get('addresses', [])
        import_type = data.get('import_type')

        current_app.logger.info(f"Importing contact: {names} as {import_type}")

        if not resource_name:
            return jsonify({'error': 'No resource name provided'}), 400

        with session_scope() as session:
            # Check if contact already exists
            existing_contact = session.query(Contacts).filter_by(
                google_resource_name=resource_name
            ).first()

            # Parse address components
            address_parts = {}
            if addresses:
                address = addresses[0]
                current_app.logger.debug(f"Processing address: {address}")
                try:
                    # Try to parse the formatted address
                    address_lines = address.split(',')
                    if len(address_lines) >= 2:
                        # Last part usually contains state and zip
                        state_zip = address_lines[-1].strip().split()
                        if len(state_zip) >= 2:
                            address_parts['state'] = state_zip[0]
                            address_parts['zip_code'] = state_zip[1]
                        # Second to last part usually contains city
                        address_parts['city'] = address_lines[-2].strip()
                        # First part(s) contain street address
                        address_parts['street_address'] = ','.join(address_lines[:-2]).strip()
                except Exception as e:
                    current_app.logger.warning(f"Error parsing address: {e}")

            current_app.logger.debug(f"Address parts: {address_parts}")

            try:
                if import_type == 'church':
                    if existing_contact and existing_contact.type == 'person':
                        # Delete the existing person contact
                        current_app.logger.info(f"Deleting existing person contact: {existing_contact.get_name()}")
                        session.delete(existing_contact)
                        session.flush()
                        existing_contact = None

                    if existing_contact and existing_contact.type == 'church':
                        return jsonify({
                            'message': 'Church already imported',
                            'contact': {
                                'id': existing_contact.id,
                                'name': existing_contact.get_name(),
                                'type': existing_contact.type
                            }
                        })

                    # Create new church
                    new_contact = Church(
                        type='church',
                        church_name=names,
                        email=email_addresses[0] if email_addresses else None,
                        phone=phone_numbers[0] if phone_numbers else None,
                        street_address=address_parts.get('street_address'),
                        city=address_parts.get('city'),
                        state=address_parts.get('state'),
                        zip_code=address_parts.get('zip_code'),
                        google_resource_name=resource_name,
                        location=f"{address_parts.get('city', '')}, {address_parts.get('state', '')}" if address_parts.get('city') and address_parts.get('state') else None
                    )
                else:  # person
                    if existing_contact:
                        return jsonify({
                            'message': 'Contact already imported',
                            'contact': {
                                'id': existing_contact.id,
                                'name': existing_contact.get_name(),
                                'type': existing_contact.type
                            }
                        })

                    # Create new person contact
                    name_parts = names.split()
                    first_name = name_parts[0] if name_parts else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    new_contact = Person(
                        type='person',
                        first_name=first_name,
                        last_name=last_name,
                        email=email_addresses[0] if email_addresses else None,
                        phone=phone_numbers[0] if phone_numbers else None,
                        street_address=address_parts.get('street_address'),
                        city=address_parts.get('city'),
                        state=address_parts.get('state'),
                        zip_code=address_parts.get('zip_code'),
                        google_resource_name=resource_name
                    )

                current_app.logger.info(f"Adding new contact to database: {new_contact.get_name()}")
                session.add(new_contact)
                
                return jsonify({
                    'message': 'Contact imported successfully',
                    'contact': {
                        'id': new_contact.id,
                        'name': new_contact.get_name(),
                        'email': new_contact.email,
                        'type': import_type
                    }
                })

            except Exception as db_error:
                current_app.logger.error(f"Database error: {db_error}")
                current_app.logger.error(traceback.format_exc())
                raise

    except Exception as e:
        current_app.logger.error(f"Error importing contact: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Failed to import contact',
            'message': str(e)
        }), 500
