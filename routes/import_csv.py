from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from werkzeug.utils import secure_filename
import os
from models import Person, Church, Contacts
from database import db, session_scope
import csv
import io
from datetime import datetime
from routes.dashboard import auth_required
from routes.google_auth import get_current_user_id

# Create blueprint
import_csv_bp = Blueprint('import_csv_bp', __name__)

@import_csv_bp.route('/import-csv', methods=['GET', 'POST'])
@auth_required
def import_csv():
    user_id = get_current_user_id()
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'csv_file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        contact_type = request.form.get('contact_type')
        if not contact_type or contact_type not in ['person', 'church']:
            flash('Invalid contact type', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            # Read the file
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            # Get the fieldnames from the CSV
            fieldnames = csv_reader.fieldnames
            
            # Check for required fields based on contact type
            required_fields = []
            if contact_type == 'person':
                required_fields = ['first_name', 'last_name', 'email']
            else:  # church
                required_fields = ['church_name', 'email']
            
            missing_fields = [field for field in required_fields if field not in fieldnames]
            if missing_fields:
                flash(f'Missing required fields: {", ".join(missing_fields)}', 'error')
                return redirect(request.url)
            
            # Reset the stream position
            stream.seek(0)
            csv_reader = csv.DictReader(stream)
            
            # Process the CSV data
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
                try:
                    # Create a new contact based on the type
                    if contact_type == 'person':
                        contact = Person(
                            first_name=row.get('first_name', ''),
                            last_name=row.get('last_name', ''),
                            email=row.get('email', ''),
                            phone=row.get('phone', ''),
                            address=row.get('address', ''),
                            city=row.get('city', ''),
                            state=row.get('state', ''),
                            zip_code=row.get('zip_code', ''),
                            country=row.get('country', ''),
                            church_role=row.get('church_role', ''),
                            spouse_first_name=row.get('spouse_first_name', ''),
                            spouse_last_name=row.get('spouse_last_name', ''),
                            home_country=row.get('home_country', ''),
                            notes=row.get('notes', ''),
                            user_id=user_id,
                            type='person'
                        )
                    else:  # church
                        contact = Church(
                            church_name=row.get('church_name', ''),
                            email=row.get('email', ''),
                            phone=row.get('phone', ''),
                            address=row.get('address', ''),
                            city=row.get('city', ''),
                            state=row.get('state', ''),
                            zip_code=row.get('zip_code', ''),
                            country=row.get('country', ''),
                            location=row.get('location', ''),
                            website=row.get('website', ''),
                            denomination=row.get('denomination', ''),
                            senior_pastor_first_name=row.get('senior_pastor_first_name', ''),
                            senior_pastor_last_name=row.get('senior_pastor_last_name', ''),
                            senior_pastor_email=row.get('senior_pastor_email', ''),
                            missions_pastor_first_name=row.get('missions_pastor_first_name', ''),
                            missions_pastor_last_name=row.get('missions_pastor_last_name', ''),
                            missions_pastor_email=row.get('missions_pastor_email', ''),
                            congregation_size=row.get('congregation_size', ''),
                            year_founded=row.get('year_founded', ''),
                            notes=row.get('notes', '')
                        )
                    
                    # Save to database
                    with session_scope() as session:
                        session.add(contact)
                        session.commit()
                    
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Error in row {row_num}: {str(e)}")
            
            # Report results
            if imported_count > 0:
                flash(f'Successfully imported {imported_count} {contact_type}(s)', 'success')
            
            if errors:
                for error in errors[:5]:  # Show only first 5 errors to avoid overwhelming the user
                    flash(error, 'error')
                if len(errors) > 5:
                    flash(f'... and {len(errors) - 5} more errors', 'error')
            
            # Redirect to the appropriate page
            if contact_type == 'person':
                return redirect(url_for('people_bp.people'))
            else:
                return redirect(url_for('churches_bp.churches'))
        else:
            flash('File must be a CSV', 'error')
            return redirect(request.url)
    
    # GET request - show the import form
    return render_template('import_csv.html') 