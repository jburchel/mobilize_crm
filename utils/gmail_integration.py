"""
Gmail integration for Mobilize CRM
This module provides functions to interact with Gmail API
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from flask import current_app
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import logging
import json
from datetime import datetime
import traceback
from models import EmailSignature
from database import session_scope

logger = logging.getLogger(__name__)

def build_gmail_service(token):
    """Build a Gmail service object with the provided token"""
    try:
        if not token:
            logger.error("No token provided to build Gmail service")
            return None
            
        logger.debug(f"Building Gmail service with token: {token[:10]}...")
        
        # Log the client ID and secret (partially masked)
        client_id = current_app.config.get('GOOGLE_CLIENT_ID', '')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET', '')
        
        if not client_id or not client_secret:
            logger.error("Missing Google client ID or secret in application config")
            return None
            
        logger.debug(f"Using client ID: {client_id[:10]}... and client secret: {client_secret[:5]}...")
        
        # Define the scopes needed
        scopes = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
        logger.debug(f"Using scopes: {scopes}")
        
        # Try to get refresh token from database
        refresh_token = None
        try:
            from routes.google_auth import get_user_tokens
            tokens = get_user_tokens()
            if tokens and 'refresh_token' in tokens and tokens['refresh_token']:
                refresh_token = tokens['refresh_token']
                logger.debug(f"Found refresh token: {refresh_token[:5]}...")
            else:
                logger.warning("No refresh token found in user tokens")
                if tokens:
                    logger.debug(f"Available token keys: {tokens.keys()}")
        except Exception as e:
            logger.warning(f"Could not retrieve refresh token: {str(e)}")
            logger.warning(traceback.format_exc())
        
        # Create credentials object
        try:
            logger.debug("Creating credentials object")
            credentials = Credentials(
                token=token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes
            )
            logger.debug("Credentials object created successfully")
        except Exception as e:
            logger.error(f"Error creating credentials object: {str(e)}")
            logger.error(traceback.format_exc())
            return None
        
        # Validate token before proceeding
        try:
            import google.auth.transport.requests
            request = google.auth.transport.requests.Request()
            
            # Check if token needs refreshing
            if hasattr(credentials, 'expired') and credentials.expired and credentials.refresh_token:
                logger.info("Token is expired, attempting to refresh")
                try:
                    credentials.refresh(request)
                    logger.info("Token refreshed successfully")
                except Exception as refresh_error:
                    logger.error(f"Error refreshing token: {str(refresh_error)}")
                    logger.error(traceback.format_exc())
                    # Continue anyway, as the build() call will fail if the token is invalid
            
            # Verify token is valid
            auth_info = getattr(credentials, 'id_token', None) or getattr(credentials, 'token', None)
            if not auth_info:
                logger.error("Invalid token - no id_token or access token available")
                return None
                
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            logger.error(traceback.format_exc())
            # Continue anyway, as the build() call will fail if the token is invalid
        
        # Build the Gmail service
        try:
            logger.debug("Creating Gmail service with credentials")
            service = build('gmail', 'v1', credentials=credentials)
            logger.info("Gmail service built successfully")
            
            # Test the service with a simple API call
            try:
                logger.debug("Testing Gmail service with getProfile call")
                profile = service.users().getProfile(userId='me').execute()
                logger.info(f"Gmail service test successful. Email: {profile.get('emailAddress')}")
            except Exception as test_error:
                logger.warning(f"Gmail service test failed: {str(test_error)}")
                # Continue anyway, as the service might still work for other operations
            
            return service
        except Exception as build_error:
            logger.error(f"Error building Gmail service: {str(build_error)}")
            logger.error(traceback.format_exc())
            return None
    except Exception as e:
        logger.error(f"Error building Gmail service: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def create_message(sender, to, subject, message_text, html_content=None, signature_html=None):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.
        html_content: HTML version of the message (optional).
        signature_html: HTML signature to append to the message (optional).

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Add plain text version
    message.attach(MIMEText(message_text, 'plain'))
    
    # If no signature was provided, try to get the default signature from the database
    if not signature_html:
        try:
            from routes.google_auth import get_current_user_id
            user_id = get_current_user_id()
            if user_id:
                with session_scope() as db_session:
                    default_signature = db_session.query(EmailSignature).filter_by(
                        user_id=user_id, is_default=True).first()
                    if default_signature:
                        signature_html = default_signature.content
                        logger.info(f"Using default signature: {default_signature.name}")
                    else:
                        # If no default signature, try to get any signature
                        any_signature = db_session.query(EmailSignature).filter_by(
                            user_id=user_id).first()
                        if any_signature:
                            signature_html = any_signature.content
                            logger.info(f"No default signature found, using: {any_signature.name}")
                        else:
                            logger.warning(f"No signatures found for user {user_id}")
        except Exception as e:
            logger.warning(f"Error retrieving default signature: {str(e)}")
    
    # Add HTML version if provided or if we have a signature
    if html_content or signature_html:
        # If we have HTML content, use it, otherwise convert plain text to HTML
        if html_content:
            html_body = html_content
        else:
            # Convert plain text to HTML with basic formatting
            html_body = message_text.replace('\n', '<br>')
            html_body = f'<div style="font-family: Arial, sans-serif; font-size: 14px;">{html_body}</div>'
        
        # Append signature if provided
        if signature_html:
            html_body += '<br><br><div class="signature">' + signature_html + '</div>'
        
        message.attach(MIMEText(html_body, 'html'))
    else:
        # Always create an HTML version even without signature
        html_body = message_text.replace('\n', '<br>')
        html_body = f'<div style="font-family: Arial, sans-serif; font-size: 14px;">{html_body}</div>'
        message.attach(MIMEText(html_body, 'html'))

    # Encode the message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': encoded_message}

def create_message_with_attachment(sender, to, subject, message_text, 
                                  html_content=None, file_attachments=None, signature_html=None):
    """Create a message for an email with attachment(s).

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.
        html_content: HTML version of the message (optional).
        file_attachments: List of dictionaries with file info:
                         [{'file_data': binary_data, 'filename': name, 'content_type': type}]
        signature_html: HTML signature to append to the message (optional).

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEMultipart('mixed')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Create the message body as a multipart/alternative container
    msg_alternative = MIMEMultipart('alternative')
    message.attach(msg_alternative)

    # Add plain text version
    msg_alternative.attach(MIMEText(message_text, 'plain'))
    
    # If no signature was provided, try to get the default signature from the database
    if not signature_html:
        try:
            from routes.google_auth import get_current_user_id
            user_id = get_current_user_id()
            if user_id:
                with session_scope() as db_session:
                    default_signature = db_session.query(EmailSignature).filter_by(
                        user_id=user_id, is_default=True).first()
                    if default_signature:
                        signature_html = default_signature.content
                        logger.info(f"Using default signature: {default_signature.name}")
        except Exception as e:
            logger.warning(f"Error retrieving default signature: {str(e)}")
    
    # Add HTML version if provided or if we have a signature
    if html_content or signature_html:
        # If we have HTML content, use it, otherwise convert plain text to HTML
        if html_content:
            html_body = html_content
        else:
            # Convert plain text to HTML with basic formatting
            html_body = message_text.replace('\n', '<br>')
            html_body = f'<div style="font-family: Arial, sans-serif; font-size: 14px;">{html_body}</div>'
        
        # Append signature if provided
        if signature_html:
            html_body += '<br><br><div class="signature">' + signature_html + '</div>'
        
        msg_alternative.attach(MIMEText(html_body, 'html'))

    # Add attachments
    if file_attachments:
        for attachment in file_attachments:
            part = MIMEApplication(
                attachment['file_data'],
                Name=attachment['filename']
            )
            part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
            message.attach(part)

    # Encode the message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': encoded_message}

