from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from datetime import datetime
from models import Session, Person, Church, Communication, UserOffice, Office, Contacts
from sqlalchemy import func, or_, text
import logging
from database import db, session_scope
from routes.dashboard import auth_required
from routes.google_auth import get_current_user_id
from utils.permissions import is_super_admin

people_bp = Blueprint('people_bp', __name__)

@people_bp.route('/')
@auth_required
def list_people():
    user_id = get_current_user_id()
    current_app.logger.info(f"Getting people for user_id: {user_id}")
    
    # Debug authentication state
    from flask import session, request
    current_app.logger.info(f"Session data: {session}")
    current_app.logger.info(f"Request cookies: {request.cookies}")
    current_app.logger.info(f"Request headers: {request.headers}")
    
    with session_scope() as session:
        try:
            # Use ORM query instead of raw SQL
            people_query = session.query(Person).filter(Person.type == 'person')
            
            # Apply user filter if not super admin
            if not is_super_admin(user_id):
                people_query = people_query.filter(Person.user_id == user_id)
            
            # Get the people
            people_objects = people_query.limit(100).all()
            
            current_app.logger.info(f"Found {len(people_objects)} people total using ORM query")
            
            return render_template('people/list.html', people=people_objects)
        except Exception as e:
            current_app.logger.error(f"Error in list_people: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            return redirect(url_for('dashboard_bp.dashboard'))

@people_bp.route('/add_person_form')
@auth_required
def add_person_form():
    with session_scope() as session:
        churches = session.query(Church).all()
        return render_template('people/new.html', churches=churches)

@people_bp.route('/<int:person_id>')
@auth_required
def person_detail(person_id):
    """Display details for a specific person"""
    user_id = get_current_user_id()
    if not user_id:
        current_app.logger.warning("No user ID found in session, redirecting to login")
        return redirect(url_for('dashboard_bp.dashboard'))
        
    with session_scope() as session:
        # Get the person
        person = session.query(Person).filter_by(id=person_id).first()
        
        if not person:
            flash('Person not found', 'danger')
            return redirect(url_for('people_bp.people_list'))
            
        # Get churches for this person
        churches = []
        try:
            from models import Church
            churches = session.query(Church).all()
        except Exception as e:
            current_app.logger.error(f"Error getting churches: {str(e)}")
            
        # Use distinct to avoid duplicates
        query = session.query(Communication)\
            .filter(
                Communication.person_id == person_id,
                # Filter by user_id if it's set in the communication
                # But don't exclude communications without a user_id
                ((Communication.user_id == user_id) | (Communication.user_id == None))
            )\
            .order_by(Communication.date_sent.desc())
            
        current_app.logger.debug(f"SQL Query for communications: {query}")
        
        # Execute the query and get distinct communications by gmail_message_id
        all_communications = query.all()
        
        # Log the types of communications found
        comm_types = {}
        for comm in all_communications:
            if comm and comm.type:
                if comm.type in comm_types:
                    comm_types[comm.type] += 1
                else:
                    comm_types[comm.type] = 1
        
        current_app.logger.info(f"Communication types found for person {person_id}: {comm_types}")
        current_app.logger.info(f"Total communications found for person {person_id}: {len(all_communications)}")
        
        # Use a set to track seen message IDs
        seen_message_ids = set()
        recent_communications = []
        
        for comm in all_communications:
            # Skip if comm is None or we've already seen this message ID
            if comm is None:
                continue
                
            # Skip if we've already seen this message ID
            if comm.gmail_message_id and comm.gmail_message_id in seen_message_ids:
                continue
                
            # Add to recent communications
            recent_communications.append(comm)
            
            # Add message ID to seen set if it exists
            if comm.gmail_message_id:
                seen_message_ids.add(comm.gmail_message_id)
                
            # Limit to 5 recent communications
            if len(recent_communications) >= 5:
                break
                
        current_app.logger.debug(f"Found {len(recent_communications)} recent communications")
        
        # Get tasks for this person
        tasks = []
        try:
            from models import Task
            tasks = session.query(Task).filter(Task.person_id == person_id).all()
            current_app.logger.debug(f"Found {len(tasks)} tasks for person {person_id}")
        except Exception as e:
            current_app.logger.error(f"Error getting tasks: {str(e)}")
            
        # Get activity timeline
        activities = []
        
        # Add communications to activities
        for comm in all_communications[:10]:  # Limit to 10 most recent
            # Skip None communications
            if comm is None:
                continue
                
            activities.append({
                'type': 'communication',
                'title': f"{comm.type} Communication",
                'description': comm.subject or comm.message[:50] + ('...' if len(comm.message) > 50 else ''),
                'date': comm.date_sent
            })
            
        # Add tasks to activities
        for task in tasks:
            activities.append({
                'type': 'task',
                'title': task.title,
                'description': task.description[:50] + ('...' if len(task.description) > 50 else ''),
                'date': task.due_date or task.date_created
            })
            
        # Sort activities by date, newest first
        activities.sort(key=lambda x: x['date'], reverse=True)
        
        # Limit to 10 most recent activities
        activities = activities[:10]
        
        return render_template('people/view.html', 
                              person=person, 
                              churches=churches,
                              recent_communications=recent_communications,
                              tasks=tasks,
                              activities=activities)

@people_bp.route('/add_person', methods=['POST'])
@auth_required
def add_person():
    user_id = get_current_user_id()
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
            virtuous=virtuous,
            user_id=user_id  # Associate with current user
        )
        
        session.add(new_person)
        return redirect(url_for('people_bp.list_people'))

