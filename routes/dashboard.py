from flask import Blueprint, render_template
from sqlalchemy import func
from models import Session, Person, Church, Task, Communication, session_scope

dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/')
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
                Person.name.label('person_name'),
                Church.name.label('church_name')
            )
            .outerjoin(Person, Task.person_id == Person.id)
            .outerjoin(Church, Task.church_id == Church.id)
            .filter(Task.status != 'Completed')
            .all()
        )
        
        recent_communications = (
            session.query(Communication, Person.name.label('person_name'), Church.name.label('church_name'))
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