def send_message(service, user_id, message):
    """Send an email message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        logger.info(f"Sending message via Gmail API for user: {user_id}")
        
        # Log message details (without the raw content which is too large)
        if 'raw' in message:
            raw_length = len(message['raw']) if message['raw'] else 0
            logger.debug(f"Message has raw content of length: {raw_length}")
        
        logger.debug("Calling Gmail API send method")
        message = service.users().messages().send(userId=user_id, body=message).execute()
        logger.info(f"Message sent successfully. Message Id: {message['id']}")
        logger.debug(f"Full message response: {message}")
        return message
    except HttpError as error:
        logger.error(f"An HTTP error occurred while sending message: {error.status_code}")
        logger.error(f"Error details: {error.error_details}")
        logger.error(f"Error content: {error.content}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def get_message(service, user_id, msg_id):
    """Get a specific message from Gmail.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        msg_id: The ID of the message to retrieve.

    Returns:
        A message resource.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()
        return message
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        return None

def list_messages(service, user_id, query=''):
    """List messages in the user's mailbox matching the query.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        query: String used to filter messages returned (optional).

    Returns:
        List of messages that match the criteria.
    """
    try:
        response = service.users().messages().list(userId=user_id, q=query).execute()
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(
                userId=user_id, q=query, pageToken=page_token).execute()
            if 'messages' in response:
                messages.extend(response['messages'])

        return messages
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        return []

