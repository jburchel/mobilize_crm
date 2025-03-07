from models import Session, Church, Person, Contacts, Communication, Office
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from datetime import datetime
from sqlalchemy import func, or_
from database import db, session_scope
from routes.dashboard import auth_required
from routes.google_auth import get_current_user_id
from routes.offices_admin import is_super_admin, get_user_offices
from utils.auth import get_current_user_id as utils_get_current_user_id
from utils.permissions import has_permission
import logging

churches_bp = Blueprint('churches_bp', __name__)

@churches_bp.route('/')
@auth_required
@has_permission('view_churches')
def list_churches():
    """List all churches."""
    user_id = get_current_user_id()
    office_id = request.args.get('office_id', type=int)
    
    # Get user's offices
    super_admin = is_super_admin(user_id)
    user_offices = get_user_offices(user_id)
    user_office_ids = [office.id for office in user_offices]
    
    with session_scope() as session:
        query = session.query(Church).filter(Church.type == 'church')
        
        # Filter by office if specified and user has access to that office
        if office_id:
            if super_admin or office_id in user_office_ids:
                query = query.filter(Church.office_id == office_id)
            else:
                # If user doesn't have access to the specified office, show no churches
                query = query.filter(Church.id == -1)  # This will return no results
        elif not super_admin:
            # If not super admin and no specific office requested, show churches from user's offices
            if user_office_ids:
                query = query.filter(Church.office_id.in_(user_office_ids))
            else:
                # If user has no offices, show no churches
                query = query.filter(Church.id == -1)  # This will return no results
        
        # Apply any additional filters
        search_term = request.args.get('search', '')
        if search_term:
            query = query.filter(Church.church_name.ilike(f'%{search_term}%'))
        
        # Get all churches
        churches = query.all()
        
        # Get all offices for the filter dropdown
        offices = []
        if super_admin:
            # Get all offices
            offices = session.query(Office).all()
        else:
            # Get only user's offices
            offices = user_offices
        
        return render_template(
            'churches/list.html',
            churches=churches,
            search_term=search_term,
            offices=offices,
            selected_office_id=office_id,
            super_admin=super_admin
        )

@churches_bp.route('/add_church_form')
@auth_required
def add_church_form():
    return render_template('add_church.html')

