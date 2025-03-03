"""
Blueprint for Gmail integration with Communications
"""
from flask import Blueprint, request, jsonify, current_app
from models import Communication, Person, Church, session_scope
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
from routes.google_auth import auth_required, get_access_token_from_header
import logging
from datetime import datetime
import json
import os
import traceback

gmail_api = Blueprint('gmail_api', __name__)
logger = logging.getLogger(__name__)

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
                from models import EmailSignature, session_scope
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
                from models import EmailSignature, session_scope
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
            logger.info(f"Sender email: {sender_email}")
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
                    last_synced_at=datetime.now()
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
                last_synced_at=datetime.now()
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
    """Sync emails with contacts in the CRM"""
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
        
        # Get all contacts' email addresses
        with session_scope() as session:
            people = session.query(Person).filter(Person.email != None).all()
            churches = session.query(Church).filter(Church.email != None).all()
            
            contact_emails = {}
            for person in people:
                if person.email:
                    contact_emails[person.email.lower()] = {'type': 'person', 'id': person.id}
            
            for church in churches:
                if church.email:
                    contact_emails[church.email.lower()] = {'type': 'church', 'id': church.id}
            
            # Build query to find emails from or to any of our contacts
            query = ""
            if contact_emails:
                # Create a query to find emails from or to any of our contacts
                # Using a broader query to catch more emails
                query = "in:inbox OR in:sent newer_than:30d"
                
                # Log the contacts we're searching for
                logger.info(f"Looking for emails involving {len(contact_emails)} contacts")
                for email, info in list(contact_emails.items())[:5]:
                    logger.info(f"Sample contact: {email} ({info['type']} ID: {info['id']})")
            
            # Get recent emails (last 30 days)
            logger.info(f"Gmail query: {query}")
            
            messages = list_messages(gmail_service, 'me', query)
            logger.info(f"Found {len(messages)} messages matching the query")
            
            # Process each message
            synced_count = 0
            for message in messages[:100]:  # Limit to 100 messages to avoid rate limits
                # Check if we already have this message in our database
                existing = session.query(Communication).filter(
                    Communication.gmail_message_id == message['id']
                ).first()
                
                if existing:
                    continue  # Skip if already synced
                
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
                
                # Check if from_email is a contact
                contact_info = None
                email_status = None
                
                if from_email in contact_emails:
                    contact_info = contact_emails[from_email]
                    email_status = 'received'
                elif to_email in contact_emails:
                    contact_info = contact_emails[to_email]
                    email_status = 'sent'
                
                # Process emails related to contacts (both received from contacts and sent to contacts)
                if contact_info and email_status:
                    # Create a new communication record
                    new_communication = Communication(
                        type='Email',
                        message=content['body'],
                        date_sent=datetime.now(),
                        person_id=contact_info['id'] if contact_info['type'] == 'person' else None,
                        church_id=contact_info['id'] if contact_info['type'] == 'church' else None,
                        gmail_message_id=content['id'],
                        gmail_thread_id=content['thread_id'],
                        email_status=email_status,
                        subject=content['subject'],
                        last_synced_at=datetime.now()
                    )
                    session.add(new_communication)
                    synced_count += 1
                    logger.info(f"Synced email: {content['subject']} with {contact_info['type']} ID {contact_info['id']}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully synced {synced_count} emails',
                'synced_count': synced_count,
                'total_messages_found': len(messages)
            })
    
    except Exception as e:
        logger.error(f"Error syncing emails: {e}")
        return jsonify({
            'success': False,
            'message': f'Error syncing emails: {str(e)}'
        }), 500

@gmail_api.route('/api/gmail/force-sync-emails', methods=['GET'])
def force_sync_emails():
    """Force sync emails for testing purposes (temporary debug endpoint)"""
    from utils.background_jobs import sync_gmail_emails
    
    try:
        # Run the sync job directly
        current_app.logger.info("Manually triggering Gmail email sync")
        sync_gmail_emails()
        
        return jsonify({
            'success': True,
            'message': 'Gmail email sync triggered manually'
        })
    
    except Exception as e:
        current_app.logger.error(f"Error triggering manual Gmail sync: {e}")
        return jsonify({
            'success': False,
            'message': f'Error triggering manual Gmail sync: {str(e)}'
        }), 500 