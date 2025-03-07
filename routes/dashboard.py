from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, session, flash
from sqlalchemy import func
from models import Session, Person, Church, Task, Communication, EmailSignature, UserOffice, Office
from database import db, session_scope
from firebase_admin import auth
from functools import wraps
from routes.google_auth import get_current_user_id
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
from bs4 import BeautifulSoup
import base64
import requests
import traceback

from utils.auth import auth_required, get_current_user_id
from utils.gmail_integration import convert_image_urls_to_data_urls

dashboard_bp = Blueprint('dashboard_bp', __name__)

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split('Bearer ')[1]
                decoded_token = auth.verify_id_token(token)
                # Set the user_id in the session
                session['user_id'] = decoded_token['uid']
                return f(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Bearer token verification failed: {str(e)}")

        # If no valid bearer token, check for session token
        if 'firebase_token' in request.cookies:
            try:
                decoded_token = auth.verify_id_token(request.cookies['firebase_token'])
                # Set the user_id in the session
                session['user_id'] = decoded_token['uid']
                return f(*args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Cookie token verification failed: {str(e)}")
                
        # No valid authentication found, redirect to home
        return redirect(url_for('home'))
            
    return decorated_function

@dashboard_bp.route('/')
@auth_required
def dashboard():
    user_id = get_current_user_id()
    
    # If user_id is None, try to get it from the firebase_token cookie
    if user_id is None:
        try:
            if 'firebase_token' in request.cookies:
                token = request.cookies['firebase_token']
                decoded_token = auth.verify_id_token(token)
                user_id = decoded_token['uid']
                current_app.logger.info(f"Retrieved user_id from firebase_token cookie: {user_id}")
        except Exception as e:
            current_app.logger.error(f"Error getting user_id from firebase_token cookie: {str(e)}")
    
    # If still None, redirect to login
    if user_id is None:
        current_app.logger.warning("No user_id found, redirecting to login")
        return redirect(url_for('home'))
    
    with session_scope() as session:
        # Count only the user's people
        total_people = session.query(func.count(Person.id)).filter(
            Person.type == 'person',
            Person.user_id == user_id
        ).scalar()
        
        # Log the query and result for debugging
        current_app.logger.info(f"Dashboard people count query for user_id={user_id}: {total_people}")
        
        # Show all churches
        total_churches = session.query(func.count(Church.id)).filter(
            Church.type == 'church'
        ).scalar()
        
        # Get pending tasks and format them properly
        # Only show tasks for this user
        pending_tasks = (
            session.query(
                Task.id,
                Task.title,
                Task.description,
                Task.due_date,
                Task.due_time,
                Task.status,
                Task.priority,
                Person.first_name,
                Person.last_name,
                Church.church_name,
                Task.person_id,
                Task.church_id
            )
            .outerjoin(Person, Task.person_id == Person.id)
            .outerjoin(Church, Task.church_id == Church.id)
            .filter(Task.user_id == user_id)
            .filter(Task.status != 'Completed')
            .order_by(Task.due_date)
            .limit(5)
            .all()
        )
        
        # Get recent communications
        recent_communications = (
            session.query(Communication)
            .filter(Communication.user_id == user_id)
            .order_by(Communication.date_sent.desc())
            .limit(5)
            .all()
        )
        
        # Get user's offices and roles
        user_offices = (
            session.query(UserOffice)
            .filter(UserOffice.user_id == user_id)
            .join(Office, UserOffice.office_id == Office.id)
            .all()
        )
        
        return render_template(
            'dashboard.html',
            total_people=total_people,
            total_churches=total_churches,
            pending_tasks=pending_tasks,
            recent_communications=recent_communications,
            user_offices=user_offices
        )

@dashboard_bp.route('/google-settings')
@auth_required
def google_settings():
    """Google integration settings page"""
    return render_template('google_settings.html')

@dashboard_bp.route('/email-signatures')
@auth_required
def email_signatures():
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('home'))
    
    current_app.logger.info(f"Accessing email signatures for user: {user_id}")
    
    try:
        with session_scope() as session:
            signatures = session.query(EmailSignature).filter_by(user_id=user_id).all()
            current_app.logger.info(f"Found {len(signatures)} signatures for user {user_id}")
            return render_template('email_signatures.html', signatures=signatures)
    except Exception as e:
        current_app.logger.error(f"Error retrieving email signatures: {str(e)}")
        return render_template('email_signatures.html', signatures=[], error=str(e))

@dashboard_bp.route('/email-signatures/create', methods=['GET', 'POST'])
@auth_required
def create_signature():
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('home'))
    
    current_app.logger.info(f"Creating signature for user: {user_id}")
    
    if request.method == 'POST':
        current_app.logger.info(f"Received POST request to create signature")
        current_app.logger.info(f"Form data: {request.form}")
        current_app.logger.info(f"Files: {request.files}")
        
        try:
            name = request.form.get('name')
            content = request.form.get('content')
            is_default = request.form.get('is_default') == 'on'
            
            current_app.logger.info(f"Received signature data: name={name}, is_default={is_default}, content length={len(content) if content else 0}")
            
            # Ensure all images in the content are data URLs
            if content:
                content = convert_image_urls_to_data_urls(content)
            
            # Handle logo upload
            logo_url = None
            if 'logo' in request.files and request.files['logo'].filename:
                logo_file = request.files['logo']
                filename = secure_filename(f"{uuid.uuid4()}_{logo_file.filename}")
                upload_folder = os.path.join(current_app.static_folder, 'uploads/signatures')
                
                # Create upload folder if it doesn't exist
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Save the file
                file_path = os.path.join(upload_folder, filename)
                logo_file.save(file_path)
                
                # Set the URL for the logo
                logo_url = url_for('static', filename=f'uploads/signatures/{filename}')
            
            with session_scope() as session:
                # If this is the default signature, unset any existing default
                if is_default:
                    existing_defaults = session.query(EmailSignature).filter_by(
                        user_id=user_id, is_default=True
                    ).all()
                    for sig in existing_defaults:
                        sig.is_default = False
                
                # Create new signature
                new_signature = EmailSignature(
                    user_id=user_id,
                    name=name,
                    content=content,
                    logo_url=logo_url,
                    is_default=is_default,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(new_signature)
                session.commit()
                
                return redirect(url_for('dashboard_bp.email_signatures'))
        except Exception as e:
            current_app.logger.error(f"Error creating signature: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return render_template('create_signature.html', error=str(e))
    
    return render_template('create_signature.html')

@dashboard_bp.route('/email-signatures/edit/<int:signature_id>', methods=['GET', 'POST'])
@auth_required
def edit_signature(signature_id):
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('home'))
    
    current_app.logger.info(f"Editing signature {signature_id} for user: {user_id}")
    
    try:
        with session_scope() as session:
            signature = session.query(EmailSignature).filter_by(id=signature_id).first()
            
            if not signature:
                current_app.logger.warning(f"Signature {signature_id} not found")
                return redirect(url_for('dashboard_bp.email_signatures'))
            
            if signature.user_id != user_id and signature.user_id != 'default':
                current_app.logger.warning(f"User {user_id} attempted to edit signature {signature_id} belonging to user {signature.user_id}")
                return redirect(url_for('dashboard_bp.email_signatures'))
            
            if request.method == 'POST':
                current_app.logger.info(f"Received POST request to update signature {signature_id}")
                
                try:
                    name = request.form.get('name')
                    content = request.form.get('content')
                    is_default = request.form.get('is_default') == 'on'
                    
                    current_app.logger.info(f"Received signature data: name={name}, is_default={is_default}, content length={len(content) if content else 0}")
                    
                    # Ensure all images in the content are data URLs
                    if content:
                        content = convert_image_urls_to_data_urls(content)
                    
                    # Handle logo upload
                    if 'logo' in request.files and request.files['logo'].filename:
                        logo_file = request.files['logo']
                        filename = secure_filename(f"{uuid.uuid4()}_{logo_file.filename}")
                        upload_folder = os.path.join(current_app.static_folder, 'uploads/signatures')
                        
                        # Create upload folder if it doesn't exist
                        if not os.path.exists(upload_folder):
                            os.makedirs(upload_folder)
                        
                        # Save the file
                        file_path = os.path.join(upload_folder, filename)
                        logo_file.save(file_path)
                        
                        # Set the URL for the logo
                        signature.logo_url = url_for('static', filename=f'uploads/signatures/{filename}')
                    
                    # If this is the default signature, unset any existing default
                    if is_default and not signature.is_default:
                        existing_defaults = session.query(EmailSignature).filter_by(
                            user_id=user_id, is_default=True
                        ).all()
                        for sig in existing_defaults:
                            sig.is_default = False
                    
                    # Update signature
                    signature.name = name
                    signature.content = content
                    signature.is_default = is_default
                    signature.updated_at = datetime.now()
                    session.commit()
                    
                    return redirect(url_for('dashboard_bp.email_signatures'))
                except Exception as e:
                    current_app.logger.error(f"Error updating signature: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
                    return render_template('edit_signature.html', signature=signature, error=str(e))
            
            return render_template('edit_signature.html', signature=signature)
    except Exception as e:
        current_app.logger.error(f"Error accessing signature: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return redirect(url_for('dashboard_bp.email_signatures'))

@dashboard_bp.route('/email-signatures/delete/<int:signature_id>', methods=['POST'])
@auth_required
def delete_signature(signature_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    current_app.logger.info(f"Deleting signature {signature_id} for user: {user_id}")
    
    try:
        with session_scope() as session:
            signature = session.query(EmailSignature).filter_by(id=signature_id, user_id=user_id).first()
            if not signature:
                current_app.logger.warning(f"Signature {signature_id} not found for user {user_id}")
                return jsonify({'success': False, 'message': 'Signature not found'}), 404
            
            # Delete the logo file if it exists
            if signature.logo_url:
                try:
                    logo_path = os.path.join(current_app.static_folder, signature.logo_url.replace('/static/', ''))
                    if os.path.exists(logo_path):
                        os.remove(logo_path)
                        current_app.logger.info(f"Deleted logo file: {logo_path}")
                except Exception as e:
                    current_app.logger.error(f"Error deleting logo file: {str(e)}")
            
            # Delete the signature
            session.delete(signature)
            session.commit()
            current_app.logger.info(f"Signature {signature_id} deleted successfully")
            
            return jsonify({'success': True, 'message': 'Signature deleted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error deleting signature: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting signature: {str(e)}'}), 500

@dashboard_bp.route('/api/signatures')
@auth_required
def get_signatures():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
    with session_scope() as session:
        signatures = session.query(EmailSignature).filter_by(user_id=user_id).all()
        result = []
        for sig in signatures:
            result.append({
                'id': sig.id,
                'name': sig.name,
                'content': sig.content,
                'logo_url': sig.logo_url,
                'is_default': sig.is_default,
                'created_at': sig.created_at.isoformat() if sig.created_at else None,
                'updated_at': sig.updated_at.isoformat() if sig.updated_at else None
            })
        
        return jsonify({'success': True, 'signatures': result})

@dashboard_bp.route('/api/email-signatures', methods=['GET'])
@auth_required
def get_email_signatures_api():
    """API endpoint to get the user's email signatures"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not authenticated'
            }), 401
            
        current_app.logger.info(f"API request for email signatures for user: {user_id}")
        
        with session_scope() as db_session:
            signatures = db_session.query(EmailSignature).filter_by(user_id=user_id).all()
            current_app.logger.info(f"Found {len(signatures)} signatures for user {user_id}")
            
            signatures_data = [{
                'id': signature.id,
                'name': signature.name,
                'content': signature.content,
                'is_default': signature.is_default,
                'created_at': signature.created_at.isoformat() if signature.created_at else None,
                'updated_at': signature.updated_at.isoformat() if signature.updated_at else None
            } for signature in signatures]
            
            return jsonify({
                'success': True,
                'signatures': signatures_data
            })
    except Exception as e:
        current_app.logger.error(f"Error getting email signatures: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting email signatures: {str(e)}'
        }), 500

@dashboard_bp.route('/api/pipeline-stats', methods=['GET'])
@auth_required
def pipeline_stats():
    """API endpoint to get pipeline statistics for both People and Churches"""
    try:
        with session_scope() as session:
            # Get people pipeline statistics
            people_pipeline_stats = (
                session.query(
                    Person.people_pipeline,
                    func.count(Person.id).label('count')
                )
                .filter(Person.people_pipeline.isnot(None))
                .group_by(Person.people_pipeline)
                .all()
            )
            
            # Get church pipeline statistics
            church_pipeline_stats = (
                session.query(
                    Church.church_pipeline,
                    func.count(Church.id).label('count')
                )
                .filter(Church.church_pipeline.isnot(None))
                .group_by(Church.church_pipeline)
                .all()
            )
            
            # Convert to dictionaries
            people_stats = {
                'PROMOTION': 0,
                'INFORMATION': 0,
                'INVITATION': 0,
                'CONFIRMATION': 0,
                'AUTOMATION': 0
            }
            
            church_stats = {
                'PROMOTION': 0,
                'INFORMATION': 0,
                'INVITATION': 0,
                'CONFIRMATION': 0,
                'AUTOMATION': 0
            }
            
            # Fill in the actual counts
            for stage, count in people_pipeline_stats:
                if stage in people_stats:
                    people_stats[stage] = count
                    
            for stage, count in church_pipeline_stats:
                if stage in church_stats:
                    church_stats[stage] = count
            
            # Format the data for the chart
            result = {
                'people': {
                    'labels': list(people_stats.keys()),
                    'counts': list(people_stats.values())
                },
                'churches': {
                    'labels': list(church_stats.keys()),
                    'counts': list(church_stats.values())
                }
            }
            
            return jsonify(result)
    
    except Exception as e:
        current_app.logger.error(f"Error retrieving pipeline stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/settings')
@auth_required
def settings():
    """Settings page that combines Email Signatures, Google Settings, and Import CSV"""
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('home'))
    
    current_app.logger.info(f"Accessing settings page for user: {user_id}")
    
    try:
        with session_scope() as session:
            # Get email signatures for the user
            signatures = session.query(EmailSignature).filter_by(user_id=user_id).all()
            current_app.logger.info(f"Found {len(signatures)} signatures for user {user_id}")
            
            return render_template('settings.html', signatures=signatures)
    except Exception as e:
        current_app.logger.error(f"Error retrieving settings data: {str(e)}")
        return render_template('settings.html', signatures=[], error=str(e))
