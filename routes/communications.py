from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from models import Session, Communication, Person, Church, EmailSignature
from database import db, session_scope
from routes.dashboard import auth_required
from routes.google_auth import get_user_tokens, get_current_user_id
import os
import requests
import traceback
from sqlalchemy import func, desc
from utils.gmail_integration import build_gmail_service, create_message, send_message

communications_bp = Blueprint('communications_bp', __name__)

@communications_bp.route('/communications')
def communications_route():
    # Get the current user ID
    user_id = get_current_user_id()
    if not user_id:
        current_app.logger.warning("No user ID found in session, redirecting to login")
        return redirect(url_for('dashboard_bp.dashboard'))
        
    with session_scope() as session:
        # Get filter parameters
        person_id = request.args.get('person_id')
        church_id = request.args.get('church_id')
        
        # Add pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Limit the number of communications per page
        
        # Start with a base query with eager loading of relationships
        query = session.query(Communication).options(
            db.joinedload(Communication.person),
            db.joinedload(Communication.church)
        )
        
        # Apply filters
        if person_id:
            try:
                # Convert person_id to integer if it's a string
                person_id_int = int(person_id)
                query = query.filter(Communication.person_id == person_id_int)
                current_app.logger.debug(f"Filtering communications by person_id={person_id_int}")
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")
            
        if church_id:
            try:
                # Convert church_id to integer if it's a string
                church_id_int = int(church_id)
                query = query.filter(Communication.church_id == church_id_int)
                current_app.logger.debug(f"Filtering communications by church_id={church_id_int}")
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")
        
        # Filter by user_id if it's set in the communication
        # But don't exclude communications without a user_id
        if user_id:
            query = query.filter(Communication.user_id == user_id)
            current_app.logger.debug(f"Filtering communications by user_id={user_id}")
            
        # Order by date_sent, handling NULL values
        query = query.order_by(func.coalesce(Communication.date_sent, datetime(1900, 1, 1)).desc())
        
        # Get total count for pagination info
        total_count = query.count()
        
        # Apply pagination
        query = query.limit(per_page).offset((page - 1) * per_page)
        
        # Execute the query
        all_communications = query.all()
        
        # Filter out duplicates based on gmail_message_id
        # Use a dictionary to keep track of unique communications
        unique_communications = {}
        for comm in all_communications:
            # If the communication has a gmail_message_id, use it as the key
            if comm.gmail_message_id:
                # Only keep the most recent communication for each gmail_message_id
                if comm.gmail_message_id not in unique_communications:
                    unique_communications[comm.gmail_message_id] = comm
                elif comm.date_sent and unique_communications[comm.gmail_message_id].date_sent:
                    # If we already have this message ID, keep the newer one
                    if comm.date_sent > unique_communications[comm.gmail_message_id].date_sent:
                        unique_communications[comm.gmail_message_id] = comm
            else:
                # For communications without a gmail_message_id, use the ID as the key
                unique_communications[f"local_{comm.id}"] = comm
        
        # Convert the dictionary values back to a list and sort by date
        communications_list = sorted(
            unique_communications.values(),
            key=lambda x: x.date_sent if x.date_sent else datetime(1900, 1, 1),
            reverse=True
        )
        
        current_app.logger.debug(f"Found {len(all_communications)} total communications, filtered to {len(communications_list)} unique communications")
        
        # Get the filter name if applicable
        filter_name = None
        if person_id:
            try:
                person_id_int = int(person_id)
                person = session.query(Person).filter(Person.id == person_id_int).first()
                if person:
                    # Use first_name and last_name directly instead of get_name()
                    filter_name = f"{person.first_name} {person.last_name}"
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")
        elif church_id:
            try:
                church_id_int = int(church_id)
                church = session.query(Church).filter(Church.id == church_id_int).first()
                if church:
                    # Use church_name directly instead of get_name()
                    filter_name = church.church_name
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")
        
        # Debug the first few communications
        for i, comm in enumerate(communications_list[:5]):
            current_app.logger.debug(f"Communication {i+1}: ID={comm.id}, Type={comm.type}, Subject={comm.subject}, Person ID={comm.person_id}, User ID={comm.user_id}, Gmail Message ID={comm.gmail_message_id}")
        
        # Fetch people and churches in separate queries to avoid loading all communications
        people_list = session.query(Person.id, Person.first_name, Person.last_name).all()
        churches_list = session.query(Church.id, Church.church_name).all()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Import Python's built-in max and min functions for use in the template
        import builtins
        
        return render_template('communications.html', 
                             communications=communications_list, 
                             people=people_list, 
                             churches=churches_list,
                             filter_name=filter_name,
                             page=page,
                             total_pages=total_pages,
                             has_next=has_next,
                             has_prev=has_prev,
                             total_count=total_count,
                             max=builtins.max,
                             min=builtins.min)

