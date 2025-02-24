from flask import Blueprint, jsonify, request
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import auth
from sqlalchemy import or_
from models import Person, Church, Contacts, session_scope
import os

contacts_api = Blueprint('contacts_api', __name__)

def verify_firebase_token(request):
    if 'Authorization' not in request.headers:
        return None
    
    token = request.headers['Authorization'].split('Bearer ')[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"Token verification error: {e}")
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
        print(f"Error checking import status: {e}")
        return jsonify({'error': str(e)}), 500

@contacts_api.route('/api/contacts/sync', methods=['POST'])
def sync_contacts():
    token_data = verify_firebase_token(request)
    if not token_data:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        request_data = request.get_json()
        if not request_data or 'access_token' not in request_data:
            return jsonify({'error': 'No access token provided'}), 400

        access_token = request_data['access_token']
        
        google_credentials = Credentials(
            token=access_token,
            refresh_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=["https://www.googleapis.com/auth/contacts.readonly"]
        )

        service = build('people', 'v1', credentials=google_credentials)
        
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=1000,
            personFields='names,emailAddresses,phoneNumbers,addresses,memberships'
        ).execute()

        connections = results.get('connections', [])
        processed_contacts = []

        print(f"Processing {len(connections)} contacts from Google")
        
        for person in connections:
            try:
                names = person.get('names', [])
                name = names[0].get('displayName', 'No Name') if names else 'No Name'
                
                email_addresses = person.get('emailAddresses', [])
                emails = [email.get('value') for email in email_addresses if email.get('value')]
                
                phone_numbers = person.get('phoneNumbers', [])
                phones = [phone.get('value') for phone in phone_numbers if phone.get('value')]
                
                addresses = person.get('addresses', [])
                formatted_addresses = [addr.get('formattedValue') for addr in addresses if addr.get('formattedValue')]
                
                contact = {
                    'resource_name': person.get('resourceName'),
                    'names': name,
                    'email_addresses': emails,
                    'phone_numbers': phones,
                    'addresses': formatted_addresses
                }
                
                print(f"Processed contact: {name}")  # Debug log
                processed_contacts.append(contact)
            except Exception as e:
                print(f"Error processing contact: {e}")
                continue

        print(f"Successfully processed {len(processed_contacts)} contacts")
        return jsonify(processed_contacts)

    except Exception as e:
        print(f"Error syncing contacts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@contacts_api.route('/api/contacts/import', methods=['POST'])
def import_contact():
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

        print(f"[DEBUG] Attempting to import contact: {names} as {import_type}")

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
                print(f"[DEBUG] Processing address: {address}")
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
                print(f"[DEBUG] Parsed address parts: {address_parts}")

            try:
                if import_type == 'church':
                    if existing_contact and existing_contact.type == 'person':
                        # Delete the existing person contact
                        print(f"[DEBUG] Deleting existing person contact: {existing_contact.get_name()}")
                        session.delete(existing_contact)
                        session.flush()
                        existing_contact = None

                    if existing_contact and existing_contact.type == 'church':
                        print(f"[DEBUG] Church already exists: {existing_contact.get_name()}")
                        return jsonify({
                            'message': 'Church already imported',
                            'contact': {
                                'id': existing_contact.id,
                                'name': existing_contact.get_name(),
                                'type': existing_contact.type
                            }
                        })

                    print(f"[DEBUG] Creating new church: {names}")
                    new_contact = Church(
                        type='church',  # This is redundant but explicit
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
                else:
                    if existing_contact:
                        print(f"[DEBUG] Contact already exists: {existing_contact.get_name()}")
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
                    
                    print(f"[DEBUG] Creating new person: {first_name} {last_name}")
                    new_contact = Person(
                        type='person',  # This is redundant but explicit
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

                print(f"[DEBUG] Adding new contact to session...")
                session.add(new_contact)
                print(f"[DEBUG] Contact will be committed by session_scope: {new_contact.get_name()} (type: {new_contact.type})")
                
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
                print(f"[DEBUG] Database error while importing contact: {db_error}")
                raise

    except Exception as e:
        print(f"[DEBUG] Error importing contact: {e}")
        return jsonify({'error': str(e)}), 500

@contacts_api.route('/api/contacts/list', methods=['POST'])
def list_contacts():
    """List Google contacts without syncing"""
    token_data = verify_firebase_token(request)
    if not token_data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get access token from request body
        request_data = request.get_json()
        if not request_data or 'access_token' not in request_data:
            return jsonify({'error': 'No access token provided'}), 400
        
        access_token = request_data['access_token']
        
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
        
        # Build the People API service
        service = build('people', 'v1', credentials=google_credentials)
        
        try:
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
            
            # Then fetch contacts with their memberships
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,emailAddresses,phoneNumbers,addresses,memberships'
            ).execute()
            
            connections = results.get('connections', [])
            processed_contacts = []
            
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
            
            print(f"Found {len(processed_groups)} groups and {len(processed_contacts)} contacts")
            return jsonify({
                'contacts': processed_contacts,
                'groups': processed_groups
            })
            
        except Exception as e:
            print(f"Error in Google API calls: {e}")
            raise
            
    except Exception as e:
        print(f"Error listing contacts: {e}")
        return jsonify({'error': str(e)}), 500