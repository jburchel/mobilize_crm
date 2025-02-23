from flask import Blueprint, render_template, request, redirect, url_for, current_app
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from models import Session, Communication, Person, Church, session_scope
import os

communications_bp = Blueprint('communications_bp', __name__)

@communications_bp.route('/communications')
def communications_route():
    with session_scope() as session:
        communications_list = session.query(Communication).all()
        people_list = session.query(Person).all()
        churches_list = session.query(Church).all()
        return render_template('communications.html', 
                             communications=communications_list, 
                             people=people_list, 
                             churches=churches_list)

@communications_bp.route('/send_communication', methods=['POST'])
def send_communication_route():
    with session_scope() as session:
        comm_type = request.form['type']
        message = request.form['message']
        person_id = request.form['person_id'] or None
        church_id = request.form['church_id'] or None
        date_sent = datetime.now().date()

        # Send Email if type is Email
        if comm_type == 'Email':
            # Email sending logic remains here as it's specific to communications
            to_email = None
            if person_id:
                person = session.query(Person).filter_by(id=person_id).first()
                to_email = person.email if person else None
            elif church_id:
                church = session.query(Church).filter_by(id=church_id).first()
                to_email = church.email if church else None

            sender_email = os.environ.get('SMTP_EMAIL')
            sender_password = os.environ.get('SMTP_PASSWORD')
            
            if not sender_email or not sender_password:
                current_app.logger.warning("Email credentials not configured")
                return redirect(url_for('communications_bp.communications_route'))

            msg = MIMEText(message)
            msg['Subject'] = 'Mobilize CRM Communication'
            msg['From'] = sender_email
            msg['To'] = to_email
            
            try:
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
            except Exception as e:
                current_app.logger.error(f"Email error: {str(e)}")
                # Still log the communication even if email fails

        # Log the communication
        new_communication = Communication(
            type=comm_type,
            message=message,
            date_sent=date_sent,
            person_id=person_id,
            church_id=church_id
        )
        session.add(new_communication)
        return redirect(url_for('communications_bp.communications_route'))