@communications_bp.route('/communications/all-communications')
def all_communications_route():
    # Get the current user ID
    user_id = get_current_user_id()
    if not user_id:
        current_app.logger.warning("No user ID found in session, redirecting to login")
        return redirect(url_for('dashboard_bp.dashboard'))
        
    with session_scope() as session:
        # Get filter parameters
        person_id = request.args.get('person_id')
        church_id = request.args.get('church_id')
        search_term = request.args.get('search', '')
        
        # Add pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Limit the number of communications per page
        
        current_app.logger.debug(f"all_communications_route called with person_id={person_id}, church_id={church_id}, user_id={user_id}, search_term={search_term}, page={page}")
        
        # Start with a base query with eager loading
        query = session.query(Communication).options(
            db.joinedload(Communication.person),
            db.joinedload(Communication.church)
        )
        
        # Apply filters
        if person_id:
            try:
                # Convert person_id to integer if it's a string
                person_id_int = int(person_id)
                query = query.filter(Communication.person_id == person_id_int)
                current_app.logger.debug(f"Filtering communications by person_id={person_id_int}")
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")
            
        if church_id:
            try:
                # Convert church_id to integer if it's a string
                church_id_int = int(church_id)
                query = query.filter(Communication.church_id == church_id_int)
                current_app.logger.debug(f"Filtering communications by church_id={church_id_int}")
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")
        
        # Filter by user_id if it's set in the communication
        # But don't exclude communications without a user_id
        if user_id:
            query = query.filter(Communication.user_id == user_id)
            current_app.logger.debug(f"Filtering communications by user_id={user_id}")
            
        # Apply search term if provided
        if search_term:
            # Join with Person and Church to search in their fields too
            query = query.outerjoin(Person, Communication.person_id == Person.id)
            query = query.outerjoin(Church, Communication.church_id == Church.id)
            
            # Search in multiple fields
            search_filter = (
                func.lower(Communication.message).contains(search_term.lower()) |
                func.lower(Communication.subject).contains(search_term.lower()) |
                func.lower(Person.first_name).contains(search_term.lower()) |
                func.lower(Person.last_name).contains(search_term.lower()) |
                func.lower(Person.email).contains(search_term.lower()) |
                func.lower(Church.church_name).contains(search_term.lower()) |
                func.lower(Church.email).contains(search_term.lower())
            )
            query = query.filter(search_filter)
            
        # Order by date_sent, handling NULL values
        query = query.order_by(func.coalesce(Communication.date_sent, datetime(1900, 1, 1)).desc())
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination
        query = query.limit(per_page).offset((page - 1) * per_page)
        
        # Debug the SQL query
        current_app.logger.debug(f"SQL Query: {query}")
        
        # Execute the query
        all_communications = query.all()
        
        # Filter out duplicates based on gmail_message_id
        # Use a dictionary to keep track of unique communications
        unique_communications = {}
        for comm in all_communications:
            # If the communication has a gmail_message_id, use it as the key
            if comm.gmail_message_id:
                # Only keep the most recent communication for each gmail_message_id
                if comm.gmail_message_id not in unique_communications:
                    unique_communications[comm.gmail_message_id] = comm
                elif comm.date_sent and unique_communications[comm.gmail_message_id].date_sent:
                    # If we already have this message ID, keep the newer one
                    if comm.date_sent > unique_communications[comm.gmail_message_id].date_sent:
                        unique_communications[comm.gmail_message_id] = comm
            else:
                # For communications without a gmail_message_id, use the ID as the key
                unique_communications[f"local_{comm.id}"] = comm
        
        # Convert the dictionary values back to a list and sort by date
        communications_list = sorted(
            unique_communications.values(),
            key=lambda x: x.date_sent if x.date_sent else datetime(1900, 1, 1),
            reverse=True
        )
        
        current_app.logger.debug(f"Found {len(all_communications)} total communications, filtered to {len(communications_list)} unique communications")
        
        # Get filter name if applicable
        filter_name = None
        if person_id:
            try:
                person_id_int = int(person_id)
                person = session.query(Person).filter_by(id=person_id_int).first()
                if person:
                    # Use first_name and last_name directly instead of get_name()
                    filter_name = f"{person.first_name} {person.last_name}"
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")
        elif church_id:
            try:
                church_id_int = int(church_id)
                church = session.query(Church).filter_by(id=church_id_int).first()
                if church:
                    # Use church_name directly instead of get_name()
                    filter_name = church.church_name
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")
                
        current_app.logger.debug(f"Found {len(communications_list)} unique communications with filters: person_id={person_id}, church_id={church_id}")
        
        # Debug the first few communications
        for i, comm in enumerate(communications_list[:5]):
            current_app.logger.debug(f"Communication {i+1}: ID={comm.id}, Type={comm.type}, Subject={comm.subject}, Person ID={comm.person_id}, User ID={comm.user_id}, Gmail Message ID={comm.gmail_message_id}")
        
        # Fetch people and churches in separate queries to avoid loading all communications
        people_list = session.query(Person.id, Person.first_name, Person.last_name).all()
        churches_list = session.query(Church.id, Church.church_name).all()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Import Python's built-in max and min functions for use in the template
        import builtins
        
        return render_template('all_communications.html', 
                             communications=communications_list, 
                             people=people_list, 
                             churches=churches_list,
                             filter_name=filter_name,
                             page=page,
                             total_pages=total_pages,
                             has_next=has_next,
                             has_prev=has_prev,
                             total_count=total_count,
                             max=builtins.max,
                             min=builtins.min)