@churches_bp.route('/<int:church_id>')
@auth_required
@has_permission('view_churches')
def church_detail(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        if church is None:
            abort(404)
        
        # Get the 5 most recent communications for this church
        recent_communications = session.query(Communication)\
            .filter(Communication.church_id == church_id)\
            .order_by(Communication.date_sent.desc())\
            .limit(5)\
            .all()
        
        return render_template('church_detail.html', church=church, recent_communications=recent_communications)

@churches_bp.route('/new', methods=['GET', 'POST'])
@auth_required
@has_permission('add_church')
def new_church():
    """Create a new church."""
    user_id = get_current_user_id()
    
    # Check if user has access to create churches
    super_admin = is_super_admin(user_id)
    user_offices = get_user_offices(user_id)
    user_office_ids = [office.id for office in user_offices]
    
    if request.method == 'POST':
        # Get form data
        church_name = request.form.get('church_name')
        location = request.form.get('location')
        website = request.form.get('website')
        denomination = request.form.get('denomination')
        congregation_size = request.form.get('congregation_size', type=int)
        year_founded = request.form.get('year_founded', type=int)
        
        # Get office ID
        office_id = request.form.get('office_id', type=int)
        
        # Check if user has access to the selected office
        if office_id and not (super_admin or office_id in user_office_ids):
            flash("You don't have permission to create a church in this office.", "danger")
            return redirect(url_for('churches_bp.list_churches'))
        
        # Get contact information
        phone = request.form.get('phone')
        email = request.form.get('email')
        street_address = request.form.get('street_address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        
        # Create new church
        with session_scope() as session:
            new_church = Church(
                church_name=church_name,
                location=location,
                website=website,
                denomination=denomination,
                congregation_size=congregation_size,
                year_founded=year_founded,
                office_id=office_id,
                phone=phone,
                email=email,
                street_address=street_address,
                city=city,
                state=state,
                zip_code=zip_code,
                date_created=datetime.date.today(),
                date_modified=datetime.date.today(),
                type='church'
            )
            
            session.add(new_church)
            session.commit()
            
            return redirect(url_for('churches_bp.view_church', church_id=new_church.id))
    
    # Get all offices for the dropdown
    with session_scope() as session:
        offices = []
        if super_admin:
            # Super admin can see all offices
            offices = session.query(Office).all()
        else:
            # Other users can only see their offices
            offices = user_offices
        
        return render_template('churches/new.html', offices=offices)

@churches_bp.route('/edit/<int:church_id>', methods=['GET', 'POST'])
@auth_required
@has_permission('edit_church')
def edit_church(church_id):
    """Edit a church."""
    user_id = get_current_user_id()
    
    # Check if user has access to this church
    super_admin = is_super_admin(user_id)
    user_offices = get_user_offices(user_id)
    user_office_ids = [office.id for office in user_offices]
    
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        
        if not church:
            return redirect(url_for('churches_bp.list_churches'))
        
        # Check if user has access to this church's office
        if not super_admin and church.office_id not in user_office_ids:
            flash("You don't have permission to edit this church.", "danger")
            return redirect(url_for('churches_bp.list_churches'))
        
        if request.method == 'POST':
            # Update church details
            church.church_name = request.form.get('church_name')
            church.location = request.form.get('location')
            church.website = request.form.get('website')
            church.denomination = request.form.get('denomination')
            church.congregation_size = request.form.get('congregation_size', type=int)
            church.year_founded = request.form.get('year_founded', type=int)
            
            # Update office if user is super admin or has access to both offices
            new_office_id = request.form.get('office_id', type=int)
            if new_office_id:
                if super_admin or new_office_id in user_office_ids:
                    church.office_id = new_office_id
            
            # Update contact information
            church.phone = request.form.get('phone')
            church.email = request.form.get('email')
            church.street_address = request.form.get('street_address')
            church.city = request.form.get('city')
            church.state = request.form.get('state')
            church.zip_code = request.form.get('zip_code')
            
            # Update other fields as needed
            # ...
            
            # Update date modified
            church.date_modified = datetime.date.today()
            
            session.commit()
            
            return redirect(url_for('churches_bp.view_church', church_id=church.id))
        
        # Get all offices for the dropdown
        offices = []
        if super_admin:
            # Super admin can see all offices
            offices = session.query(Office).all()
        else:
            # Other users can only see their offices
            offices = user_offices
        
        return render_template('churches/edit.html', church=church, offices=offices)

@churches_bp.route('/batch_update', methods=['POST'])
def batch_update():
    """Handle batch updates for multiple churches"""
    with session_scope() as session:
        selected_ids = request.form.get('selected_ids', '')
        if not selected_ids:
            flash('No churches selected for update', 'error')
            return redirect(url_for('churches_bp.churches'))
        
        # Parse the comma-separated list of IDs
        church_ids = [int(id) for id in selected_ids.split(',')]
        
        # Get the batch update values from the form
        batch_pipeline = request.form.get('batch_pipeline')
        batch_priority = request.form.get('batch_priority')
        batch_assigned_to = request.form.get('batch_assigned_to')
        batch_virtuous = request.form.get('batch_virtuous')
        
        # Count how many records were updated
        update_count = 0
        
        # Update each selected church
        for church_id in church_ids:
            church = session.query(Church).filter(Church.id == church_id).first()
            if church:
                # Only update fields that were selected for batch update
                if batch_pipeline:
                    church.church_pipeline = batch_pipeline
                
                if batch_priority:
                    church.priority = batch_priority
                
                if batch_assigned_to:
                    church.assigned_to = batch_assigned_to
                
                if batch_virtuous:
                    church.virtuous = (batch_virtuous.lower() == 'true')
                
                update_count += 1
        
        # Commit the changes
        session.commit()
        
        # Flash a success message
        flash(f'Successfully updated {update_count} churches', 'success')
        
        return redirect(url_for('churches_bp.churches'))

@churches_bp.route('/batch_delete', methods=['POST'])
def batch_delete():
    """Handle batch deletion for multiple churches"""
    with session_scope() as session:
        selected_ids = request.form.get('selected_ids', '')
        if not selected_ids:
            flash('No churches selected for deletion', 'error')
            return redirect(url_for('churches_bp.churches'))
        
        # Parse the comma-separated list of IDs
        church_ids = [int(id) for id in selected_ids.split(',')]
        
        # Count how many records were deleted
        delete_count = 0
        
        # Delete each selected church
        for church_id in church_ids:
            church = session.query(Church).filter(Church.id == church_id).first()
            if church:
                session.delete(church)
                delete_count += 1
        
        # Commit the changes
        session.commit()
        
        # Flash a success message
        flash(f'Successfully deleted {delete_count} churches', 'success')
        
        return redirect(url_for('churches_bp.churches'))

@churches_bp.route('/api/churches/<int:church_id>', methods=['GET'])
def get_church_api(church_id):
    """API endpoint to get a church by ID"""
    try:
        with session_scope() as session:
            church = session.query(Church).filter(Church.id == church_id).first()
            if not church:
                return jsonify({'success': False, 'message': 'Church not found'})
            
            # Return church data
            church_data = {
                'id': church.id,
                'name': church.get_name(),
                'church_name': church.church_name,
                'location': church.location,
                'email': church.email,
                'phone': church.phone
            }
            
            return jsonify({'success': True, 'church': church_data})
    except Exception as e:
        logging.error(f'Error retrieving church {church_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@churches_bp.route('/update_church_pipeline/<int:church_id>', methods=['POST'])
def update_church_pipeline(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first_or_404()
        
        # Get the pipeline value from the form
        pipeline_value = request.form.get('church_pipeline')
        
        if pipeline_value:
            church.church_pipeline = pipeline_value
            flash(f"Pipeline stage updated to {pipeline_value}", "success")
        
        return redirect(url_for('churches_bp.church_detail', church_id=church_id))

@churches_bp.route('/api/churches')
@auth_required
def churches_api():
    """API endpoint for churches that returns JSON data"""
    user_id = get_current_user_id()
    current_app.logger.info(f"API: Getting churches for user_id: {user_id}")
    
    with session_scope() as session:
        logging.info("API: Fetching churches from database...")
        try:
            # Get all churches without filtering by user_id since Church model doesn't have user_id field
            query = session.query(Church)
            
            # Print the SQL query for debugging
            current_app.logger.info(f"API: SQL Query: {query}")
            
            churches_list = query.all()
            current_app.logger.info(f"API: Found {len(churches_list)} churches")
            
            # Prepare JSON response
            churches_data = []
            for church in churches_list:
                churches_data.append({
                    'id': church.id,
                    'church_name': church.church_name,
                    'email': church.email,
                    'phone': church.phone,
                    'city': church.city,
                    'state': church.state,
                    'location': church.location,
                    'pipeline': church.church_pipeline,
                    'priority': church.priority
                })
            
            # Return JSON response
            return jsonify({
                'count': len(churches_list),
                'churches': churches_data[:10]  # Return first 10 for brevity
            })
        except Exception as e:
            logging.error(f"API: Error fetching churches: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

@churches_bp.route('/<int:church_id>')
@auth_required
@has_permission('view_churches')
def view_church(church_id):
    """View a church."""
    user_id = get_current_user_id()
    
    # Check if user has access to this church
    super_admin = is_super_admin(user_id)
    user_offices = get_user_offices(user_id)
    user_office_ids = [office.id for office in user_offices]
    
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        
        if not church:
            return redirect(url_for('churches_bp.list_churches'))
        
        # Check if user has access to this church's office
        if not super_admin and church.office_id not in user_office_ids:
            flash("You don't have permission to view this church.", "danger")
            return redirect(url_for('churches_bp.list_churches'))
        
        # Get tasks for this church
        tasks = session.query(Task).filter(Task.church_id == church_id).all()
        
        # Get communications for this church
        communications = session.query(Communication).filter(Communication.church_id == church_id).all()
        
        return render_template(
            'churches/view.html',
            church=church,
            tasks=tasks,
            communications=communications
        )
