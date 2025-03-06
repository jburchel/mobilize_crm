from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, flash
from flask_restx import Resource, Namespace, fields
from models import Task, Person, Church, task_schema
from datetime import datetime, timedelta
from database import db, session_scope
from routes.dashboard import auth_required
from routes.google_auth import get_current_user_id
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError

api = Namespace('tasks', description='Task operations')

# Define the task_model for request validation and documentation
task_model = api.model('Task', {
    'id': fields.Integer(readOnly=True, description='The unique identifier of a task'),
    'title': fields.String(required=True, description='Task title'),
    'description': fields.String(description='Task description'),
    'due_date': fields.String(description='Due date in YYYY-MM-DD format'),
    'priority': fields.String(description='Task priority (e.g. High, Medium, Low)'),
    'status': fields.String(required=True, description='Task status'),
    'person_id': fields.Integer(description='ID of the person assigned'),
    'church_id': fields.Integer(description='ID of the church associated')
})

tasks_bp = Blueprint('tasks_bp', __name__)

@api.route('/')
class TaskList(Resource):
    @api.doc('list_tasks')
    def get(self):
        """List all tasks"""
        try:
            # Get the current user ID
            user_id = get_current_user_id()
            if not user_id:
                current_app.logger.warning("No user ID found in session, cannot list tasks")
                return {'error': 'Authentication required'}, 401
                
            with session_scope() as session:
                tasks = session.query(Task).filter(Task.user_id == user_id).all()
                return task_schema.dump(tasks, many=True)
        except Exception as e:
            current_app.logger.error(f'Error fetching tasks: {str(e)}')
            return {'error': 'Internal server error'}, 500

    @api.doc('create_task')
    @api.expect(task_model)
    def post(self):
        """Create a new task"""
        try:
            # Get the current user ID
            user_id = get_current_user_id()
            if not user_id:
                current_app.logger.warning("No user ID found in session, cannot create task")
                return {'error': 'Authentication required'}, 401
                
            data = task_schema.load(request.json)
            # Add user_id to the task data
            data['user_id'] = user_id
            
            with session_scope() as session:
                new_task = Task(**data)
                session.add(new_task)
                current_app.logger.info(f'Task created: {data["title"]}')
                return task_schema.dump(new_task), 201
        except ValidationError as err:
            current_app.logger.warning(f'Validation error in task creation: {err.messages}')
            return {'error': err.messages}, 400
        except SQLAlchemyError as e:
            current_app.logger.error(f'Database error in task creation: {str(e)}')
            return {'error': 'Database error occurred'}, 500
        except Exception as e:
            current_app.logger.error(f'Unexpected error in task creation: {str(e)}')
            return {'error': 'Internal server error'}, 500

@api.route('/<int:id>')
class TaskDetail(Resource):
    @api.doc('get_task')
    def get(self, id):
        """Get a task by ID"""
        try:
            # Get the current user ID
            user_id = get_current_user_id()
            if not user_id:
                current_app.logger.warning("No user ID found in session, cannot get task")
                return {'error': 'Authentication required'}, 401
                
            with session_scope() as session:
                task = session.query(Task).get(id)
                if not task:
                    return {'error': 'Task not found'}, 404
                    
                # Verify that the user owns this task
                if task.user_id != user_id:
                    current_app.logger.warning(f"User {user_id} attempted to view task {id} owned by {task.user_id}")
                    return {'error': 'You do not have permission to view this task'}, 403
                    
                return task_schema.dump(task)
        except Exception as e:
            current_app.logger.error(f'Error fetching task {id}: {str(e)}')
            return {'error': 'Internal server error'}, 500

    @api.doc('update_task')
    def put(self, id):
        """Update a task"""
        try:
            # Get the current user ID
            user_id = get_current_user_id()
            if not user_id:
                current_app.logger.warning("No user ID found in session, cannot update task")
                return {'error': 'Authentication required'}, 401
                
            data = task_schema.load(request.json, partial=True)
            with session_scope() as session:
                task = session.query(Task).get(id)
                if not task:
                    return {'error': 'Task not found'}, 404
                    
                # Verify that the user owns this task
                if task.user_id != user_id:
                    current_app.logger.warning(f"User {user_id} attempted to update task {id} owned by {task.user_id}")
                    return {'error': 'You do not have permission to update this task'}, 403
                    
                for key, value in data.items():
                    setattr(task, key, value)
                current_app.logger.info(f'Task {id} updated')
                return task_schema.dump(task)
        except ValidationError as err:
            current_app.logger.warning(f'Validation error in task update: {err.messages}')
            return {'error': err.messages}, 400
        except Exception as e:
            current_app.logger.error(f'Error updating task {id}: {str(e)}')
            return {'error': 'Internal server error'}, 500

    @api.doc('delete_task')
    def delete(self, id):
        """Delete a task"""
        try:
            # Get the current user ID
            user_id = get_current_user_id()
            if not user_id:
                current_app.logger.warning("No user ID found in session, cannot delete task")
                return {'error': 'Authentication required'}, 401
                
            with session_scope() as session:
                task = session.query(Task).get(id)
                if not task:
                    return {'error': 'Task not found'}, 404
                    
                # Verify that the user owns this task
                if task.user_id != user_id:
                    current_app.logger.warning(f"User {user_id} attempted to delete task {id} owned by {task.user_id}")
                    return {'error': 'You do not have permission to delete this task'}, 403
                    
                session.delete(task)
                current_app.logger.info(f'Task {id} deleted')
                return {'message': 'Task deleted successfully'}
        except Exception as e:
            current_app.logger.error(f'Error deleting task {id}: {str(e)}')
            return {'error': 'Internal server error'}, 500