@communications_bp.route('/communications/send', methods=['POST'])
def send_communication_route():
    """Handle sending a new communication"""
    # Get the current user ID
    user_id = get_current_user_id()
    if not user_id:
        current_app.logger.warning("No user ID found in session, cannot send communication")
        return jsonify({
            'success': False,
            'message': 'User not authenticated'
        }), 401
        
    with session_scope() as session:
        try:
            # Get form data
            if request.is_json:
                form_data = request.json
            else:
                form_data = request.form
                
            # Extract form fields
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
                                'signature_id': form_data.get('signature_id'),
                                'user_id': user_id  # Add user_id to ensure it's saved with the communication
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
                                
                                # Check if the response is a redirect (302)
                                if response.status_code == 302:
                                    redirect_url = response.headers.get('Location')
                                    current_app.logger.info(f"Received redirect to: {redirect_url}")
                                    return redirect(redirect_url)
                                
                                # Check if the response is JSON before trying to parse it
                                content_type = response.headers.get('Content-Type', '')
                                if 'application/json' in content_type:
                                    # Log the full response for debugging
                                    try:
                                        response_data = response.json()
                                        current_app.logger.debug(f"Gmail API response data: {response_data}")
                                        
                                        if response.status_code == 200 and response_data.get('success'):
                                            current_app.logger.info(f"Email sent successfully via Gmail API")
                                            
                                            # If we're handling a JSON request, return the API response
                                            if request.is_json:
                                                return jsonify(response_data)
                                            # Otherwise, redirect to the communications page
                                            return redirect(url_for('communications_bp.communications_route'))
                                        else:
                                            error_msg = response_data.get('message', 'Unknown error')
                                            current_app.logger.error(f"Gmail API error: {error_msg}")
                                            
                                            # Log the communication as failed
                                            new_communication = Communication(
                                                type=comm_type,
                                                message=message,
                                                date_sent=date_sent,
                                                person_id=person_id,
                                                church_id=church_id,
                                                subject=subject,
                                                email_status='failed',
                                                user_id=user_id
                                            )
                                            session.add(new_communication)
                                            session.commit()
                                            current_app.logger.info(f"Failed communication record created with ID: {new_communication.id}")
                                            
                                            return jsonify({
                                                'success': False,
                                                'message': f'Failed to send email: {error_msg}'
                                            }), 500
                                    except ValueError:
                                        current_app.logger.error(f"Gmail API returned a non-JSON response: {response.text}")
                                        return jsonify({
                                            'success': False,
                                            'message': 'Server returned a non-JSON response'
                                        }), 500
                                else:
                                    # Handle non-JSON response (like HTML)
                                    current_app.logger.error(f"Gmail API returned a non-JSON response with content type: {content_type}")
                                    current_app.logger.debug(f"Response text: {response.text[:500]}...")  # Log first 500 chars
                                    
                                    # Instead of assuming success, we need to directly call the Gmail API
                                    current_app.logger.info("Attempting to send email directly via Gmail API")
                                    
                                    try:
                                        # Build Gmail service
                                        gmail_service = build_gmail_service(access_token)
                                        
                                        if not gmail_service:
                                            current_app.logger.error("Failed to build Gmail service")
                                            return jsonify({
                                                'success': False,
                                                'message': 'Failed to build Gmail service. Please check your Google account permissions and try again.'
                                            }), 500
                                        
                                        # Get sender email
                                        profile = gmail_service.users().getProfile(userId='me').execute()
                                        sender_email = profile['emailAddress']
                                        current_app.logger.info(f"Sender email: {sender_email}")
                                        
                                        # Get signature if specified
                                        signature_html = None
                                        signature_id = form_data.get('signature_id')
                                        if signature_id:
                                            try:
                                                with session_scope() as sig_session:
                                                    signature = sig_session.query(EmailSignature).filter_by(id=signature_id).first()
                                                    if signature:
                                                        signature_html = signature.content
                                                        current_app.logger.info(f"Using signature: {signature.name}")
                                            except Exception as sig_error:
                                                current_app.logger.warning(f"Error retrieving signature: {str(sig_error)}")
                                        
                                        # Create email message
                                        email_message = create_message(
                                            sender=sender_email,
                                            to=to_email,
                                            subject=subject,
                                            message_text=message,
                                            signature_html=signature_html
                                        )
                                        
                                        # Send email
                                        sent_message = send_message(gmail_service, 'me', email_message)
                                        current_app.logger.info(f"Email sent successfully, message ID: {sent_message['id']}")
                                        
                                        # Log the communication as sent
                                        new_communication = Communication(
                                            type=comm_type,
                                            message=message,
                                            date_sent=date_sent,
                                            person_id=person_id,
                                            church_id=church_id,
                                            subject=subject,
                                            gmail_message_id=sent_message['id'],
                                            gmail_thread_id=sent_message.get('threadId'),
                                            email_status='sent',
                                            user_id=user_id
                                        )
                                        session.add(new_communication)
                                        session.commit()
                                        current_app.logger.info(f"Communication record created with ID: {new_communication.id}")
                                        
                                        # If we're handling a JSON request, return a success response
                                        if request.is_json:
                                            return jsonify({
                                                'success': True,
                                                'message': 'Email sent successfully',
                                                'gmail_message_id': sent_message['id'],
                                                'gmail_thread_id': sent_message.get('threadId')
                                            })
                                        # Otherwise, redirect to the communications page
                                        return redirect(url_for('communications_bp.communications_route'))
                                    except Exception as direct_send_error:
                                        current_app.logger.error(f"Error sending email directly: {str(direct_send_error)}")
                                        current_app.logger.error(traceback.format_exc())
                                        
                                        # Log the communication as failed
                                        new_communication = Communication(
                                            type=comm_type,
                                            message=message,
                                            date_sent=date_sent,
                                            person_id=person_id,
                                            church_id=church_id,
                                            subject=subject,
                                            email_status='failed',
                                            user_id=user_id
                                        )
                                        session.add(new_communication)
                                        session.commit()
                                        current_app.logger.info(f"Failed communication record created with ID: {new_communication.id}")
                                        
                                        return jsonify({
                                            'success': False,
                                            'message': f'Failed to send email directly: {str(direct_send_error)}'
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
                            # Don't fall back to SMTP - we want to use the user's Gmail account
                            return jsonify({
                                'success': False,
                                'message': f'Error using Gmail API: {str(e)}'
                            }), 500
                    else:
                        current_app.logger.warning("Tokens found but missing access_token/token")
                        current_app.logger.debug(f"Available token keys: {tokens.keys()}")
                        return jsonify({
                            'success': False,
                            'message': 'Your Google account is connected but the access token is missing. Please reconnect your Google account.'
                        }), 400
                else:
                    current_app.logger.info("No Google tokens available")
                    return jsonify({
                        'success': False,
                        'message': 'You need to connect your Google account to send emails. Please click the "Connect Google Account" button.'
                    }), 400

            # Log the communication
            current_app.logger.info(f"Logging communication in database")
            new_communication = Communication(
                type=comm_type,
                message=message,
                date_sent=date_sent,
                person_id=person_id,
                church_id=church_id,
                subject=subject,
                user_id=user_id
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
        churches_data = []
        for church in churches:
            if hasattr(church, 'get_name'):
                name = church.get_name()
            else:
                name = church.church_name
            churches_data.append({'id': church.id, 'name': name})
        return jsonify({
            'success': True,
            'churches': churches_data
        })

@communications_bp.route('/api/communications/search')
def search_communications():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
        
    search_term = request.args.get('q', '').lower()
    person_id = request.args.get('person_id')
    church_id = request.args.get('church_id')
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Limit results per page
    
    current_app.logger.debug(f"Searching communications with term: {search_term}, person_id: {person_id}, church_id: {church_id}, page: {page}")
    
    with session_scope() as session:
        # Start with a base query with eager loading
        query = session.query(Communication).options(
            db.joinedload(Communication.person),
            db.joinedload(Communication.church)
        )
        
        # Apply filters
        if person_id:
            try:
                person_id_int = int(person_id)
                query = query.filter(Communication.person_id == person_id_int)
            except ValueError:
                current_app.logger.error(f"Invalid person_id: {person_id}")
            
        if church_id:
            try:
                church_id_int = int(church_id)
                query = query.filter(Communication.church_id == church_id_int)
            except ValueError:
                current_app.logger.error(f"Invalid church_id: {church_id}")
        
        # Filter by user_id
        query = query.filter(Communication.user_id == user_id)
        
        # Apply search term if provided
        if search_term:
            # Join with Person and Church to search in their fields too
            query = query.outerjoin(Person, Communication.person_id == Person.id)
            query = query.outerjoin(Church, Communication.church_id == Church.id)
            
            # Search in multiple fields
            search_filter = (
                func.lower(Communication.message).contains(search_term) |
                func.lower(Communication.subject).contains(search_term) |
                func.lower(Person.first_name).contains(search_term) |
                func.lower(Person.last_name).contains(search_term) |
                func.lower(Person.email).contains(search_term) |
                func.lower(Church.church_name).contains(search_term) |
                func.lower(Church.email).contains(search_term)
            )
            query = query.filter(search_filter)
        
        # Order by date_sent
        query = query.order_by(func.coalesce(Communication.date_sent, datetime(1900, 1, 1)).desc())
        
        # Get total count for pagination info
        total_count = query.count()
        
        # Apply pagination
        query = query.limit(per_page).offset((page - 1) * per_page)
        
        # Execute the query
        results = query.all()
        
        # Filter out duplicates based on gmail_message_id
        unique_communications = {}
        for comm in results:
            if comm.gmail_message_id:
                if comm.gmail_message_id not in unique_communications:
                    unique_communications[comm.gmail_message_id] = comm
            else:
                # For communications without gmail_message_id, use the id as key
                unique_communications[f"id_{comm.id}"] = comm
        
        # Convert to a list
        filtered_communications = list(unique_communications.values())
        
        # Prepare the response data
        communications_data = []
        for comm in filtered_communications:
            recipient_name = "N/A"
            if comm.person:
                if hasattr(comm.person, 'get_name'):
                    recipient_name = comm.person.get_name()
                else:
                    recipient_name = f"{comm.person.first_name} {comm.person.last_name}"
            elif comm.church:
                if hasattr(comm.church, 'get_name'):
                    recipient_name = comm.church.get_name()
                else:
                    recipient_name = comm.church.church_name
                
            communications_data.append({
                'id': comm.id,
                'date_sent': comm.date_sent.strftime('%Y-%m-%d %H:%M') if comm.date_sent else 'N/A',
                'type': comm.type,
                'subject': comm.subject or 'N/A',
                'recipient': recipient_name,
                'message': (comm.message[:50] + '...') if comm.message and len(comm.message) > 50 else (comm.message or 'N/A'),
                'email_status': comm.email_status or 'N/A',
                'view_url': url_for('communications_bp.view_communication', comm_id=comm.id) if comm.type == 'Email' else None
            })
        
        # Add pagination info to the response
        response = {
            'communications': communications_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        }
        
        return jsonify(response)

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
    # Get the current user ID
    user_id = get_current_user_id()
    if not user_id:
        current_app.logger.warning("No user ID found in session, cannot reply to communication")
        return jsonify({
            'success': False,
            'message': 'User not authenticated'
        }), 401
        
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
        original = session.query(Communication).get(comm_id)
        if not original:
            return jsonify({
                'success': False,
                'message': 'Communication not found'
            }), 404
        
        # Determine recipient
        recipient_person_id = None
        recipient_church_id = None
        to_email = None
        recipient_name = None
        
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
        subject = f"Re: {original.subject}"
        
        # Try to send via Gmail API
        tokens = get_user_tokens()
        if tokens:
            access_token = tokens.get('token') or tokens.get('access_token')
            if access_token:
                try:
                    # Format the message - include original text for replies
                    formatted_message = message
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
                            gmail_thread_id=original.gmail_thread_id or response_data.get('thread_id'),
                            user_id=user_id
                        )
                        session.add(new_comm)
                        session.commit()
                        
                        return jsonify({
                            'success': True,
                            'message': f'Successfully sent reply to {recipient_name}',
                            'communication_id': new_comm.id
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'message': f'Failed to send email: {response.text}'
                        }), 500
                except Exception as e:
                    current_app.logger.error(f"Error sending reply: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
                    return jsonify({
                        'success': False,
                        'message': f'Error sending email: {str(e)}'
                    }), 500
        
        return jsonify({
            'success': False,
            'message': 'Google connection required to send emails'
        }), 400
