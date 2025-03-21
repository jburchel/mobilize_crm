"""
Blueprint for Gmail integration with Communications
"""
from flask import Blueprint, request, jsonify, current_app
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from models import Communication, Person, Church, EmailSignature
from database import db, session_scope
from routes.google_auth import get_access_token_from_header, get_current_user_id
from routes.dashboard import auth_required
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
import traceback
from datetime import datetime
import time
import threading
import re
import os
from utils.gmail_integration import (
    build_gmail_service,
    create_message,
    create_message_with_attachment,
    send_message,
    get_message,
    list_messages,
    get_message_content,
    create_draft,
    send_draft
)
from sqlalchemy import func, desc

gmail_api = Blueprint('gmail_api', __name__)
logger = logging.getLogger(__name__)

def extract_email_address(email_string):
    """Extract the email address from a string like 'Name <email@example.com>'"""
    if not email_string:
        return None
        
    # Check if the email has the format "Name <email@example.com>"
    if '<' in email_string and '>' in email_string:
        # Extract the part between < and >
        return email_string.split('<')[1].split('>')[0].strip().lower()
    else:
        # Assume the string is just an email address
        return email_string.strip().lower()

@gmail_api.route('/api/gmail/send', methods=['POST'])
@auth_required
def send_email():
    """Send an email through Gmail API"""
    logger.info("Gmail API send_email endpoint called")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request content type: {request.content_type}")
    logger.debug(f"Request method: {request.method}")
    
    # Get Google access token from header
    token = get_access_token_from_header()
    if not token:
        logger.error("No Google access token provided in request")
        return jsonify({
            'success': False,
            'message': 'Google access token required. Please reconnect your Google account.'
        }), 401
    
    logger.debug(f"Using token: {token[:10]}...")
    
    try:
        # Get request data
        try:
            if request.is_json:
                data = request.json
                logger.debug(f"Parsed JSON data: {data}")
            else:
                logger.warning("Request is not JSON. Content-Type: " + request.content_type)
                # Try to parse form data
                data = request.form.to_dict()
                logger.debug(f"Parsed form data: {data}")
                
                # If no form data, try to parse raw data
                if not data:
                    logger.warning("No form data found, trying to parse raw data")
                    try:
                        raw_data = request.get_data(as_text=True)
                        logger.debug(f"Raw request data: {raw_data}")
                        data = json.loads(raw_data)
                        logger.debug(f"Parsed raw data: {data}")
                    except json.JSONDecodeError:
                        logger.error("Failed to parse raw data as JSON")
                        return jsonify({
                            'success': False,
                            'message': 'Invalid request format. Expected JSON data.'
                        }), 400
        except Exception as e:
            logger.error(f"Error parsing request data: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Error parsing request data: {str(e)}'
            }), 400
        
        if not data:
            logger.error("No data provided in request")
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['to', 'subject', 'message']
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get email data
        to_email = data['to']
        subject = data['subject']
        message_text = data['message']
        html_content = data.get('html_content')
        person_id = data.get('person_id')
        church_id = data.get('church_id')
        signature_id = data.get('signature_id')
        
        logger.info(f"Preparing to send email to: {to_email}")
        logger.debug(f"Subject: {subject}")
        logger.debug(f"Person ID: {person_id}, Church ID: {church_id}")
        logger.debug(f"Signature ID: {signature_id}")
        
        # Get signature if signature_id is provided
        signature_html = None
        if signature_id:
            try:
                with session_scope() as session:
                    signature = session.query(EmailSignature).filter_by(id=signature_id).first()
                    if signature:
                        signature_html = signature.content
                        logger.debug(f"Using signature: {signature.name}")
                    else:
                        logger.warning(f"Signature with ID {signature_id} not found")
            except Exception as e:
                logger.error(f"Error retrieving signature: {str(e)}")
                logger.error(traceback.format_exc())
        
        # If no specific signature was requested, try to get the default signature
        if not signature_html:
            try:
                from routes.google_auth import get_current_user_id
                user_id = get_current_user_id()
                if user_id:
                    with session_scope() as session:
                        default_signature = session.query(EmailSignature).filter_by(
                            user_id=user_id, is_default=True
                        ).first()
                        if default_signature:
                            signature_html = default_signature.content
                            logger.debug(f"Using default signature: {default_signature.name}")
                        else:
                            logger.debug(f"No default signature found for user {user_id}")
            except Exception as e:
                logger.error(f"Error retrieving default signature: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Verify the recipient is a contact in our system
        with session_scope() as session:
            is_contact = False
            
            # Check if we have a person_id or church_id
            if person_id or church_id:
                is_contact = True
                logger.debug(f"Recipient is a contact (person_id: {person_id}, church_id: {church_id})")
            else:
                # Check if the email belongs to a contact
                person = session.query(Person).filter(Person.email == to_email).first()
                church = session.query(Church).filter(Church.email == to_email).first()
                
                if person:
                    person_id = person.id
                    is_contact = True
                    logger.debug(f"Found person contact with email {to_email}: {person.get_name()}")
                elif church:
                    church_id = church.id
                    is_contact = True
                    logger.debug(f"Found church contact with email {to_email}: {church.get_access_name()}")
                    logger.debug(f"Found church contact with email {to_email}: {church.get_name()}")
            
            if not is_contact:
                logger.warning(f"Recipient {to_email} is not a contact in the CRM system")
                return jsonify({
                    'success': False,
                    'message': 'Recipient is not a contact in the CRM system'
                }), 400
        
        # Build Gmail service
        logger.info("Building Gmail service")
        gmail_service = build_gmail_service(token)
        if not gmail_service:
            logger.error("Failed to build Gmail service")
            return jsonify({
                'success': False,
                'message': 'Failed to build Gmail service. Please check your Google account permissions and try again.'
            }), 500
        
        # Get sender email (from authenticated user)
        try:
            logger.debug("Getting user profile from Gmail")
            profile = gmail_service.users().getProfile(userId='me').execute()
            sender_email = profile['emailAddress']
            logger.info(f"Sender email from Gmail API: {sender_email}")
            
            # Get user's name from session or database
            from routes.google_auth import get_current_user_id
            user_id = get_current_user_id()
            user_email = session.get('user_email')
            
            # If we have a user_email in the session, verify it matches the Gmail profile
            if user_email and user_email != sender_email:
                logger.warning(f"Session email ({user_email}) doesn't match Gmail profile email ({sender_email})")
                # We'll still use the Gmail profile email as it's the one authorized to send
            
            logger.info(f"Using sender email: {sender_email} for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Check if this is a permission error
            if 'insufficient permission' in str(e).lower() or 'access not granted' in str(e).lower():
                return jsonify({
                    'success': False,
                    'message': 'Your Google account does not have permission to send emails. Please reconnect your account with the proper permissions.'
                }), 403
                
            sender_email = os.environ.get('DEFAULT_EMAIL', 'noreply@mobilizecrm.com')
            logger.debug(f"Using default sender email: {sender_email}")
        
        # Create email message
        logger.info("Creating email message")
        email_message = create_message(
            sender=sender_email,
            to=to_email,
            subject=subject,
            message_text=message_text,
            html_content=html_content,
            signature_html=signature_html
        )
        
        # Send email
        logger.info("Sending email via Gmail API")
        try:
            sent_message = send_message(gmail_service, 'me', email_message)
            logger.info(f"Email sent successfully, message ID: {sent_message['id']}")
            logger.debug(f"Full message response: {sent_message}")
        except Exception as e:
            logger.error(f"Error sending email via Gmail API: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Check for specific error types
            error_str = str(e).lower()
            if 'insufficient permission' in error_str:
                return jsonify({
                    'success': False,
                    'message': 'Your Google account does not have permission to send emails. Please reconnect your account with the proper permissions.'
                }), 403
            elif 'invalid credentials' in error_str or 'token expired' in error_str:
                return jsonify({
                    'success': False,
                    'message': 'Your Google authentication has expired. Please sign in again.'
                }), 401
            else:
                return jsonify({
                    'success': False,
                    'message': f'Error sending email: {str(e)}'
                }), 500
        
        # Log communication in database
        logger.info("Logging communication in database")
        with session_scope() as session:
            try:
                new_communication = Communication(
                    type='Email',
                    message=message_text,
                    date_sent=datetime.now(),
                    person_id=person_id,
                    church_id=church_id,
                    gmail_message_id=sent_message['id'],
                    gmail_thread_id=sent_message['threadId'],
                    email_status='sent',
                    subject=subject,
                    last_synced_at=datetime.now(),
                    user_id=user_id
                )
                session.add(new_communication)
                session.commit()
                logger.info(f"Communication logged successfully with ID: {new_communication.id}")
            except Exception as e:
                logger.error(f"Error logging communication: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Still return success since the email was sent
            
            return jsonify({
                'success': True,
                'message': 'Email sent successfully',
                'gmail_message_id': sent_message['id'],
                'gmail_thread_id': sent_message['threadId']
            })
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error sending email: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/draft', methods=['POST'])
@auth_required
def create_email_draft():
    """Create an email draft through Gmail API"""
    # Get Google access token from header
    token = get_access_token_from_header()
    if not token:
        return jsonify({
            'success': False,
            'message': 'Google access token required'
        }), 401
    
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['to', 'subject', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get email data
        to_email = data['to']
        subject = data['subject']
        message_text = data['message']
        html_content = data.get('html_content')
        person_id = data.get('person_id')
        church_id = data.get('church_id')
        
        # Verify the recipient is a contact in our system
        with session_scope() as session:
            is_contact = False
            
            # Check if we have a person_id or church_id
            if person_id or church_id:
                is_contact = True
            else:
                # Check if the email belongs to a contact
                person = session.query(Person).filter(Person.email == to_email).first()
                church = session.query(Church).filter(Church.email == to_email).first()
                
                if person:
                    person_id = person.id
                    is_contact = True
                elif church:
                    church_id = church.id
                    is_contact = True
            
            if not is_contact:
                return jsonify({
                    'success': False,
                    'message': 'Recipient is not a contact in the CRM system'
                }), 400
        
        # Build Gmail service
        gmail_service = build_gmail_service(token)
        if not gmail_service:
            return jsonify({
                'success': False,
                'message': 'Failed to build Gmail service'
            }), 500
        
        # Get sender email (from authenticated user)
        try:
            profile = gmail_service.users().getProfile(userId='me').execute()
            sender_email = profile['emailAddress']
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            sender_email = os.environ.get('DEFAULT_EMAIL', 'noreply@mobilizecrm.com')
        
        # Create email message
        email_message = create_message(
            sender=sender_email,
            to=to_email,
            subject=subject,
            message_text=message_text,
            html_content=html_content
        )
        
        # Create draft
        draft = create_draft(gmail_service, 'me', email_message)
        
        # Log communication in database
        with session_scope() as session:
            new_communication = Communication(
                type='Email',
                message=message_text,
                date_sent=datetime.now(),
                person_id=person_id,
                church_id=church_id,
                gmail_message_id=draft['message']['id'],
                gmail_thread_id=draft['message']['threadId'],
                email_status='draft',
                subject=subject,
                last_synced_at=datetime.now(),
                user_id=user_id
            )
            session.add(new_communication)
            
            return jsonify({
                'success': True,
                'message': 'Email draft created successfully',
                'draft_id': draft['id'],
                'gmail_message_id': draft['message']['id'],
                'gmail_thread_id': draft['message']['threadId']
            })
    
    except Exception as e:
        logger.error(f"Error creating email draft: {e}")
        return jsonify({
            'success': False,
            'message': f'Error creating email draft: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/send-draft/<string:draft_id>', methods=['POST'])
@auth_required
def send_email_draft(draft_id):
    """Send an email draft through Gmail API"""
    # Get Google access token from header
    token = get_access_token_from_header()
    if not token:
        return jsonify({
            'success': False,
            'message': 'Google access token required'
        }), 401
    
    try:
        # Build Gmail service
        gmail_service = build_gmail_service(token)
        if not gmail_service:
            return jsonify({
                'success': False,
                'message': 'Failed to build Gmail service'
            }), 500
        
        # Send draft
        sent_message = send_draft(gmail_service, 'me', draft_id)
        
        # Update communication in database
        with session_scope() as session:
            # Find the communication with the draft message ID
            communication = session.query(Communication).filter(
                Communication.gmail_message_id == sent_message['id'],
                Communication.email_status == 'draft'
            ).first()
            
            if communication:
                communication.email_status = 'sent'
                communication.last_synced_at = datetime.now()
            
            return jsonify({
                'success': True,
                'message': 'Email draft sent successfully',
                'gmail_message_id': sent_message['id'],
                'gmail_thread_id': sent_message['threadId']
            })
    
    except Exception as e:
        logger.error(f"Error sending email draft: {e}")
        return jsonify({
            'success': False,
            'message': f'Error sending email draft: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/recent-emails', methods=['GET'])
@auth_required
def get_recent_emails():
    """Get recent emails from Gmail that are related to contacts in the CRM"""
    # Get Google access token from header
    token = get_access_token_from_header()
    if not token:
        return jsonify({
            'success': False,
            'message': 'Google access token required'
        }), 401
    
    try:
        # Build Gmail service
        gmail_service = build_gmail_service(token)
        if not gmail_service:
            return jsonify({
                'success': False,
                'message': 'Failed to build Gmail service'
            }), 500
        
        # Get query parameters
        max_results = request.args.get('max_results', 50, type=int)
        query = request.args.get('query', '')
        
        # Get all contacts' email addresses
        with session_scope() as session:
            people = session.query(Person).filter(Person.email != None).all()
            churches = session.query(Church).filter(Church.email != None).all()
            
            contact_emails = set()
            for person in people:
                if person.email:
                    contact_emails.add(person.email.lower())
            
            for church in churches:
                if church.email:
                    contact_emails.add(church.email.lower())
            
            # Build query to filter by contacts
            contact_query = ""
            if contact_emails:
                # Create a query to find emails from or to any of our contacts
                # We'll filter more precisely after retrieving the messages
                if query:
                    query = f"({query}) AND ("
                else:
                    query = "("
                
                # Add a few sample contacts to the query (Gmail has query length limits)
                sample_contacts = list(contact_emails)[:5]  # Take a few contacts for the query
                for i, email in enumerate(sample_contacts):
                    if i > 0:
                        query += " OR "
                    query += f"from:{email} OR to:{email}"
                
                query += ")"
        
        # List messages with the contact-filtered query
        messages = list_messages(gmail_service, 'me', query)
        
        # Get message details and filter to only include those related to contacts
        email_details = []
        processed_count = 0
        
        for message in messages:
            if processed_count >= max_results:
                break
                
            content = get_message_content(gmail_service, 'me', message['id'])
            if not content:
                continue
            
            # Extract email addresses
            from_email = content['from'].lower()
            if '<' in from_email:
                from_email = from_email.split('<')[1].split('>')[0]
            
            to_email = content['to'].lower()
            if '<' in to_email:
                to_email = to_email.split('<')[1].split('>')[0]
            
            # Check if this email is from or to a contact
            if from_email in contact_emails or to_email in contact_emails:
                email_details.append(content)
                processed_count += 1
        
        return jsonify({
            'success': True,
            'emails': email_details,
            'total_found': len(email_details)
        })
    
    except Exception as e:
        logger.error(f"Error getting recent emails: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting recent emails: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/sync-emails', methods=['POST'])
@auth_required
def sync_emails():
    """Sync emails from Gmail that match user's contacts"""
    return _sync_emails_impl()

def _sync_emails_impl():
    """Implementation of sync_emails without the auth_required decorator"""
    try:
        # Get the current user ID
        from routes.google_auth import get_current_user_id, get_access_token_from_header
        from flask import session
        
        user_id = get_current_user_id()
        user_email = session.get('user_email') if 'user_email' in session else None
        
        # If no user ID from auth, check for X-User-ID header (used by background jobs)
        if not user_id:
            user_id = request.headers.get('X-User-ID')
            if user_id:
                current_app.logger.info(f"Using user ID from X-User-ID header: {user_id}")
            else:
                # Try to get user_id from request body
                if request.is_json and request.json and 'user_id' in request.json:
                    user_id = request.json.get('user_id')
                    current_app.logger.info(f"Using user ID from request body: {user_id}")
                else:
                    current_app.logger.warning("No user ID found for email sync")
                    return jsonify({
                        'success': False,
                        'message': 'User not authenticated'
                    }), 401
        
        # If no user email from session, check request body
        if not user_email and request.is_json and request.json and 'user_email' in request.json:
            user_email = request.json.get('user_email')
            current_app.logger.info(f"Using user email from request body: {user_email}")
        
        current_app.logger.info(f"Syncing emails for user_id: {user_id}, email: {user_email}")
        
        # Get access token
        current_app.logger.debug("Attempting to extract Google access token")
        
        # Try getting from X-Google-Token header first 
        if 'X-Google-Token' in request.headers:
            access_token = request.headers.get('X-Google-Token')
            current_app.logger.info(f"Found token in X-Google-Token header: {access_token[:10]}...")
        else:
            # Fall back to getting token from session or database
            access_token = get_access_token_from_header()
            
        if not access_token:
            current_app.logger.warning(f"No Google access token found for user {user_id}")
            return jsonify({
                'success': False,
                'message': 'No Google access token found'
            }), 400
            
        # Log the start of the sync process
        current_app.logger.info(f"Starting Gmail sync for user {user_id}")
        
        try:
            # Get all contacts (people and churches) with email addresses
            with session_scope() as session:
                people_with_email = session.query(Person).filter(Person.email != None, Person.email != '').all()
                church_with_email = session.query(Church).filter(Church.email != None, Church.email != '').all()
                
                all_contacts_emails = []
                # Add person emails
                for person in people_with_email:
                    if person.email and person.email.strip():
                        all_contacts_emails.append(person.email.lower())
                
                # Add church emails
                for church in church_with_email:
                    if church.email and church.email.strip():
                        all_contacts_emails.append(church.email.lower())
                
                if not all_contacts_emails:
                    return jsonify({
                        'success': False,
                        'message': 'No contacts with email found'
                    }), 400
                    
                # Get existing message IDs to avoid duplicates
                existing_message_ids = session.query(Communication.gmail_message_id).filter(
                    Communication.gmail_message_id != None
                ).all()
                
                # Convert to a set for faster lookups
                existing_message_ids = {id[0] for id in existing_message_ids if id[0]}
                
                current_app.logger.info(f"Found {len(existing_message_ids)} already synced messages")
                current_app.logger.info(f"Searching for emails for contacts: {', '.join(all_contacts_emails[:5])}{'...' if len(all_contacts_emails) > 5 else ''}")
                
                # Build query to find emails from or to contacts
                query_parts = []

                # Get user's email from Google API for more targeted searching
                user_email_str = None
                try:
                    credentials = Credentials(token=access_token)
                    user_info_service = build('oauth2', 'v2', credentials=credentials)
                    user_info = user_info_service.userinfo().get().execute()
                    if 'email' in user_info:
                        user_email_str = user_info['email']
                        current_app.logger.debug(f"Found user email: {user_email_str}")
                except Exception as e:
                    current_app.logger.warning(f"Unable to get user email from Google API: {e}")

                # If we have the user's email, build more targeted queries
                if user_email_str:
                    # Emails FROM contacts TO the user
                    for contact_email in all_contacts_emails:
                        query_parts.append(f"(from:{contact_email} AND to:{user_email_str})")
                    
                    # Emails FROM the user TO contacts
                    for contact_email in all_contacts_emails:
                        query_parts.append(f"(from:{user_email_str} AND to:{contact_email})")
                else:
                    # Fallback to the simpler but less precise approach
                    # Find emails FROM any contact 
                    from_queries = [f"from:{email}" for email in all_contacts_emails]
                    # Find emails TO any contact
                    to_queries = [f"to:{email}" for email in all_contacts_emails]
                    query_parts = from_queries + to_queries

                # Combine all queries with OR
                query = " OR ".join(query_parts)
                current_app.logger.debug(f"Gmail search query: {query}")
            
            # Setup Gmail service
            token_dict = {
                'token': access_token
            }
            service = build_gmail_service(access_token)
            if not service:
                current_app.logger.error("Failed to build Gmail service")
                return jsonify({
                    'success': False,
                    'message': 'Failed to build Gmail service. Please check your Google account permissions and try again.'
                }), 500

            # Check if we should include historical emails
            include_history = request.headers.get('X-Include-History', '').lower() == 'true'
            if include_history:
                current_app.logger.info("Including historical emails in sync")

            # Get messages matching the query
            messages = list_messages(service, 'me', query)
            current_app.logger.info(f"Found {len(messages) if messages else 0} messages matching query")

            if not messages:
                return jsonify({
                    'success': True,
                    'message': 'No new emails found',
                    'synced_count': 0,
                    'total_messages_found': 0
                })
                
            # Process each message that isn't already synced
            synced_count = 0
            for msg in messages:
                msg_id = msg.get('id')
                
                # Skip if already synced
                if msg_id in existing_message_ids:
                    continue
                
                # Get full message
                message_data = get_message_content(service, 'me', msg_id)
                
                if not message_data:
                    continue
                
                # Extract email addresses
                sender_email = extract_email_address(message_data.get('from', ''))
                recipient_email = extract_email_address(message_data.get('to', ''))
                
                # Log for debugging
                current_app.logger.debug(f"Processing message: ID={msg_id}, From={sender_email}, To={recipient_email}")

                # Only sync emails that are between user and a contact
                user_is_sender = user_email_str and sender_email and sender_email.lower() == user_email_str.lower()
                user_is_recipient = user_email_str and recipient_email and recipient_email.lower() == user_email_str.lower()
                contact_is_sender = sender_email and sender_email.lower() in [email.lower() for email in all_contacts_emails]
                contact_is_recipient = recipient_email and recipient_email.lower() in [email.lower() for email in all_contacts_emails]

                # Modified validation logic:
                # 1. User sending to contact OR
                # 2. Contact sending to user OR
                # 3. Email involves a contact (either as sender or recipient)
                valid_email = (user_is_sender and contact_is_recipient) or \
                              (contact_is_sender and user_is_recipient) or \
                              contact_is_sender or contact_is_recipient

                if not valid_email:
                    current_app.logger.debug(f"Skipping message - not involving any contact: {sender_email} -> {recipient_email}")
                    continue
                
                # Create a new communication record
                communication = Communication(
                    type='Email',
                    message=message_data.get('body', ''),
                    date_sent=datetime.now(),  # Will be overridden below if date available
                    date=datetime.now(),  # Will be overridden below if date available
                    subject=message_data.get('subject', ''),
                    gmail_message_id=msg_id,
                    gmail_thread_id=message_data.get('threadId'),
                    user_id=user_id,  # Ensure user_id is set
                    direction='inbound' if contact_is_sender else 'outbound'  # Set direction based on sender
                )
                
                # Parse date if available
                if message_data.get('date'):
                    try:
                        # Try parsing ISO format first
                        parsed_date = datetime.fromisoformat(message_data.get('date').replace('Z', '+00:00'))
                        communication.date_sent = parsed_date
                        communication.date = parsed_date
                    except ValueError:
                        try:
                            # Try parsing email format
                            from email.utils import parsedate_to_datetime
                            parsed_date = parsedate_to_datetime(message_data.get('date'))
                            communication.date_sent = parsed_date
                            communication.date = parsed_date
                        except Exception as e:
                            # Default to current date if parsing fails
                            current_app.logger.error(f"Error parsing date {message_data.get('date')}: {e}")
                            now = datetime.now()
                            communication.date_sent = now
                            communication.date = now
                else:
                    now = datetime.now()
                    communication.date_sent = now
                    communication.date = now
                    
                # Link to person/church if sender/recipient matches
                if contact_is_sender:
                    # Find matching person or church
                    person = session.query(Person).filter(func.lower(Person.email) == sender_email.lower()).first()
                    church = session.query(Church).filter(func.lower(Church.email) == sender_email.lower()).first()
                    
                    if person:
                        communication.person_id = person.id
                    elif church:
                        communication.church_id = church.id
                
                elif contact_is_recipient:
                    # Find matching person or church
                    person = session.query(Person).filter(func.lower(Person.email) == recipient_email.lower()).first()
                    church = session.query(Church).filter(func.lower(Church.email) == recipient_email.lower()).first()
                    
                    if person:
                        communication.person_id = person.id
                    elif church:
                        communication.church_id = church.id
                
                session.add(communication)
                synced_count += 1
            
            # Commit all changes
            session.commit()
            
            # Store the result in the application config for status checks
            current_app.config['LAST_SYNC_RESULT'] = {
                'success': True,
                'message': f'Successfully synced {synced_count} emails',
                'synced_count': synced_count,
                'total_messages_found': len(messages) if messages else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify({
                'success': True,
                'message': f'Successfully synced {synced_count} emails',
                'synced_count': synced_count,
                'total_messages_found': len(messages) if messages else 0
            })
            
        except Exception as inner_e:
            # Log the detailed error
            current_app.logger.error(f"Error during Gmail sync process: {str(inner_e)}")
            current_app.logger.error(traceback.format_exc())
            
            # Store the error in the application config
            current_app.config['LAST_SYNC_RESULT'] = {
                'success': False,
                'message': f'Error during sync: {str(inner_e)}',
                'synced_count': 0,
                'total_messages_found': 0,
                'timestamp': datetime.now().isoformat(),
                'error': str(inner_e)
            }
            
            return jsonify({
                'success': False,
                'message': f'Error syncing emails: {str(inner_e)}'
            }), 500
    
    except Exception as e:
        logger.error(f"Error syncing emails: {e}")
        logger.error(traceback.format_exc())
        
        # Store the error in the application config
        current_app.config['LAST_SYNC_RESULT'] = {
            'success': False,
            'message': f'Error in sync setup: {str(e)}',
            'synced_count': 0,
            'total_messages_found': 0,
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }
        
        return jsonify({
            'success': False,
            'message': f'Error syncing emails: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/force-sync-emails', methods=['GET'])
@auth_required
def force_sync_emails():
    """Force sync emails for testing purposes (temporary debug endpoint)"""
    from utils.background_jobs import sync_gmail_emails
    from routes.google_auth import get_current_user_id
    
    try:
        # Get the user ID from auth or header
        user_id = get_current_user_id() or request.headers.get('X-User-ID')
        
        if not user_id:
            current_app.logger.warning("No user ID found for force email sync")
            return jsonify({
                'success': False,
                'message': 'User not authenticated'
            }), 401
            
        # Get access token if not in header
        access_token = request.headers.get('X-Google-Token') or get_access_token_from_header()
        
        if not access_token:
            current_app.logger.warning(f"No Google access token found for user {user_id}")
            return jsonify({
                'success': False,
                'message': 'No Google access token found'
            }), 400
        
        # Run the sync job directly
        current_app.logger.info(f"Manually triggering Gmail email sync for user {user_id}")
        
        # Call the sync_emails endpoint directly with the user ID and token
        try:
            # Create a new request context
            with current_app.test_request_context(
                path='/api/gmail/sync-emails',
                method='POST',
                headers={
                    'X-User-ID': user_id,
                    'X-Google-Token': access_token
                }
            ):
                # Call the _sync_emails_impl function directly to bypass auth_required
                current_app.logger.info("Calling _sync_emails_impl function directly")
                result = _sync_emails_impl()
                current_app.logger.info(f"Sync result: {result}")
                
                # Check if the result is a redirect (302)
                if hasattr(result, 'status_code') and result.status_code == 302:
                    current_app.logger.warning("Received redirect response from sync_emails, likely due to authentication")
                    # Return a JSON response instead of the redirect
                    return jsonify({
                        'success': False,
                        'message': 'Authentication required',
                        'redirect_url': result.location
                    }), 401
                
                # Store the last run result in the application config for status checks
                if hasattr(result, 'json'):
                    try:
                        result_data = result.json
                        if callable(result_data):
                            result_data = result_data()
                        
                        # Check if result_data is None before trying to access it
                        if result_data is not None:
                            current_app.config['LAST_SYNC_RESULT'] = {
                                'success': result_data.get('success', False),
                                'message': result_data.get('message', ''),
                                'synced_count': result_data.get('synced_count', 0),
                                'timestamp': datetime.now().isoformat()
                            }
                        else:
                            current_app.logger.warning("Result data is None, cannot update LAST_SYNC_RESULT")
                            current_app.config['LAST_SYNC_RESULT'] = {
                                'success': False,
                                'message': 'Sync completed but returned no data',
                                'synced_count': 0,
                                'timestamp': datetime.now().isoformat()
                            }
                    except Exception as json_error:
                        current_app.logger.error(f"Error processing JSON result: {json_error}")
                        current_app.config['LAST_SYNC_RESULT'] = {
                            'success': False,
                            'message': f'Error processing sync result: {str(json_error)}',
                            'synced_count': 0,
                            'timestamp': datetime.now().isoformat()
                        }
                
                return result
        except Exception as e:
            current_app.logger.error(f"Error calling _sync_emails_impl function: {e}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Error syncing emails: {str(e)}'
            }), 500
    
    except Exception as e:
        current_app.logger.error(f"Error triggering manual Gmail sync: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error triggering manual Gmail sync: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/sync-status', methods=['GET'])
@auth_required
def get_sync_status():
    """Check if there's a background email sync in progress"""
    try:
        from utils.background_jobs import is_job_running
        from routes.google_auth import get_current_user_id
        
        # Get the user ID
        user_id = get_current_user_id() or request.headers.get('X-User-ID')
        
        # Check if the background sync job is running
        background_sync = is_job_running('sync_gmail_emails')
        
        # Check if there's a manual sync in progress from session
        manual_sync = False  # We don't track manual syncs right now
        
        # Get last run result if available
        last_run_result = current_app.config.get('LAST_SYNC_RESULT', {})
        
        response_data = {
            'success': True,
            'sync_in_progress': background_sync,
            'manual_sync_in_progress': manual_sync,
            'user_id': user_id,
            'last_run_success': last_run_result.get('success'),
            'last_run_message': last_run_result.get('message'),
            'last_run_timestamp': last_run_result.get('timestamp'),
            'last_run_results': {
                'processed': last_run_result.get('total_messages_found', 0),
                'new_communications': last_run_result.get('synced_count', 0)
            } if last_run_result else None
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error checking sync status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error checking sync status: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/force-sync-emails-with-history', methods=['GET'])
@auth_required
def force_sync_emails_with_history():
    """Force sync emails including historical emails (useful for initial setup)"""
    from utils.background_jobs import sync_gmail_emails
    from routes.google_auth import get_current_user_id
    
    try:
        # Get the user ID from auth or header
        user_id = get_current_user_id() or request.headers.get('X-User-ID')
        
        if not user_id:
            current_app.logger.warning("No user ID found for force email sync with history")
            return jsonify({
                'success': False,
                'message': 'User not authenticated'
            }), 401
            
        # Get access token if not in header
        access_token = request.headers.get('X-Google-Token') or get_access_token_from_header()
        
        if not access_token:
            current_app.logger.warning(f"No Google access token found for user {user_id}")
            return jsonify({
                'success': False,
                'message': 'No Google access token found'
            }), 400
        
        # Run the sync job directly
        current_app.logger.info(f"Manually triggering Gmail email sync WITH HISTORY for user {user_id}")
        
        # Call the sync_emails endpoint directly with the user ID and token
        try:
            # Create a new request context
            with current_app.test_request_context(
                path='/api/gmail/sync-emails',
                method='POST',
                headers={
                    'X-User-ID': user_id,
                    'X-Google-Token': access_token,
                    'X-Include-History': 'true'  # Special header to indicate we want historical emails
                }
            ):
                # Call the _sync_emails_impl function directly to bypass auth_required
                current_app.logger.info("Calling _sync_emails_impl function directly with history flag")
                result = _sync_emails_impl()
                current_app.logger.info(f"Sync result: {result}")
                
                # Check if the result is a redirect (302)
                if hasattr(result, 'status_code') and result.status_code == 302:
                    current_app.logger.warning("Received redirect response from sync_emails, likely due to authentication")
                    # Return a JSON response instead of the redirect
                    return jsonify({
                        'success': False,
                        'message': 'Authentication required',
                        'redirect_url': result.location
                    }), 401
                
                # Store the last run result in the application config for status checks
                if hasattr(result, 'json'):
                    try:
                        result_data = result.json
                        if callable(result_data):
                            result_data = result_data()
                        
                        # Check if result_data is None before trying to access it
                        if result_data is not None:
                            current_app.config['LAST_SYNC_RESULT'] = {
                                'success': result_data.get('success', False),
                                'message': result_data.get('message', ''),
                                'synced_count': result_data.get('synced_count', 0),
                                'timestamp': datetime.now().isoformat()
                            }
                        else:
                            current_app.logger.warning("Result data is None, cannot update LAST_SYNC_RESULT")
                            current_app.config['LAST_SYNC_RESULT'] = {
                                'success': False,
                                'message': 'Sync completed but returned no data',
                                'synced_count': 0,
                                'timestamp': datetime.now().isoformat()
                            }
                    except Exception as json_error:
                        current_app.logger.error(f"Error processing JSON result: {json_error}")
                        current_app.config['LAST_SYNC_RESULT'] = {
                            'success': False,
                            'message': f'Error processing sync result: {str(json_error)}',
                            'synced_count': 0,
                            'timestamp': datetime.now().isoformat()
                        }
                
                return result
        except Exception as e:
            current_app.logger.error(f"Error calling _sync_emails_impl function with history: {e}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Error syncing emails with history: {str(e)}'
            }), 500
    
    except Exception as e:
        current_app.logger.error(f"Error triggering manual Gmail sync with history: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error triggering manual Gmail sync with history: {str(e)}'
        }), 500 

