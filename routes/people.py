from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
from models import Session, Person, Church, session_scope

people_bp = Blueprint('people_bp', __name__)

@people_bp.route('/people')
def people():
    with session_scope() as session:
        people = session.query(Person).order_by(Person.first_name, Person.last_name).all()
        return render_template('people.html', people=people)

@people_bp.route('/add_person_form')
def add_person_form():
    with session_scope() as session:
        churches = session.query(Church).all()
        return render_template('add_person.html', churches=churches)

@people_bp.route('/people/<int:person_id>')
def person_detail(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        churches = session.query(Church).all()
        return render_template('person_detail.html', person=person, churches=churches)

@people_bp.route('/edit_person/<int:person_id>', methods=['POST'])
def edit_person(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        if person:
            # Update base contact fields
            person.first_name = request.form['first_name']
            person.last_name = request.form['last_name']
            person.preferred_contact_method = request.form['preferred_contact_method']
            person.phone = request.form['phone']
            person.email = request.form['email']
            person.street_address = request.form['street_address']
            person.city = request.form['city']
            person.state = request.form['state']
            person.zip_code = request.form['zip_code']
            person.initial_notes = request.form['initial_notes']
            
            # Update person-specific fields
            person.role = request.form['role']
            person.church_id = request.form['church_id'] or None
            person.spouse_first_name = request.form['spouse_first_name']
            person.spouse_last_name = request.form['spouse_last_name']
            person.virtuous = 'virtuous' in request.form
            person.title = request.form['title']
            person.home_country = request.form['home_country']
            person.marital_status = request.form['marital_status']
            person.people_pipeline = request.form['people_pipeline']
            person.priority = request.form['priority']
            person.assigned_to = request.form['assigned_to']
            person.source = request.form['source']
            person.referred_by = request.form['referred_by']
            person.info_given = request.form['info_given']
            person.desired_service = request.form['desired_service']
            person.reason_closed = request.form['reason_closed']
            person.date_closed = datetime.strptime(request.form['date_closed'], '%Y-%m-%d').date() if request.form['date_closed'] else None
            
            return redirect(url_for('people_bp.person_detail', person_id=person_id))
        return "Person not found", 404

@people_bp.route('/add_person', methods=['POST'])
def add_person():
    with session_scope() as session:
        new_person = Person(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            preferred_contact_method=request.form.get('preferred_contact_method'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            street_address=request.form.get('street_address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            zip_code=request.form.get('zip_code'),
            initial_notes=request.form.get('initial_notes'),
            role=request.form.get('role', 'Contact'),
            church_id=request.form.get('church_id') or None,
            spouse_first_name=request.form.get('spouse_first_name'),
            spouse_last_name=request.form.get('spouse_last_name')
        )
        session.add(new_person)
        return redirect(url_for('people_bp.people'))