# Web interface routes
@tasks_bp.route('/')
def tasks():
    current_app.logger.info("Loading tasks page...")
    try:
        # Get the current user ID
        user_id = get_current_user_id()
        if not user_id:
            current_app.logger.warning("No user ID found in session, redirecting to login")
            return redirect(url_for('dashboard_bp.dashboard'))
            
        with session_scope() as session:
            current_app.logger.debug("Querying database for tasks...")
            # Filter tasks by user_id
            tasks = session.query(Task).filter(Task.user_id == user_id).order_by(Task.due_date.desc()).all()
            current_app.logger.debug(f"Found {len(tasks)} tasks for user {user_id}")
            
            current_app.logger.debug("Querying database for people...")
            people = session.query(Person).all()
            current_app.logger.debug(f"Found {len(people)} people")
            
            # Log details about people for debugging
            current_app.logger.debug("People data for dropdowns:")
            for person in people:
                current_app.logger.debug(f"Person: ID={person.id}, Name={person.get_name()}, "
                                       f"Type={person.type}, Email={person.email}")
                # Check if get_name method returns a valid value
                if not person.get_name() or person.get_name().strip() == '':
                    current_app.logger.warning(f"Person ID {person.id} has empty name: first_name='{person.first_name}', last_name='{person.last_name}'")
            
            current_app.logger.debug("Querying database for churches...")
            churches = session.query(Church).all()
            current_app.logger.debug(f"Found {len(churches)} churches")
            
            # Log details about churches for debugging
            current_app.logger.debug("Church data for dropdowns:")
            for church in churches:
                current_app.logger.debug(f"Church: ID={church.id}, Name={church.get_name()}, "
                                       f"Type={church.type}, Email={church.email}")
                # Check if get_name method returns a valid value
                if not church.get_name() or church.get_name().strip() == '':
                    current_app.logger.warning(f"Church ID {church.id} has empty name: church_name='{church.church_name}'")
            
            # Add debug logging for template context
            current_app.logger.debug("Rendering template with context: tasks=%d, people=%d, churches=%d", 
                                   len(tasks), len(people), len(churches))
            
            return render_template('tasks.html', 
                                tasks=tasks, 
                                people=people, 
                                churches=churches)
    except SQLAlchemyError as e:
        current_app.logger.error(f'Database error in tasks page: {str(e)}', exc_info=True)
        flash('A database error occurred. Please try again later.', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))
    except Exception as e:
        current_app.logger.error(f'Error in tasks page: {str(e)}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(url_for('dashboard_bp.dashboard'))

@tasks_bp.route('/add', methods=['POST'])
def add_task():
    try:
        # Get the current user ID
        user_id = get_current_user_id()
        if not user_id:
            current_app.logger.warning("No user ID found in session, cannot create task")
            flash('You must be logged in to create tasks', 'error')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        # Log incoming form data for debugging
        current_app.logger.info("Received task form data: %s", request.form)
        
        # Get the due date from form
        due_date = request.form.get('due_date', '').strip()
        if due_date:
            try:
                # Ensure date is in MM/DD/YYYY format
                datetime.strptime(due_date, '%m/%d/%Y')
                current_app.logger.info(f"Valid date format received: {due_date}")
            except ValueError:
                current_app.logger.error(f"Invalid date format received: {due_date}")
                flash('Please enter the due date in MM/DD/YYYY format', 'error')
                return redirect(url_for('tasks_bp.tasks'))
        
        # Create task data from form
        data = {
            'title': request.form['title'],
            'description': request.form.get('description'),
            'due_date': due_date if due_date else None,  # Handle empty string
            'due_time': request.form.get('due_time'),  # Get due time
            'reminder_time': request.form.get('reminder_time'),  # Get reminder time
            'priority': request.form.get('priority', 'Medium'),
            'status': request.form['status'],
            'person_id': request.form.get('person_id') or None,
            'church_id': request.form.get('church_id') or None,
            'google_calendar_sync_enabled': bool(request.form.get('google_calendar_sync_enabled')),
            'user_id': user_id  # Add the user_id to the task data
        }
        
        # Log the processed data
        current_app.logger.debug("Processing task data: %s", data)
        
        # Validate data using schema
        try:
            validated_data = task_schema.load(data)
            current_app.logger.debug("Data validated successfully: %s", validated_data)
        except ValidationError as err:
            current_app.logger.error("Validation error: %s", err.messages)
            raise
        
        with session_scope() as session:
            new_task = Task(**validated_data)
            session.add(new_task)
            session.flush()  # This gets us the ID of the new task
            task_id = new_task.id
            current_app.logger.info(f'Task created successfully: {data["title"]} (ID: {task_id})')
            flash('Task created successfully!', 'success')
            
            if validated_data.get('google_calendar_sync_enabled'):
                current_app.logger.info("Google Calendar sync enabled for task %s", task_id)
                return redirect(url_for('tasks_bp.tasks', new_task_id=task_id, sync_enabled=True))
            
            return redirect(url_for('tasks_bp.tasks'))
            
    except ValidationError as err:
        current_app.logger.warning('Validation error in task creation: %s', err.messages)
        for field, errors in err.messages.items():
            flash(f"{field}: {', '.join(errors)}", 'error')
        return redirect(url_for('tasks_bp.tasks'))
    except Exception as e:
        current_app.logger.error('Error in task creation: %s', str(e), exc_info=True)
        flash('An error occurred while creating the task. Please try again.', 'error')
        return redirect(url_for('tasks_bp.tasks'))

@tasks_bp.route('/edit/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    try:
        # Get the current user ID
        user_id = get_current_user_id()
        if not user_id:
            current_app.logger.warning("No user ID found in session, cannot edit task")
            flash('You must be logged in to edit tasks', 'error')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        # Log incoming form data for debugging
        current_app.logger.info("Received task edit form data: %s", request.form)
        
        # Get the due date from form
        due_date = request.form.get('due_date', '').strip()
        if due_date:
            try:
                # Ensure date is in MM/DD/YYYY format
                datetime.strptime(due_date, '%m/%d/%Y')
                current_app.logger.info(f"Valid date format received: {due_date}")
            except ValueError:
                current_app.logger.error(f"Invalid date format received: {due_date}")
                flash('Please enter the due date in MM/DD/YYYY format', 'error')
                return redirect(url_for('tasks_bp.tasks'))
        
        # Create task data from form
        data = {
            'title': request.form['title'],
            'description': request.form.get('description'),
            'due_date': due_date if due_date else None,  # Handle empty string
            'due_time': request.form.get('due_time'),  # Get due time
            'reminder_time': request.form.get('reminder_time'),  # Get reminder time
            'priority': request.form.get('priority', 'Medium'),
            'status': request.form['status'],
            'person_id': request.form.get('person_id') or None,
            'church_id': request.form.get('church_id') or None,
            'google_calendar_sync_enabled': bool(request.form.get('google_calendar_sync_enabled'))
            # Note: We don't include user_id here as we'll verify ownership below
        }
        
        # Log the processed data
        current_app.logger.debug("Processing task edit data: %s", data)
        
        # Validate data using schema
        try:
            validated_data = task_schema.load(data, partial=True)
            current_app.logger.debug("Data validated successfully: %s", validated_data)
        except ValidationError as err:
            current_app.logger.error("Validation error: %s", err.messages)
            raise
        
        with session_scope() as session:
            task = session.query(Task).get(task_id)
            if not task:
                flash('Task not found', 'error')
                return redirect(url_for('tasks_bp.tasks'))
                
            # Verify that the user owns this task
            if task.user_id != user_id:
                current_app.logger.warning(f"User {user_id} attempted to edit task {task_id} owned by {task.user_id}")
                flash('You do not have permission to edit this task', 'error')
                return redirect(url_for('tasks_bp.tasks'))
                
            # Update task fields
            for key, value in validated_data.items():
                setattr(task, key, value)
                
            # If sync is enabled and task has changed, mark for re-sync
            if task.google_calendar_sync_enabled:
                task.last_synced_at = None
                
            current_app.logger.info(f'Task updated successfully: {task.title} (ID: {task_id})')
            flash('Task updated successfully!', 'success')
            
            if task.google_calendar_sync_enabled:
                return redirect(url_for('tasks_bp.tasks', updated_task_id=task_id, sync_enabled=True))
            
            return redirect(url_for('tasks_bp.tasks'))
            
    except ValidationError as err:
        current_app.logger.warning('Validation error in task update: %s', err.messages)
        for field, errors in err.messages.items():
            flash(f"{field}: {', '.join(errors)}", 'error')
        return redirect(url_for('tasks_bp.tasks'))
    except Exception as e:
        current_app.logger.error('Error in task update: %s', str(e), exc_info=True)
        flash('An error occurred while updating the task. Please try again.', 'error')
        return redirect(url_for('tasks_bp.tasks'))

@tasks_bp.route('/get_task/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get task data for the edit form"""
    try:
        # Get the current user ID
        user_id = get_current_user_id()
        if not user_id:
            current_app.logger.warning("No user ID found in session, cannot get task")
            return jsonify({'success': False, 'message': 'Authentication required'})
            
        with session_scope() as session:
            task = session.query(Task).get(task_id)
            if not task:
                return jsonify({'success': False, 'message': 'Task not found'})
                
            # Verify that the user owns this task
            if task.user_id != user_id:
                current_app.logger.warning(f"User {user_id} attempted to view task {task_id} owned by {task.user_id}")
                return jsonify({'success': False, 'message': 'You do not have permission to view this task'})
            
            # Convert task to dictionary
            task_data = {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date.strftime('%m/%d/%Y') if task.due_date else '',
                'due_time': task.due_time,
                'reminder_time': task.reminder_time,
                'priority': task.priority,
                'status': task.status,
                'person_id': task.person_id,
                'church_id': task.church_id,
                'google_calendar_sync_enabled': task.google_calendar_sync_enabled
            }
            
            current_app.logger.info(f'Task data retrieved for ID {task_id}: {task_data}')
            return jsonify({'success': True, 'task': task_data})
    except Exception as e:
        current_app.logger.error(f'Error retrieving task {task_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@tasks_bp.route('/get_description/<int:task_id>', methods=['GET'])
def get_task_description(task_id):
    """Get task description for the edit form"""
    try:
        # Get the current user ID
        user_id = get_current_user_id()
        if not user_id:
            current_app.logger.warning("No user ID found in session, cannot get task description")
            return jsonify({'success': False, 'message': 'Authentication required'})
            
        with session_scope() as session:
            task = session.query(Task).get(task_id)
            if not task:
                return jsonify({'success': False, 'message': 'Task not found'})
                
            # Verify that the user owns this task
            if task.user_id != user_id:
                current_app.logger.warning(f"User {user_id} attempted to view description of task {task_id} owned by {task.user_id}")
                return jsonify({'success': False, 'message': 'You do not have permission to view this task'})
            
            return jsonify({'success': True, 'description': task.description})
    except Exception as e:
        current_app.logger.error(f'Error retrieving task description {task_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@tasks_bp.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete a task"""
    try:
        # Get the current user ID
        user_id = get_current_user_id()
        if not user_id:
            current_app.logger.warning("No user ID found in session, cannot delete task")
            flash('You must be logged in to delete tasks', 'error')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        with session_scope() as session:
            task = session.query(Task).get(task_id)
            if not task:
                flash('Task not found', 'error')
                return redirect(url_for('tasks_bp.tasks'))
                
            # Verify that the user owns this task
            if task.user_id != user_id:
                current_app.logger.warning(f"User {user_id} attempted to delete task {task_id} owned by {task.user_id}")
                flash('You do not have permission to delete this task', 'error')
                return redirect(url_for('tasks_bp.tasks'))
            
            # Check if task has a Google Calendar event
            has_calendar_event = task.google_calendar_event_id is not None
            
            # Delete the task
            session.delete(task)
            
            current_app.logger.info(f'Task deleted successfully: ID {task_id}')
            
            if has_calendar_event:
                flash('Task and its Google Calendar event were deleted successfully!', 'success')
            else:
                flash('Task deleted successfully!', 'success')
            
            return redirect(url_for('tasks_bp.tasks'))
    except Exception as e:
        current_app.logger.error(f'Error deleting task {task_id}: {str(e)}', exc_info=True)
        flash(f'An error occurred while deleting the task: {str(e)}', 'error')
        return redirect(url_for('tasks_bp.tasks'))
