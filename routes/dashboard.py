from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import func
from models import Session, Person, Church, Task, Communication, session_scope
from firebase_admin import auth
from functools import wraps

dashboard_bp = Blueprint('dashboard_bp', __name__)

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return redirect(url_for('home'))
            
        try:
            token = auth_header.split('Bearer ')[1]
            auth.verify_id_token(token)
        except:
            return redirect(url_for('home'))
            
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/')
@auth_required
def dashboard():
    with session_scope() as session:
        total_people = session.query(func.count(Person.id)).scalar()
        total_churches = session.query(func.count(Church.id)).scalar()
        
        # Get pending tasks and format them properly
        pending_tasks = (
            session.query(
                Task.id,
                Task.title,
                Task.description,
                Task.due_date,
                Task.status,
                func.coalesce(func.concat(Person.first_name, ' ', Person.last_name), None).label('person_name'),
                Church.church_name.label('church_name')
            )
            .outerjoin(Person, Task.person_id == Person.id)
            .outerjoin(Church, Task.church_id == Church.id)
            .filter(Task.status != 'Completed')
            .all()
        )
        
        recent_communications = (
            session.query(
                Communication,
                func.coalesce(func.concat(Person.first_name, ' ', Person.last_name), None).label('person_name'),
                Church.church_name.label('church_name')
            )
            .outerjoin(Person, Communication.person_id == Person.id)
            .outerjoin(Church, Communication.church_id == Church.id)
            .order_by(Communication.date_sent.desc())
            .limit(5)
            .all()
        )
        
        return render_template('dashboard.html', 
                             people=total_people, 
                             churches=total_churches, 
                             tasks=pending_tasks, 
                             communications=recent_communications)