def get_message_content(service, user_id, msg_id):
    """Get message content from Gmail API and process it into a usable format"""
    try:
        message = get_message(service, user_id, msg_id)
        if not message:
            return None
            
        # Extract headers
        headers = message['payload']['headers']
        subject = ''
        from_email = ''
        to_email = ''
        date = ''
        thread_id = message.get('threadId', '')
        
        for header in headers:
            name = header['name'].lower()
            if name == 'subject':
                subject = header['value']
            elif name == 'from':
                from_email = header['value']
            elif name == 'to':
                to_email = header['value']
            elif name == 'date':
                date = header['value']
                
        # Extract body
        body = ""
        if 'parts' in message['payload']:
            # Multi-part message
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                        body = text
                        break
                elif part['mimeType'] == 'text/html':
                    # If we don't have plain text yet, use HTML (will be our fallback)
                    if not body and 'data' in part['body']:
                        html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                        # Very simple HTML to text conversion
                        from html.parser import HTMLParser
                        
                        class MLStripper(HTMLParser):
                            def __init__(self):
                                super().__init__()
                                self.reset()
                                self.strict = False
                                self.convert_charrefs = True
                                self.text = []
                            def handle_data(self, d):
                                self.text.append(d)
                            def get_data(self):
                                return ''.join(self.text)
                                
                        stripper = MLStripper()
                        stripper.feed(html)
                        body = stripper.get_data()
                elif 'parts' in part:
                    # Handle nested multipart messages
                    for subpart in part['parts']:
                        if subpart['mimeType'] == 'text/plain':
                            if 'data' in subpart['body']:
                                text = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8', errors='replace')
                                body = text
                                break
                        elif subpart['mimeType'] == 'text/html' and not body:
                            if 'data' in subpart['body']:
                                html = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8', errors='replace')
                                # Strip HTML tags for plain text
                                from html.parser import HTMLParser
                                
                                class MLStripper(HTMLParser):
                                    def __init__(self):
                                        super().__init__()
                                        self.reset()
                                        self.strict = False
                                        self.convert_charrefs = True
                                        self.text = []
                                    def handle_data(self, d):
                                        self.text.append(d)
                                    def get_data(self):
                                        return ''.join(self.text)
                                        
                                stripper = MLStripper()
                                stripper.feed(html)
                                body = stripper.get_data()
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            # Single part message
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8', errors='replace')
            
        # If body is still empty, try one more approach
        if not body:
            try:
                # Try to get full message with raw format to extract body
                full_message = service.users().messages().get(
                    userId=user_id, id=msg_id, format='raw').execute()
                if 'raw' in full_message:
                    # Decode the raw message
                    raw_email = base64.urlsafe_b64decode(full_message['raw'].encode('ASCII'))
                    # Parse the email using email package
                    import email
                    email_message = email.message_from_bytes(raw_email)
                    
                    # Get the body from the email
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == 'text/plain':
                                body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                break
                    else:
                        body = email_message.get_payload(decode=True).decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Error extracting raw email body: {str(e)}")
                
        # Return processed message content
        return {
            'id': msg_id,
            'thread_id': thread_id,
            'subject': subject,
            'from': from_email,
            'to': to_email,
            'body': body,
            'date': date
        }
    except Exception as e:
        logger.error(f"Error getting message content: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def create_draft(service, user_id, message_body):
    """Create a draft email.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        message_body: The body of the email message.

    Returns:
        Draft object, including draft id and message meta data.
    """
    try:
        draft = service.users().drafts().create(userId=user_id, body={'message': message_body}).execute()
        logger.info(f"Draft id: {draft['id']}")
        return draft
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        raise

def send_draft(service, user_id, draft_id):
    """Send a draft email.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        draft_id: The ID of the draft to send.

    Returns:
        Sent Message.
    """
    try:
        message = service.users().drafts().send(userId=user_id, body={'id': draft_id}).execute()
        logger.info(f"Message Id: {message['id']}")
        return message
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        raise 