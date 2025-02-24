from flask import Blueprint, render_template, request, redirect, url_for, current_app
from models import Session, Church, Person, Contacts, session_scope
from sqlalchemy import func
from datetime import datetime
import logging

churches_bp = Blueprint('churches_bp', __name__)

@churches_bp.route('/churches')
def churches():
    with session_scope() as session:
        logging.info("Fetching churches from database...")
        try:
            # Get all contacts of type 'church' with debug info
            churches_query = session.query(Church).filter(Church.type == 'church')
            logging.info(f"SQL Query: {str(churches_query)}")
            
            churches_list = churches_query.all()
            
            logging.info(f"Found {len(churches_list)} churches")
            for church in churches_list:
                logging.info(f"Church details: ID={church.id}, Type={church.type}, "
                           f"Name={church.get_name()}, Church Name={church.church_name}, "
                           f"Location={church.location}, Email={church.email}")
            
            return render_template('churches.html', churches=churches_list)
        except Exception as e:
            logging.error(f"Error fetching churches: {str(e)}", exc_info=True)
            raise

@churches_bp.route('/add_church_form')
def add_church_form():
    with session_scope() as session:
        people = session.query(Person).order_by(Person.first_name, Person.last_name).all()
        return render_template('add_church.html', people=people)

@churches_bp.route('/churches/<int:church_id>')
def church_detail(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        return render_template('church_detail.html', church=church)

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

@churches_bp.route('/edit_church/<int:church_id>', methods=['POST'])
def edit_church(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        if church:
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
        return "Church not found", 404
