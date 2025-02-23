from flask import Blueprint, render_template, request, redirect, url_for
from models import Session, Church, Person, session_scope

churches_bp = Blueprint('churches_bp', __name__)

@churches_bp.route('/churches')
def churches():
    with session_scope() as session:
        churches_list = session.query(Church).all()
        people_list = session.query(Person).all()  # Fetch people for dropdown
        return render_template('churches.html', churches=churches_list, people=people_list)

@churches_bp.route('/churches/<int:church_id>')
def church_detail(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        return render_template('church_detail.html', church=church)

@churches_bp.route('/add_church', methods=['POST'])
def add_church():
    with session_scope() as session:
        name = request.form['name']
        location = request.form['location']
        phone = request.form['phone']
        email = request.form['email']
        main_contact_id = request.form['main_contact_id'] or None
        
        new_church = Church(
            name=name, 
            location=location, 
            phone=phone, 
            email=email, 
            main_contact_id=main_contact_id
        )
        session.add(new_church)
        return redirect(url_for('churches_bp.churches'))

@churches_bp.route('/edit_church/<int:church_id>', methods=['POST'])
def edit_church(church_id):
    with session_scope() as session:
        church = session.query(Church).filter(Church.id == church_id).first()
        if church:
            church.name = request.form['name']
            church.location = request.form['location']
            church.phone = request.form['phone']
            church.email = request.form['email']
            church.main_contact_id = request.form['main_contact_id'] or None
            return redirect(url_for('churches_bp.church_detail', church_id=church_id))
        return "Church not found", 404
