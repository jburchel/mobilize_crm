from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from datetime import datetime
from models import Session, Person, Church, session_scope, Communication
from sqlalchemy import func
import logging
from database import db
from routes.dashboard import auth_required

people_bp = Blueprint('people_bp', __name__)

@people_bp.route('/people')
@auth_required
def people():
    with session_scope() as session:
        people_list = session.query(Person).filter(Person.type == 'person').all()
        return render_template('people.html', people=people_list)

@people_bp.route('/add_person_form')
@auth_required
def add_person_form():
    with session_scope() as session:
        churches = session.query(Church).order_by(Church.church_name).all()
        return render_template('add_person.html', churches=churches)

@people_bp.route('/people/<int:person_id>')
@auth_required
def person_detail(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        if person is None:
            abort(404)
        
        churches = session.query(Church).order_by(Church.church_name).all()
        
        # Get the 5 most recent communications for this person
        recent_communications = session.query(Communication)\
            .filter(Communication.person_id == person_id)\
            .order_by(Communication.date_sent.desc())\
            .limit(5)\
            .all()
        
        return render_template('person_detail.html', person=person, churches=churches, recent_communications=recent_communications)

@people_bp.route('/add_person', methods=['POST'])
def add_person():
    with session_scope() as session:
        title = request.form['title']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        preferred_contact_method = request.form['preferred_contact_method']
        street_address = request.form['street_address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        home_country = request.form['home_country']
        church_role = request.form['church_role']
        church_id = request.form['church_id'] or None
        marital_status = request.form['marital_status']
        spouse_first_name = request.form['spouse_first_name']
        spouse_last_name = request.form['spouse_last_name']
        people_pipeline = request.form['people_pipeline']
        priority = request.form['priority']
        assigned_to = request.form['assigned_to']
        source = request.form['source']
        referred_by = request.form['referred_by']
        initial_notes = request.form['initial_notes']
        info_given = request.form['info_given']
        desired_service = request.form['desired_service']
        virtuous = 'virtuous' in request.form
        
        new_person = Person(
            type='person',  # Explicitly set the type
            title=title,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            preferred_contact_method=preferred_contact_method,
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code,
            home_country=home_country,
            church_role=church_role,
            church_id=church_id,
            marital_status=marital_status,
            spouse_first_name=spouse_first_name,
            spouse_last_name=spouse_last_name,
            people_pipeline=people_pipeline,
            priority=priority,
            assigned_to=assigned_to,
            source=source,
            referred_by=referred_by,
            initial_notes=initial_notes,
            info_given=info_given,
            desired_service=desired_service,
            virtuous=virtuous
        )
        
        session.add(new_person)
        return redirect(url_for('people_bp.people'))

@people_bp.route('/edit_person/<int:person_id>', methods=['POST'])
def edit_person(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        if person:
            person.title = request.form['title']
            person.first_name = request.form['first_name']
            person.last_name = request.form['last_name']
            person.email = request.form['email']
            person.phone = request.form['phone']
            person.preferred_contact_method = request.form['preferred_contact_method']
            person.street_address = request.form['street_address']
            person.city = request.form['city']
            person.state = request.form['state']
            person.zip_code = request.form['zip_code']
            person.home_country = request.form['home_country']
            person.church_role = request.form['church_role']
            person.church_id = request.form['church_id'] or None
            person.marital_status = request.form['marital_status']
            person.spouse_first_name = request.form['spouse_first_name']
            person.spouse_last_name = request.form['spouse_last_name']
            person.people_pipeline = request.form['people_pipeline']
            person.priority = request.form['priority']
            person.assigned_to = request.form['assigned_to']
            person.source = request.form['source']
            person.referred_by = request.form['referred_by']
            person.info_given = request.form['info_given']
            person.desired_service = request.form['desired_service']
            person.virtuous = 'virtuous' in request.form
            person.reason_closed = request.form['reason_closed']
            
            # Convert date_closed string to Python date object if present
            date_closed_str = request.form['date_closed']
            if date_closed_str:
                try:
                    person.date_closed = datetime.strptime(date_closed_str, '%Y-%m-%d').date()
                except ValueError:
                    person.date_closed = None
            else:
                person.date_closed = None
                
            return redirect(url_for('people_bp.person_detail', person_id=person_id))
        return "Person not found", 404

@people_bp.route('/batch_update', methods=['POST'])
def batch_update():
    """Handle batch updates for multiple people"""
    with session_scope() as session:
        selected_ids = request.form.get('selected_ids', '')
        if not selected_ids:
            flash('No people selected for update', 'error')
            return redirect(url_for('people_bp.people'))
        
        # Parse the comma-separated list of IDs
        person_ids = [int(id) for id in selected_ids.split(',')]
        
        # Get the batch update values from the form
        batch_pipeline = request.form.get('batch_pipeline')
        batch_priority = request.form.get('batch_priority')
        batch_assigned_to = request.form.get('batch_assigned_to')
        batch_virtuous = request.form.get('batch_virtuous')
        
        # Count how many records were updated
        update_count = 0
        
        # Update each selected person
        for person_id in person_ids:
            person = session.query(Person).filter(Person.id == person_id).first()
            if person:
                # Only update fields that were selected for batch update
                if batch_pipeline:
                    person.people_pipeline = batch_pipeline
                
                if batch_priority:
                    person.priority = batch_priority
                
                if batch_assigned_to:
                    person.assigned_to = batch_assigned_to
                
                if batch_virtuous:
                    person.virtuous = (batch_virtuous.lower() == 'true')
                
                update_count += 1
        
        # Commit the changes
        session.commit()
        
        # Flash a success message
        flash(f'Successfully updated {update_count} people', 'success')
        
        return redirect(url_for('people_bp.people'))

@people_bp.route('/batch_delete', methods=['POST'])
def batch_delete():
    """Handle batch deletion for multiple people"""
    with session_scope() as session:
        selected_ids = request.form.get('selected_ids', '')
        if not selected_ids:
            flash('No people selected for deletion', 'error')
            return redirect(url_for('people_bp.people'))
        
        # Parse the comma-separated list of IDs
        person_ids = [int(id) for id in selected_ids.split(',')]
        
        # Count how many records were deleted
        delete_count = 0
        
        # Delete each selected person
        for person_id in person_ids:
            person = session.query(Person).filter(Person.id == person_id).first()
            if person:
                session.delete(person)
                delete_count += 1
        
        # Commit the changes
        session.commit()
        
        # Flash a success message
        flash(f'Successfully deleted {delete_count} people', 'success')
        
        return redirect(url_for('people_bp.people'))

@people_bp.route('/api/people/<int:person_id>', methods=['GET'])
def get_person_api(person_id):
    """API endpoint to get a person by ID"""
    try:
        with session_scope() as session:
            person = session.query(Person).filter(Person.id == person_id).first()
            if not person:
                return jsonify({'success': False, 'message': 'Person not found'})
            
            # Return person data
            person_data = {
                'id': person.id,
                'name': person.get_name(),
                'first_name': person.first_name,
                'last_name': person.last_name,
                'email': person.email,
                'phone': person.phone
            }
            
            return jsonify({'success': True, 'person': person_data})
    except Exception as e:
        logging.error(f'Error retrieving person {person_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@people_bp.route('/update_pipeline/<int:person_id>', methods=['POST'])
def update_pipeline(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first_or_404()
        
        # Get the pipeline value from the form
        pipeline_value = request.form.get('people_pipeline')
        
        if pipeline_value:
            person.people_pipeline = pipeline_value
            flash(f"Pipeline stage updated to {pipeline_value}", "success")
        
        return redirect(url_for('people_bp.person_detail', person_id=person_id))
