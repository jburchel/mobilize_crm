from flask import Blueprint, jsonify, request
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import firebase_admin
from firebase_admin import auth
from models import Person, session_scope
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
            existing_contact = session.query(Person).filter_by(
                google_resource_name=resource_name
            ).first()
            return jsonify({
                'imported': existing_contact is not None,
                'person': {
                    'id': existing_contact.id,
                    'name': existing_contact.name
                } if existing_contact else None
            })
    except Exception as e:
        print(f"Error checking import status: {e}")
        return jsonify({'error': str(e)}), 500

@contacts_api.route('/api/contacts/sync', methods=['POST'])
def sync_contacts():
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
            scopes=["https://www.googleapis.com/auth/contacts.readonly"]
        )

        # Build the People API service
        service = build('people', 'v1', credentials=google_credentials)
        
        # Call the People API
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
                    contact['groups'].append(membership['contactGroupMembership'].get('contactGroupId'))
            
            processed_contacts.append(contact)

        return jsonify(processed_contacts)

    except Exception as e:
        print(f"Error syncing contacts: {e}")
        return jsonify({'error': str(e)}), 500

@contacts_api.route('/api/contacts/import', methods=['POST'])
def import_contact():
    token_data = verify_firebase_token(request)
    if not token_data:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        contact_data = request.json
        if not contact_data:
            return jsonify({'error': 'No contact data provided'}), 400

        with session_scope() as session:
            # Check if contact already exists by google_resource_name
            existing_contact = session.query(Person).filter_by(
                google_resource_name=contact_data['resource_name']
            ).first()
            
            if existing_contact:
                return jsonify({
                    'message': 'Contact already imported',
                    'person': {
                        'id': existing_contact.id,
                        'name': existing_contact.name,
                        'email': existing_contact.email,
                        'phone': existing_contact.phone,
                        'address': existing_contact.address
                    }
                }), 200

            # Create new person from contact data
            new_person = Person(
                name=contact_data['names'],
                email=contact_data['email_addresses'][0] if contact_data['email_addresses'] else None,
                phone=contact_data['phone_numbers'][0] if contact_data['phone_numbers'] else None,
                address=contact_data['addresses'][0] if contact_data['addresses'] else None,
                role='Contact',  # Default role for imported contacts
                google_resource_name=contact_data['resource_name']
            )
            session.add(new_person)
            # session.commit() is handled by the context manager
            return jsonify({
                'message': 'Contact imported successfully',
                'person': {
                    'id': new_person.id,
                    'name': new_person.name,
                    'email': new_person.email,
                    'phone': new_person.phone,
                    'address': new_person.address
                }
            })
    except Exception as e:
        print(f"Error importing contact: {e}")
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