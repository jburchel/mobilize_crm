from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from sqlalchemy import func
from models import Session, Person, Church, Task, Communication, EmailSignature
from database import db, session_scope
from firebase_admin import auth
from functools import wraps
from routes.google_auth import get_current_user_id
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime

dashboard_bp = Blueprint('dashboard_bp', __name__)

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
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
                
        # No valid authentication found, redirect to home
        return redirect(url_for('home'))
            
    return decorated_function

@dashboard_bp.route('/')
@auth_required
def dashboard():
    user_id = get_current_user_id()
    with session_scope() as session:
        # Count only the user's people
        total_people = session.query(func.count(Person.id)).filter(
            Person.type == 'person',
            Person.user_id == user_id
        ).scalar()
        
        # Show all churches
        total_churches = session.query(func.count(Church.id)).filter(
            Church.type == 'church'
        ).scalar()
        
        # Get pending tasks and format them properly
        # Only show tasks related to the user's people or any church
        pending_tasks = (
            session.query(
                Task.id,
                Task.title,
                Task.description,
                Task.due_date,
                Task.status,
                Person.first_name,
                Person.last_name,
                Church.church_name.label('church_name')
            )
            .outerjoin(Person, Task.person_id == Person.id)
            .outerjoin(Church, Task.church_id == Church.id)
            .filter(
                Task.status != 'Completed',
                # Only include tasks for this user's people or for any church
                ((Person.user_id == user_id) | (Task.church_id != None))
            )
            .all()
        )
        
        # Format the tasks with full names
        formatted_tasks = []
        for task in pending_tasks:
            person_name = None
            if task.first_name and task.last_name:
                person_name = f"{task.first_name} {task.last_name}"
            
            formatted_tasks.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date,
                'status': task.status,
                'person_name': person_name,
                'church_name': task.church_name
            })
        
        # Get recent communications
        # Only show communications related to the user's people or to any church
        recent_comms_query = (
            session.query(
                Communication,
                Person.first_name,
                Person.last_name,
                Church.church_name
            )
            .outerjoin(Person, Communication.person_id == Person.id)
            .outerjoin(Church, Communication.church_id == Church.id)
            .filter(
                # Only include communications for this user's people or for any church
                ((Person.user_id == user_id) | (Communication.church_id != None))
            )
            .order_by(Communication.date_sent.desc())
            .limit(5)
            .all()
        )
        
        # Format the communications with full names
        recent_communications = []
        for comm, first_name, last_name, church_name in recent_comms_query:
            person_name = None
            if first_name and last_name:
                person_name = f"{first_name} {last_name}"
            
            recent_communications.append((comm, person_name, church_name))
        
        return render_template('dashboard.html', 
                             people=total_people, 
                             churches=total_churches, 
                             tasks=formatted_tasks, 
                             communications=recent_communications)

@dashboard_bp.route('/google-settings')
@auth_required
def google_settings():
    """Google integration settings page"""
    return render_template('google_settings.html')

@dashboard_bp.route('/email-signatures')
# @auth_required  # Temporarily commented out for testing
def email_signatures():
    # Temporarily bypass authentication check for testing
    # user_id = get_current_user_id()
    # if not user_id:
    #     return redirect(url_for('home'))
    
    user_id = "test_user_123"  # Consistent test user ID
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
# @auth_required  # Temporarily commented out for testing
def create_signature():
    # Temporarily bypass authentication check for testing
    # user_id = get_current_user_id()
    # if not user_id:
    #     return redirect(url_for('home'))
    
    user_id = "test_user_123"  # Consistent test user ID
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
            return render_template('create_signature.html', error=str(e))
    
    return render_template('create_signature.html')

@dashboard_bp.route('/email-signatures/edit/<int:signature_id>', methods=['GET', 'POST'])
# @auth_required  # Temporarily commented out for testing
def edit_signature(signature_id):
    # Temporarily bypass authentication check for testing
    # user_id = get_current_user_id()
    # if not user_id:
    #     return redirect(url_for('home'))
    
    user_id = "test_user_123"  # Consistent test user ID
    current_app.logger.info(f"Editing signature {signature_id} for user: {user_id}")
    
    try:
        with session_scope() as session:
            signature = session.query(EmailSignature).filter_by(id=signature_id, user_id=user_id).first()
            if not signature:
                current_app.logger.warning(f"Signature {signature_id} not found for user {user_id}")
                return redirect(url_for('dashboard_bp.email_signatures'))
            
            if request.method == 'POST':
                try:
                    name = request.form.get('name')
                    content = request.form.get('content')
                    is_default = request.form.get('is_default') == 'on'
                    
                    current_app.logger.info(f"Updating signature: name={name}, is_default={is_default}, content length={len(content) if content else 0}")
                    
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
                    return render_template('edit_signature.html', signature=signature, error=str(e))
            
            return render_template('edit_signature.html', signature=signature)
    except Exception as e:
        current_app.logger.error(f"Error editing signature: {str(e)}")
        return render_template('edit_signature.html', signature=None, error=str(e))

@dashboard_bp.route('/email-signatures/delete/<int:signature_id>', methods=['POST'])
# @auth_required  # Temporarily commented out for testing
def delete_signature(signature_id):
    # Temporarily bypass authentication check for testing
    # user_id = get_current_user_id()
    # if not user_id:
    #     return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    user_id = "test_user_123"  # Consistent test user ID
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
# @auth_required  # Temporarily commented out for testing
def get_email_signatures_api():
    """API endpoint to get the user's email signatures"""
    try:
        # Temporarily bypass authentication check for testing
        # user_id = get_current_user_id()
        # if not user_id:
        #     return jsonify({
        #         'success': False,
        #         'message': 'User not authenticated'
        #     }), 401
            
        user_id = "test_user_123"  # Consistent test user ID
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