@people_bp.route('/edit_person/<int:person_id>', methods=['GET', 'POST'])
@auth_required
def edit_person(person_id):
    user_id = get_current_user_id()
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        if not person:
            return "Person not found", 404
            
        # Ensure we're only editing a person that belongs to this user
        if person.user_id != user_id:
            current_app.logger.warning(f"User {user_id} attempted to edit person {person_id} belonging to user {person.user_id}")
            return "Unauthorized", 403
        
        if request.method == 'GET':
            # For GET requests, render the edit form with the person data
            churches = session.query(Church).order_by(Church.church_name).all()
            return render_template('people/edit.html', person=person, churches=churches)
        else:
            # For POST requests, update the person data
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
            
            # Convert date_closed string to Python date object if present
            date_closed_str = request.form.get('date_closed', '')
            if date_closed_str:
                try:
                    person.date_closed = datetime.strptime(date_closed_str, '%Y-%m-%d').date()
                except ValueError:
                    person.date_closed = None
            else:
                person.date_closed = None
                
            person.reason_closed = request.form.get('reason_closed', '')

            return redirect(url_for('people_bp.person_detail', person_id=person_id))

@people_bp.route('/batch_update', methods=['POST'])
def batch_update():
    """Handle batch updates for multiple people"""
    with session_scope() as session:
        selected_ids = request.form.get('selected_ids', '')
        if not selected_ids:
            flash('No people selected for update', 'error')
            return redirect(url_for('people_bp.list_people'))
        
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
        
        return redirect(url_for('people_bp.list_people'))

@people_bp.route('/batch_delete', methods=['POST'])
def batch_delete():
    """Handle batch deletion for multiple people"""
    with session_scope() as session:
        selected_ids = request.form.get('selected_ids', '')
        if not selected_ids:
            flash('No people selected for deletion', 'error')
            return redirect(url_for('people_bp.list_people'))
        
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
        
        return redirect(url_for('people_bp.list_people'))

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

@people_bp.route('/api/people')
@auth_required
def people_api():
    """API endpoint for people that returns JSON data"""
    user_id = get_current_user_id()
    current_app.logger.info(f"API: Getting people for user_id: {user_id}")
    
    with session_scope() as session:
        logging.info("API: Fetching people from database...")
        try:
            # Filter people by user_id
            query = session.query(Person).filter(
                Person.type == 'person',
                Person.user_id == user_id
            )
            
            # Print the SQL query for debugging
            current_app.logger.info(f"API: SQL Query: {query}")
            
            people_list = query.all()
            current_app.logger.info(f"API: Found {len(people_list)} people")
            
            # Prepare JSON response
            people_data = []
            for person in people_list:
                people_data.append({
                    'id': person.id,
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'email': person.email,
                    'phone': person.phone,
                    'city': person.city,
                    'state': person.state,
                    'country': person.home_country,
                    'pipeline': person.people_pipeline,
                    'priority': person.priority,
                    'user_id': person.user_id
                })
            
            # Return JSON response
            return jsonify({
                'count': len(people_list),
                'people': people_data[:10]  # Return first 10 for brevity
            })
        except Exception as e:
            logging.error(f"API: Error fetching people: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
