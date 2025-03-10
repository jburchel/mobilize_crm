"""
Routes for office management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, flash
from models import Office, UserOffice, Church, session_scope, office_schema, user_office_schema, ROLE_CHOICES
from utils.auth import auth_required, get_current_user_id
from sqlalchemy.exc import SQLAlchemyError
import datetime
from sqlalchemy import func
import firebase_admin
from firebase_admin import auth

offices_admin_bp = Blueprint('offices_admin_bp', __name__)

# Helper function to check if user is a super admin
def is_super_admin(user_id):
    """Check if the user is a super admin."""
    with session_scope() as session:
        user_office = session.query(UserOffice).filter_by(
            user_id=user_id, 
            role='super_admin'
        ).first()
        return user_office is not None

# Helper function to check if user is an office admin
def is_office_admin(user_id, office_id):
    """Check if the user is an admin for the specified office."""
    with session_scope() as session:
        user_office = session.query(UserOffice).filter_by(
            user_id=user_id, 
            office_id=office_id,
            role='office_admin'
        ).first()
        return user_office is not None

# Helper function to get user's offices
def get_user_offices(user_id):
    """Get all offices the user has access to."""
    with session_scope() as session:
        user_offices = session.query(UserOffice).filter_by(
            user_id=user_id
        ).all()
        office_ids = [uo.office_id for uo in user_offices]
        offices = session.query(Office).filter(Office.id.in_(office_ids)).all()
        return offices

def get_user_email(user_id):
    """Get user email from Firebase UID."""
    try:
        user = auth.get_user(user_id)
        return user.email
    except Exception as e:
        current_app.logger.error(f"Error getting user email: {str(e)}")
        return user_id  # Return the UID if we can't get the email

def get_user_id_from_email(email):
    """Get Firebase UID from email."""
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except Exception as e:
        current_app.logger.error(f"Error getting user ID from email: {str(e)}")
        return None

def create_firebase_user(email, password=None):
    """Create a new Firebase user with the given email."""
    try:
        # Generate a random password if none provided
        if not password:
            import random
            import string
            password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create the user in Firebase
        user = auth.create_user(
            email=email,
            email_verified=False,
            password=password,
            disabled=False
        )
        
        # Send password reset email to allow user to set their own password
        auth.generate_password_reset_link(email)
        
        current_app.logger.info(f"Created new Firebase user with email: {email}")
        return user.uid, password
    except Exception as e:
        current_app.logger.error(f"Error creating Firebase user: {str(e)}")
        return None, None

@offices_admin_bp.route('/admin/offices')
@auth_required
def list_offices():
    """List all offices the user has access to."""
    user_id = get_current_user_id()
    
    # Check if user is a super admin
    super_admin = is_super_admin(user_id)
    
    with session_scope() as session:
        if super_admin:
            # Super admins can see all offices
            offices = session.query(Office).all()
        else:
            # Other users can only see offices they have access to
            user_offices = session.query(UserOffice).filter_by(user_id=user_id).all()
            office_ids = [uo.office_id for uo in user_offices]
            offices = session.query(Office).filter(Office.id.in_(office_ids)).all()
        
        # Get user count for each office
        office_stats = []
        for office in offices:
            user_count = session.query(func.count(UserOffice.id)).filter(UserOffice.office_id == office.id).scalar()
            church_count = session.query(func.count(Church.id)).filter(Church.office_id == office.id).scalar()
            office_stats.append({
                'office': office,
                'user_count': user_count,
                'church_count': church_count
            })
        
        return render_template('admin/offices.html', 
                               offices=offices, 
                               office_stats=office_stats,
                               super_admin=super_admin)

@offices_admin_bp.route('/admin/offices/new', methods=['GET', 'POST'])
@auth_required
def new_office():
    """Create a new office."""
    user_id = get_current_user_id()
    
    # Only super admins can create new offices
    if not is_super_admin(user_id):
        return redirect(url_for('offices_admin_bp.list_offices'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        with session_scope() as session:
            new_office = Office(
                name=name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                phone=phone,
                email=email,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )
            session.add(new_office)
            session.commit()
            
            return redirect(url_for('offices_admin_bp.list_offices'))
    
    return render_template('admin/offices/new.html')

@offices_admin_bp.route('/admin/offices/<int:office_id>/edit', methods=['GET', 'POST'])
@auth_required
def edit_office(office_id):
    """Edit an existing office."""
    user_id = get_current_user_id()
    
    # Check if user is a super admin or office admin
    super_admin = is_super_admin(user_id)
    office_admin = is_office_admin(user_id, office_id)
    
    if not (super_admin or office_admin):
        return redirect(url_for('offices_admin_bp.list_offices'))
    
    with session_scope() as session:
        office = session.query(Office).get(office_id)
        
        if not office:
            return redirect(url_for('offices_admin_bp.list_offices'))
        
        if request.method == 'POST':
            office.name = request.form.get('name')
            office.address = request.form.get('address')
            office.city = request.form.get('city')
            office.state = request.form.get('state')
            office.zip_code = request.form.get('zip_code')
            office.phone = request.form.get('phone')
            office.email = request.form.get('email')
            office.updated_at = datetime.datetime.now()
            
            session.commit()
            return redirect(url_for('offices_admin_bp.list_offices'))
        
        return render_template('admin/offices/edit.html', office=office)

@offices_admin_bp.route('/admin/offices/<int:office_id>/delete', methods=['POST'])
@auth_required
def delete_office(office_id):
    """Delete an office."""
    user_id = get_current_user_id()
    
    # Only super admins can delete offices
    if not is_super_admin(user_id):
        return redirect(url_for('offices_admin_bp.list_offices'))
    
    with session_scope() as session:
        # Check if there are churches associated with this office
        churches = session.query(Church).filter_by(office_id=office_id).count()
        
        if churches > 0:
            # Cannot delete an office with churches
            return render_template(
                'admin/offices/list.html',
                error=f"Cannot delete office with {churches} churches. Reassign churches first."
            )
        
        # Delete user-office associations
        session.query(UserOffice).filter_by(office_id=office_id).delete()
        
        # Delete the office
        office = session.query(Office).get(office_id)
        if office:
            session.delete(office)
            session.commit()
    
    return redirect(url_for('offices_admin_bp.list_offices'))

@offices_admin_bp.route('/admin/offices/<int:office_id>/users')
@auth_required
def list_office_users(office_id):
    """List all users for a specific office."""
    user_id = get_current_user_id()
    
    # Check if user is a super admin or office admin
    super_admin = is_super_admin(user_id)
    office_admin = is_office_admin(user_id, office_id)
    
    if not super_admin and not office_admin:
        flash('You do not have permission to view office users.', 'danger')
        return redirect(url_for('offices_admin_bp.list_offices'))
    
    with session_scope() as session:
        office = session.query(Office).get(office_id)
        if not office:
            flash('Office not found.', 'danger')
            return redirect(url_for('offices_admin_bp.list_offices'))
        
        user_offices = session.query(UserOffice).filter_by(office_id=office_id).all()
        
        # Get email addresses for each user
        user_data = []
        for user_office in user_offices:
            email = get_user_email(user_office.user_id)
            user_data.append({
                'user_office': user_office,
                'email': email
            })
        
        return render_template(
            'admin/office_users.html',
            office=office,
            user_offices=user_offices,
            user_data=user_data,
            super_admin=super_admin
        )

@offices_admin_bp.route('/admin/offices/<int:office_id>/users/add', methods=['GET', 'POST'])
@auth_required
def add_office_user(office_id):
    """Add a user to an office."""
    user_id = get_current_user_id()
    
    # Check if user is a super admin or office admin
    super_admin = is_super_admin(user_id)
    office_admin = is_office_admin(user_id, office_id)
    
    if not super_admin and not office_admin:
        flash('You do not have permission to add office users.', 'danger')
        return redirect(url_for('offices_admin_bp.list_offices'))
    
    with session_scope() as session:
        office = session.query(Office).get(office_id)
        if not office:
            flash('Office not found.', 'danger')
            return redirect(url_for('offices_admin_bp.list_offices'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            role = request.form.get('role')
            create_if_not_exists = request.form.get('create_if_not_exists') == 'on'
            
            # Get Firebase UID from email
            new_user_id = get_user_id_from_email(email)
            
            # If user doesn't exist and create_if_not_exists is checked, create the user
            if not new_user_id and create_if_not_exists:
                new_user_id, temp_password = create_firebase_user(email)
                if new_user_id:
                    flash(f'Created new user with email {email}. A password reset email has been sent.', 'success')
                else:
                    flash(f'Failed to create user with email {email}.', 'danger')
                    roles = ROLE_CHOICES
                    return render_template(
                        'admin/add_office_user.html',
                        office=office,
                        roles=roles,
                        super_admin=super_admin
                    )
            elif not new_user_id:
                flash(f'User with email {email} not found in Firebase.', 'danger')
                roles = ROLE_CHOICES
                return render_template(
                    'admin/add_office_user.html',
                    office=office,
                    roles=roles,
                    super_admin=super_admin
                )
            
            # Check if user already has access to this office
            existing = session.query(UserOffice).filter_by(
                user_id=new_user_id, 
                office_id=office_id
            ).first()
            
            if existing:
                flash(f'User already has access to this office with role: {existing.role}', 'warning')
                return redirect(url_for('offices_admin_bp.list_office_users', office_id=office_id))
            
            # Create new user-office association
            user_office = UserOffice(
                user_id=new_user_id,
                office_id=office_id,
                role=role
            )
            session.add(user_office)
            session.commit()
            
            flash(f'User {email} added to office successfully.', 'success')
            return redirect(url_for('offices_admin_bp.list_office_users', office_id=office_id))
        
        # GET request - show form
        roles = ROLE_CHOICES
        return render_template(
            'admin/add_office_user.html',
            office=office,
            roles=roles,
            super_admin=super_admin
        )

@offices_admin_bp.route('/admin/offices/<int:office_id>/users/<user_id>/remove', methods=['POST'])
@auth_required
def remove_office_user(office_id, user_id):
    """Remove a user from an office."""
    current_user_id = get_current_user_id()
    
    # Check if user is a super admin or office admin
    super_admin = is_super_admin(current_user_id)
    office_admin = is_office_admin(current_user_id, office_id)
    
    if not (super_admin or office_admin):
        return redirect(url_for('offices_admin_bp.list_offices'))
    
    with session_scope() as session:
        # Delete the user-office association
        session.query(UserOffice).filter_by(
            user_id=user_id,
            office_id=office_id
        ).delete()
        
        session.commit()
    
    return redirect(url_for('offices_admin_bp.list_office_users', office_id=office_id))

# API endpoints for office management
@offices_admin_bp.route('/api/offices')
@auth_required
def api_list_offices():
    """API endpoint to list offices."""
    user_id = get_current_user_id()
    
    # Check if user is a super admin
    super_admin = is_super_admin(user_id)
    
    with session_scope() as session:
        if super_admin:
            # Super admins can see all offices
            offices = session.query(Office).all()
        else:
            # Other users can only see offices they have access to
            offices = get_user_offices(user_id)
        
        return jsonify({
            'offices': office_schema.dump(offices, many=True)
        })

@offices_admin_bp.route('/api/offices/<int:office_id>')
@auth_required
def api_get_office(office_id):
    """API endpoint to get an office."""
    user_id = get_current_user_id()
    
    # Check if user has access to this office
    with session_scope() as session:
        if is_super_admin(user_id) or is_office_admin(user_id, office_id):
            office = session.query(Office).get(office_id)
            
            if not office:
                return jsonify({'error': 'Office not found'}), 404
            
            return jsonify({
                'office': office_schema.dump(office)
            })
        
        return jsonify({'error': 'Unauthorized'}), 403

@offices_admin_bp.route('/api/offices', methods=['POST'])
@auth_required
def api_create_office():
    """API endpoint to create an office."""
    user_id = get_current_user_id()
    
    # Only super admins can create offices
    if not is_super_admin(user_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    
    try:
        with session_scope() as session:
            new_office = Office(
                name=data.get('name'),
                address=data.get('address'),
                city=data.get('city'),
                state=data.get('state'),
                zip_code=data.get('zip_code'),
                phone=data.get('phone'),
                email=data.get('email'),
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )
            session.add(new_office)
            session.flush()
            
            return jsonify({
                'office': office_schema.dump(new_office),
                'message': 'Office created successfully'
            }), 201
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error creating office: {str(e)}")
        return jsonify({'error': 'Failed to create office'}), 500

@offices_admin_bp.route('/api/offices/<int:office_id>', methods=['PUT'])
@auth_required
def api_update_office(office_id):
    """API endpoint to update an office."""
    user_id = get_current_user_id()
    
    # Check if user is a super admin or office admin
    if not (is_super_admin(user_id) or is_office_admin(user_id, office_id)):
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    
    try:
        with session_scope() as session:
            office = session.query(Office).get(office_id)
            
            if not office:
                return jsonify({'error': 'Office not found'}), 404
            
            office.name = data.get('name', office.name)
            office.address = data.get('address', office.address)
            office.city = data.get('city', office.city)
            office.state = data.get('state', office.state)
            office.zip_code = data.get('zip_code', office.zip_code)
            office.phone = data.get('phone', office.phone)
            office.email = data.get('email', office.email)
            office.updated_at = datetime.datetime.now()
            
            return jsonify({
                'office': office_schema.dump(office),
                'message': 'Office updated successfully'
            })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error updating office: {str(e)}")
        return jsonify({'error': 'Failed to update office'}), 500

@offices_admin_bp.route('/api/offices/<int:office_id>', methods=['DELETE'])
@auth_required
def api_delete_office(office_id):
    """API endpoint to delete an office."""
    user_id = get_current_user_id()
    
    # Only super admins can delete offices
    if not is_super_admin(user_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        with session_scope() as session:
            # Check if there are churches associated with this office
            churches = session.query(Church).filter_by(office_id=office_id).count()
            
            if churches > 0:
                return jsonify({
                    'error': f'Cannot delete office with {churches} churches. Reassign churches first.'
                }), 400
            
            # Delete user-office associations
            session.query(UserOffice).filter_by(office_id=office_id).delete()
            
            # Delete the office
            office = session.query(Office).get(office_id)
            if not office:
                return jsonify({'error': 'Office not found'}), 404
            
            session.delete(office)
            
            return jsonify({
                'message': 'Office deleted successfully'
            })
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error deleting office: {str(e)}")
        return jsonify({'error': 'Failed to delete office'}), 500 