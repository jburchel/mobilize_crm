from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from models import Session, Communication, Person, Church
from database import db, session_scope
from routes.dashboard import auth_required
from routes.google_auth import get_user_tokens, get_current_user_id
import os
import requests
import traceback

communications_bp = Blueprint('communications_bp', __name__)

@communications_bp.route('/communications')
def communications_route():
    with session_scope() as session:
        communications_list = session.query(Communication).order_by(Communication.date_sent.desc()).all()
        people_list = session.query(Person).all()
        churches_list = session.query(Church).all()
        return render_template('communications.html', 
                             communications=communications_list, 
                             people=people_list, 
                             churches=churches_list)

@communications_bp.route('/communications/all-communications')
def all_communications_route():
    with session_scope() as session:
        # Get filter parameters
        person_id = request.args.get('person_id')
        church_id = request.args.get('church_id')
        
        # Start with a base query
        query = session.query(Communication).order_by(Communication.date_sent.desc())
        
        # Apply filters if provided
        if person_id:
            query = query.filter(Communication.person_id == person_id)
        if church_id:
            query = query.filter(Communication.church_id == church_id)
        
        communications_list = query.all()
        
        # Get filter info for the title
        filter_name = None
        if person_id:
            person = session.query(Person).filter(Person.id == person_id).first()
            if person:
                filter_name = f"{person.first_name} {person.last_name}"
        elif church_id:
            church = session.query(Church).filter(Church.id == church_id).first()
            if church:
                filter_name = church.church_name
        
        return render_template('all_communications.html', 
                             communications=communications_list,
                             filter_name=filter_name)

