from models import Session, Church, Person, Contacts, Communication
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from datetime import datetime
from sqlalchemy import func, or_
from database import db, session_scope
from routes.dashboard import auth_required
from routes.google_auth import get_current_user_id
import logging

churches_bp = Blueprint('churches_bp', __name__)

@churches_bp.route('/churches')
@auth_required
def churches():
    user_id = get_current_user_id()
    current_app.logger.info(f"Getting churches for user_id: {user_id}")
    
    # Debug: Check if format parameter is present
    format_param = request.args.get('format')
    current_app.logger.info(f"Format parameter: {format_param}")
    
    with session_scope() as session:
        logging.info("Fetching churches from database...")
        try:
            # Get all churches without filtering by user_id since Church model doesn't have user_id field
            query = session.query(Church)
            
            # Print the SQL query for debugging
            current_app.logger.info(f"SQL Query: {query}")
            
            churches_list = query.all()
            current_app.logger.info(f"Found {len(churches_list)} churches")
            
            # Return JSON response for debugging
            if format_param == 'json':
                current_app.logger.info("Returning JSON response")
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
                response = jsonify({
                    'count': len(churches_list),
                    'churches': churches_data[:10]  # Return first 10 for brevity
                })
                current_app.logger.info(f"JSON response: {response}")
                return response
            
            return render_template('churches.html', churches=churches_list)
        except Exception as e:
            logging.error(f"Error fetching churches: {str(e)}", exc_info=True)
            raise

@churches_bp.route('/add_church_form')
@auth_required
def add_church_form():
    with session_scope() as session:
        people = session.query(Person).order_by(Person.first_name, Person.last_name).all()
        return render_template('add_church.html', people=people)

@churches_bp.route('/churches/<int:church_id>')
@auth_required
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

@churches_bp.route('/add_church', methods=['POST'])
def add_church():
    with session_scope() as session:
        # Basic Information
        church_name = request.form['church_name']
        location = request.form['location']
        street_address = request.form['street_address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        phone = request.form['phone']
        email = request.form['email']
        website = request.form['website']
        denomination = request.form['denomination']
        congregation_size = request.form['congregation_size'] or None
        year_founded = request.form['year_founded'] or None
        
        # Pastor Information
        senior_pastor_first_name = request.form['senior_pastor_first_name']
        senior_pastor_last_name = request.form['senior_pastor_last_name']
        senior_pastor_phone = request.form['senior_pastor_phone']
        senior_pastor_email = request.form['senior_pastor_email']
        missions_pastor_first_name = request.form['missions_pastor_first_name']
        missions_pastor_last_name = request.form['missions_pastor_last_name']
        mission_pastor_phone = request.form['mission_pastor_phone']
        mission_pastor_email = request.form['mission_pastor_email']
        
        # Contact Information
        primary_contact_first_name = request.form['primary_contact_first_name']
        primary_contact_last_name = request.form['primary_contact_last_name']
        primary_contact_phone = request.form['primary_contact_phone']
        primary_contact_email = request.form['primary_contact_email']
        main_contact_id = request.form['main_contact_id'] or None
        
        # Additional Information
        church_pipeline = request.form['church_pipeline']
        priority = request.form['priority']
        assigned_to = request.form['assigned_to']
        source = request.form['source']
        referred_by = request.form['referred_by']
        initial_notes = request.form['initial_notes']
        info_given = request.form['info_given']
        virtuous = 'virtuous' in request.form
        
        new_church = Church(
            type='church',  # Explicitly set the type
            church_name=church_name,
            location=location,
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code,
            phone=phone,
            email=email,
            website=website,
            denomination=denomination,
            congregation_size=congregation_size,
            year_founded=year_founded,
            senior_pastor_first_name=senior_pastor_first_name,
            senior_pastor_last_name=senior_pastor_last_name,
            senior_pastor_phone=senior_pastor_phone,
            senior_pastor_email=senior_pastor_email,
            missions_pastor_first_name=missions_pastor_first_name,
            missions_pastor_last_name=missions_pastor_last_name,
            mission_pastor_phone=mission_pastor_phone,
            mission_pastor_email=mission_pastor_email,
            primary_contact_first_name=primary_contact_first_name,
            primary_contact_last_name=primary_contact_last_name,
            primary_contact_phone=primary_contact_phone,
            primary_contact_email=primary_contact_email,
            main_contact_id=main_contact_id,
            church_pipeline=church_pipeline,
            priority=priority,
            assigned_to=assigned_to,
            source=source,
            referred_by=referred_by,
            initial_notes=initial_notes,
            info_given=info_given,
            virtuous=virtuous
        )
        
        logging.info(f"Creating new church: {new_church.get_name()} (type={new_church.type})")
        session.add(new_church)
        session.flush()  # Flush to get the ID
        logging.info(f"Created church with ID: {new_church.id}")
        
        return redirect(url_for('churches_bp.churches'))

@churches_bp.route('/edit_church/<int:church_id>', methods=['GET', 'POST'])
@auth_required
def edit_church(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        if not church:
            return "Church not found", 404
            
        if request.method == 'GET':
            # For GET requests, render the edit form with the church data
            people = session.query(Person).order_by(Person.first_name, Person.last_name).all()
            return render_template('add_church.html', church=church, people=people, edit_mode=True)
        else:
            # For POST requests, update the church data
            # Basic Information
            church.church_name = request.form['church_name']
            church.location = request.form['location']
            church.street_address = request.form['street_address']
            church.city = request.form['city']
            church.state = request.form['state']
            church.zip_code = request.form['zip_code']
            church.phone = request.form['phone']
            church.email = request.form['email']
            church.website = request.form['website']
            church.denomination = request.form['denomination']
            church.congregation_size = request.form['congregation_size'] if request.form['congregation_size'] else None
            church.year_founded = request.form['year_founded'] if request.form['year_founded'] else None

            # Senior Pastor Information
            church.senior_pastor_first_name = request.form['senior_pastor_first_name']
            church.senior_pastor_last_name = request.form['senior_pastor_last_name']
            church.senior_pastor_phone = request.form['senior_pastor_phone']
            church.senior_pastor_email = request.form['senior_pastor_email']

            # Missions Pastor Information
            church.missions_pastor_first_name = request.form['missions_pastor_first_name']
            church.missions_pastor_last_name = request.form['missions_pastor_last_name']
            church.mission_pastor_phone = request.form['mission_pastor_phone']
            church.mission_pastor_email = request.form['mission_pastor_email']

            # Primary Contact Information
            church.primary_contact_first_name = request.form['primary_contact_first_name']
            church.primary_contact_last_name = request.form['primary_contact_last_name']
            church.primary_contact_phone = request.form['primary_contact_phone']
            church.primary_contact_email = request.form['primary_contact_email']

            # Additional Information
            church.church_pipeline = request.form['church_pipeline']
            church.priority = request.form['priority']
            church.assigned_to = request.form['assigned_to']
            church.source = request.form['source']
            church.referred_by = request.form['referred_by']
            church.info_given = request.form['info_given']
            church.virtuous = 'virtuous' in request.form
            church.reason_closed = request.form['reason_closed']
            
            # Convert date_closed string to Python date object if present
            date_closed_str = request.form['date_closed']
            if date_closed_str:
                try:
                    church.date_closed = datetime.strptime(date_closed_str, '%Y-%m-%d').date()
                except ValueError:
                    church.date_closed = None
            else:
                church.date_closed = None

            return redirect(url_for('churches_bp.church_detail', church_id=church_id))

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
