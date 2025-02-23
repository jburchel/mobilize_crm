from flask import Blueprint, render_template, request, redirect, url_for
from models import Session, Person, session_scope

people_bp = Blueprint('people_bp', __name__)

@people_bp.route('/people')
def people():
    with session_scope() as session:
        people = session.query(Person).all()
        return render_template('people.html', people=people)

@people_bp.route('/people/<int:person_id>')
def person_detail(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        return render_template('person_detail.html', person=person)

@people_bp.route('/edit_person/<int:person_id>', methods=['POST'])
def edit_person(person_id):
    with session_scope() as session:
        person = session.query(Person).filter(Person.id == person_id).first()
        if person:
            person.name = request.form['name']
            person.email = request.form['email']
            person.phone = request.form['phone']
            person.address = request.form['address']
            person.church_id = request.form['church_id'] or None
            person.role = request.form['role']
            return redirect(url_for('people_bp.person_detail', person_id=person_id))
        return "Person not found", 404

@people_bp.route('/add_person', methods=['POST'])
def add_person():
    with session_scope() as session:
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        new_person = Person(name=name, phone=phone, email=email)
        session.add(new_person)
        return redirect(url_for('people_bp.people'))
