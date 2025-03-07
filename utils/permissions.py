"""
Permission checking middleware for role-based access control.
"""
from functools import wraps
from flask import redirect, url_for, flash, current_app, request
from models import UserOffice, session_scope
from utils.auth import get_current_user_id

def has_permission(permission_name):
    """
    Decorator to check if a user has a specific permission.
    
    Args:
        permission_name: The name of the permission to check.
        
    Returns:
        A decorator function.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_current_user_id()
            
            if not user_id:
                return redirect(url_for('home'))
            
            # Check if user has the required permission
            if not check_permission(user_id, permission_name):
                flash(f"You don't have permission to access this resource.", "danger")
                return redirect(url_for('dashboard_bp.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_permission(user_id, permission_name):
    """
    Check if a user has a specific permission.
    
    Args:
        user_id: The user ID to check.
        permission_name: The name of the permission to check.
        
    Returns:
        bool: True if the user has the permission, False otherwise.
    """
    # Super admins have all permissions
    if is_super_admin(user_id):
        return True
    
    # TODO: Implement more granular permission checking based on the permission_name
    # This would involve checking the user's role in each office and the specific permission
    
    # For now, we'll implement some basic permission checks
    if permission_name == 'view_churches':
        # All users can view churches they have access to
        return True
    elif permission_name == 'add_church':
        # Office admins and standard users can add churches
        return has_role(user_id, ['office_admin', 'standard_user'])
    elif permission_name == 'edit_church':
        # Office admins and standard users can edit churches
        return has_role(user_id, ['office_admin', 'standard_user'])
    elif permission_name == 'delete_church':
        # Only office admins can delete churches
        return has_role(user_id, ['office_admin'])
    elif permission_name == 'manage_offices':
        # Only super admins can manage offices
        return is_super_admin(user_id)
    elif permission_name == 'manage_users':
        # Only super admins and office admins can manage users
        return has_role(user_id, ['super_admin', 'office_admin'])
    
    # Default to denying permission
    return False

def is_super_admin(user_id):
    """
    Check if a user is a super admin.
    
    Args:
        user_id: The user ID to check.
        
    Returns:
        bool: True if the user is a super admin, False otherwise.
    """
    with session_scope() as session:
        user_office = session.query(UserOffice).filter_by(
            user_id=user_id, 
            role='super_admin'
        ).first()
        return user_office is not None

def is_office_admin(user_id, office_id):
    """
    Check if a user is an admin for a specific office.
    
    Args:
        user_id: The user ID to check.
        office_id: The office ID to check.
        
    Returns:
        bool: True if the user is an admin for the office, False otherwise.
    """
    with session_scope() as session:
        user_office = session.query(UserOffice).filter_by(
            user_id=user_id, 
            office_id=office_id,
            role='office_admin'
        ).first()
        return user_office is not None

def has_role(user_id, roles):
    """
    Check if a user has any of the specified roles in any office.
    
    Args:
        user_id: The user ID to check.
        roles: A list of roles to check.
        
    Returns:
        bool: True if the user has any of the roles, False otherwise.
    """
    with session_scope() as session:
        user_office = session.query(UserOffice).filter(
            UserOffice.user_id == user_id,
            UserOffice.role.in_(roles)
        ).first()
        return user_office is not None

def get_user_role(user_id, office_id):
    """
    Get a user's role in a specific office.
    
    Args:
        user_id: The user ID to check.
        office_id: The office ID to check.
        
    Returns:
        str: The user's role in the office, or None if the user has no role.
    """
    with session_scope() as session:
        user_office = session.query(UserOffice).filter_by(
            user_id=user_id, 
            office_id=office_id
        ).first()
        return user_office.role if user_office else None 