@communications_bp.route('/send_communication', methods=['POST'])
def send_communication_route():
    current_app.logger.info("Received communication submission")
    
    # Check if the request is JSON or form data
    if request.is_json:
        current_app.logger.debug("Processing JSON request")
        form_data = request.json
        current_app.logger.debug(f"JSON data: {form_data}")
    else:
        current_app.logger.debug("Processing form data request")
        form_data = request.form
        current_app.logger.debug(f"Form data: {form_data}")
    
    with session_scope() as session:
        try:
            comm_type = form_data.get('type')
            message = form_data.get('message')
            person_id = form_data.get('person_id') or None
            church_id = form_data.get('church_id') or None
            date_sent = datetime.now()
            subject = form_data.get('subject', 'Mobilize CRM Communication')
            
            # Validate required fields
            if not comm_type:
                current_app.logger.error("Missing required field: type")
                return jsonify({
                    'success': False,
                    'message': 'Communication type is required'
                }), 400
                
            if not message:
                current_app.logger.error("Missing required field: message")
                return jsonify({
                    'success': False,
                    'message': 'Message content is required'
                }), 400
            
            current_app.logger.info(f"Processing {comm_type} communication")
            current_app.logger.debug(f"Person ID: {person_id}, Church ID: {church_id}")

            # Validate that either person_id or church_id is provided
            if not person_id and not church_id:
                current_app.logger.warning("No recipient (person or church) selected")
                return jsonify({
                    'success': False,
                    'message': 'Please select a person or church as the recipient'
                }), 400

            # Send Email if type is Email
            if comm_type == 'Email':
                to_email = None
                recipient_name = None
                
                if person_id:
                    person = session.query(Person).filter_by(id=person_id).first()
                    if person:
                        to_email = person.email
                        recipient_name = person.get_name()
                        current_app.logger.debug(f"Found person: {recipient_name}, email: {to_email}")
                elif church_id:
                    church = session.query(Church).filter_by(id=church_id).first()
                    if church:
                        to_email = church.email
                        recipient_name = church.get_name()
                        current_app.logger.debug(f"Found church: {recipient_name}, email: {to_email}")

                if not to_email:
                    current_app.logger.warning(f"No email found for selected recipient")
                    return jsonify({
                        'success': False,
                        'message': 'The selected recipient does not have an email address'
                    }), 400

                current_app.logger.info(f"Sending email to {recipient_name} ({to_email})")

                # Try to use Gmail API if user is connected with Google
                tokens = get_user_tokens()
                current_app.logger.debug(f"Retrieved tokens: {tokens is not None}")
                
                if tokens:
                    # Check if we have a token key or access_token key (different formats)
                    access_token = tokens.get('token') or tokens.get('access_token')
                    
                    if access_token:
                        current_app.logger.info("Using Gmail API for sending email")
                        current_app.logger.debug(f"Access token: {access_token[:10]}...")
                        try:
                            # Prepare data for Gmail API
                            email_data = {
                                'to': to_email,
                                'subject': subject,
                                'message': message,
                                'person_id': person_id,
                                'church_id': church_id,
                                'signature_id': form_data.get('signature_id')
                            }
                            
                            # Call Gmail API endpoint
                            api_url = url_for('gmail_api.send_email', _external=True)
                            current_app.logger.info(f"Calling Gmail API at: {api_url}")
                            current_app.logger.debug(f"Email data: {email_data}")
                            
                            # Add more detailed logging and error handling
                            try:
                                headers = {
                                    'Content-Type': 'application/json',
                                    'X-Google-Token': access_token
                                }
                                current_app.logger.debug(f"Request headers: {headers}")
                                
                                response = requests.post(api_url, json=email_data, headers=headers)
                                current_app.logger.debug(f"Gmail API response status: {response.status_code}")
                                
                                # Log the full response for debugging
                                try:
                                    response_data = response.json()
                                    current_app.logger.debug(f"Gmail API response: {response_data}")
                                except:
                                    current_app.logger.debug(f"Gmail API raw response: {response.text}")
                                
                                if response.status_code == 200 and response.json().get('success'):
                                    # Email sent successfully via Gmail API
                                    gmail_data = response.json()
                                    current_app.logger.info(f"Email sent successfully via Gmail API. Message ID: {gmail_data.get('gmail_message_id')}")
                                    
                                    # Create communication record
                                    new_communication = Communication(
                                        type=comm_type,
                                        message=message,
                                        date_sent=date_sent,
                                        person_id=person_id,
                                        church_id=church_id,
                                        subject=subject,
                                        gmail_message_id=gmail_data.get('gmail_message_id'),
                                        gmail_thread_id=gmail_data.get('gmail_thread_id'),
                                        email_status='sent',
                                        last_synced_at=datetime.now()
                                    )
                                    session.add(new_communication)
                                    session.commit()
                                    current_app.logger.info(f"Communication record created with ID: {new_communication.id}")
                                    
                                    return jsonify({
                                        'success': True,
                                        'message': f'Email sent successfully to {recipient_name}'
                                    })
                                else:
                                    # Gmail API call failed
                                    error_msg = response.json().get('message', 'Unknown error')
                                    current_app.logger.error(f"Gmail API error: {error_msg}")
                                    
                                    # Create communication record with failed status
                                    new_communication = Communication(
                                        type=comm_type,
                                        message=message,
                                        date_sent=date_sent,
                                        person_id=person_id,
                                        church_id=church_id,
                                        subject=subject,
                                        email_status='failed',
                                        last_synced_at=datetime.now()
                                    )
                                    session.add(new_communication)
                                    session.commit()
                                    current_app.logger.info(f"Failed communication record created with ID: {new_communication.id}")
                                    
                                    return jsonify({
                                        'success': False,
                                        'message': f'Failed to send email: {error_msg}'
                                    }), 500
                            except requests.RequestException as e:
                                current_app.logger.error(f"Request error calling Gmail API: {str(e)}")
                                current_app.logger.error(traceback.format_exc())
                                return jsonify({
                                    'success': False,
                                    'message': f'Error connecting to Gmail API: {str(e)}'
                                }), 500
                        except Exception as e:
                            current_app.logger.error(f"Error using Gmail API: {str(e)}")
                            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
                            # Fall back to SMTP
                    else:
                        current_app.logger.warning("Tokens found but missing access_token/token")
                        current_app.logger.debug(f"Available token keys: {tokens.keys()}")
                else:
                    current_app.logger.info("No Google tokens available, using SMTP")
                
                # Fall back to SMTP if Gmail API is not available or fails
                sender_email = os.environ.get('SMTP_EMAIL')
                sender_password = os.environ.get('SMTP_PASSWORD')
                
                if not sender_email or not sender_password:
                    current_app.logger.warning("Email credentials not configured")
                    current_app.logger.info("Logging communication without sending email")
                    # Still log the communication even if email can't be sent
                else:
                    try:
                        msg = MIMEText(message)
                        msg['Subject'] = subject
                        msg['From'] = sender_email
                        msg['To'] = to_email
                        
                        current_app.logger.debug(f"Sending email via SMTP: {sender_email} -> {to_email}")
                        
                        with smtplib.SMTP('smtp.gmail.com', 587) as server:
                            server.starttls()
                            server.login(sender_email, sender_password)
                            server.send_message(msg)
                            current_app.logger.info(f"Email sent via SMTP to {recipient_name}")
                    except Exception as e:
                        current_app.logger.error(f"Email error: {str(e)}")
                        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
                        # Still log the communication even if email fails

            # Log the communication
            current_app.logger.info(f"Logging communication in database")
            new_communication = Communication(
                type=comm_type,
                message=message,
                date_sent=date_sent,
                person_id=person_id,
                church_id=church_id,
                subject=subject
            )
            session.add(new_communication)
            session.commit()
            current_app.logger.info(f"Communication logged successfully with ID: {new_communication.id}")
            
            # If we're handling a JSON request, return a JSON response
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': f'Communication sent successfully to {recipient_name}'
                })
            # Otherwise, redirect to the communications page
            return redirect(url_for('communications_bp.communications_route'))
            
        except Exception as e:
            current_app.logger.error(f"Error in send_communication_route: {str(e)}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500

@communications_bp.route('/communications/api/people')
def get_people_api():
    with session_scope() as session:
        people_list = session.query(Person).all()
        people_data = [{'id': person.id, 'first_name': person.first_name, 'last_name': person.last_name} for person in people_list]
        return jsonify(people_data)

@communications_bp.route('/communications/api/churches')
def api_get_churches():
    with session_scope() as session:
        churches = session.query(Church).all()
        return jsonify({
            'success': True,
            'churches': [{'id': church.id, 'name': church.get_name()} for church in churches]
        })

@communications_bp.route('/communications/<int:comm_id>')
def view_communication(comm_id):
    """View a single communication with reply/forward options"""
    with session_scope() as session:
        communication = session.query(Communication).filter_by(id=comm_id).first()
        
        if not communication:
            return render_template('error.html', 
                                  error_title="Communication Not Found",
                                  error_message="The requested communication could not be found."), 404
        
        # Get recipient information
        recipient = None
        if communication.person_id:
            recipient = session.query(Person).filter_by(id=communication.person_id).first()
        elif communication.church_id:
            recipient = session.query(Church).filter_by(id=communication.church_id).first()
        
        # Get all people and churches for the reply form
        people = session.query(Person).all()
        churches = session.query(Church).all()
        
        return render_template('view_communication.html',
                              communication=communication,
                              recipient=recipient,
                              people=people,
                              churches=churches)

@communications_bp.route('/communications/reply/<int:comm_id>', methods=['POST'])
def reply_to_communication(comm_id):
    """Handle reply to a specific communication"""
    if not request.is_json:
        return jsonify({
            'success': False,
            'message': 'JSON request expected'
        }), 400
    
    data = request.json
    reply_type = data.get('reply_type', 'reply')  # reply, reply_all, or forward
    message = data.get('message')
    
    if not message:
        return jsonify({
            'success': False,
            'message': 'Message content is required'
        }), 400
    
    with session_scope() as session:
        # Get the original communication
        original = session.query(Communication).filter_by(id=comm_id).first()
        if not original:
            return jsonify({
                'success': False,
                'message': 'Original communication not found'
            }), 404
        
        # Determine recipient
        recipient_person_id = None
        recipient_church_id = None
        to_email = None
        recipient_name = None
        
        if reply_type == 'forward':
            # For forwarding, use the explicitly provided recipient
            recipient_person_id = data.get('person_id')
            recipient_church_id = data.get('church_id')
            
            if recipient_person_id:
                person = session.query(Person).filter_by(id=recipient_person_id).first()
                if person and person.email:
                    to_email = person.email
                    recipient_name = person.get_name()
            elif recipient_church_id:
                church = session.query(Church).filter_by(id=recipient_church_id).first()
                if church and church.email:
                    to_email = church.email
                    recipient_name = church.get_name()
        else:
            # For replies, use the original sender
            if original.email_status == 'received':
                # If we received it, reply to the original person/church
                recipient_person_id = original.person_id
                recipient_church_id = original.church_id
                
                if recipient_person_id:
                    person = session.query(Person).filter_by(id=recipient_person_id).first()
                    if person and person.email:
                        to_email = person.email
                        recipient_name = person.get_name()
                elif recipient_church_id:
                    church = session.query(Church).filter_by(id=recipient_church_id).first()
                    if church and church.email:
                        to_email = church.email
                        recipient_name = church.get_name()
            else:
                # If we sent it, reply to the same recipient
                recipient_person_id = original.person_id
                recipient_church_id = original.church_id
                
                if recipient_person_id:
                    person = session.query(Person).filter_by(id=recipient_person_id).first()
                    if person and person.email:
                        to_email = person.email
                        recipient_name = person.get_name()
                elif recipient_church_id:
                    church = session.query(Church).filter_by(id=recipient_church_id).first()
                    if church and church.email:
                        to_email = church.email
                        recipient_name = church.get_name()
        
        if not to_email:
            return jsonify({
                'success': False,
                'message': 'Recipient has no email address'
            }), 400
        
        # Prepare subject
        if reply_type == 'forward':
            subject = f"Fw: {original.subject}"
        else:
            subject = f"Re: {original.subject}"
        
        # Try to send via Gmail API
        tokens = get_user_tokens()
        if tokens:
            access_token = tokens.get('token') or tokens.get('access_token')
            if access_token:
                try:
                    # Format the message - include original text for replies
                    formatted_message = message
                    if reply_type != 'forward':
                        # For replies, add the original message below
                        formatted_message += f"\n\n--- Original Message ---\n"
                        formatted_message += f"From: {original.from_name if hasattr(original, 'from_name') else 'Unknown'}\n"
                        formatted_message += f"Date: {original.date_sent}\n"
                        formatted_message += f"Subject: {original.subject}\n\n"
                        formatted_message += original.message
                    
                    # Prepare data for Gmail API
                    email_data = {
                        'to': to_email,
                        'subject': subject,
                        'message': formatted_message,
                        'person_id': recipient_person_id,
                        'church_id': recipient_church_id,
                        'signature_id': data.get('signature_id'),
                        'gmail_thread_id': original.gmail_thread_id  # Link to original thread
                    }
                    
                    # Call Gmail API endpoint
                    api_url = url_for('gmail_api.send_email', _external=True)
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Google-Token': access_token
                    }
                    
                    response = requests.post(api_url, json=email_data, headers=headers)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        # Create a new communication record
                        new_comm = Communication(
                            type='Email',
                            message=formatted_message,
                            date_sent=datetime.now(),
                            person_id=recipient_person_id,
                            church_id=recipient_church_id,
                            subject=subject,
                            email_status='sent',
                            gmail_message_id=response_data.get('message_id'),
                            gmail_thread_id=original.gmail_thread_id or response_data.get('thread_id')
                        )
                        session.add(new_comm)
                        session.commit()
                        
                        return jsonify({
                            'success': True,
                            'message': f'Successfully sent {reply_type} to {recipient_name}',
                            'communication_id': new_comm.id
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'message': f'Failed to send email: {response.text}'
                        }), 500
                except Exception as e:
                    current_app.logger.error(f"Error sending reply/forward: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
                    return jsonify({
                        'success': False,
                        'message': f'Error sending email: {str(e)}'
                    }), 500
        
        return jsonify({
            'success': False,
            'message': 'Google connection required to send emails'
        }), 400
