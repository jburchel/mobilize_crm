from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app, flash
from flask_restx import Resource, Namespace, fields
from models import session_scope, Task, Person, Church, task_schema
from datetime import datetime
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
            with session_scope() as session:
                tasks = session.query(Task).all()
                return task_schema.dump(tasks, many=True)
        except Exception as e:
            current_app.logger.error(f'Error fetching tasks: {str(e)}')
            return {'error': 'Internal server error'}, 500

    @api.doc('create_task')
    @api.expect(task_model)
    def post(self):
        """Create a new task"""
        try:
            data = task_schema.load(request.json)
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
            with session_scope() as session:
                task = session.query(Task).get(id)
                if not task:
                    return {'error': 'Task not found'}, 404
                return task_schema.dump(task)
        except Exception as e:
            current_app.logger.error(f'Error fetching task {id}: {str(e)}')
            return {'error': 'Internal server error'}, 500

    @api.doc('update_task')
    def put(self, id):
        """Update a task"""
        try:
            data = task_schema.load(request.json, partial=True)
            with session_scope() as session:
                task = session.query(Task).get(id)
                if not task:
                    return {'error': 'Task not found'}, 404
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
            with session_scope() as session:
                task = session.query(Task).get(id)
                if not task:
                    return {'error': 'Task not found'}, 404
                session.delete(task)
                current_app.logger.info(f'Task {id} deleted')
                return {'message': 'Task deleted successfully'}
        except Exception as e:
            current_app.logger.error(f'Error deleting task {id}: {str(e)}')
            return {'error': 'Internal server error'}, 500

# Web interface routes
@tasks_bp.route('/tasks')
def tasks():
    current_app.logger.info("Loading tasks page...")
    try:
        with session_scope() as session:
            current_app.logger.debug("Querying database for tasks...")
            tasks = session.query(Task).order_by(Task.due_date.desc()).all()
            current_app.logger.debug(f"Found {len(tasks)} tasks")
            
            current_app.logger.debug("Querying database for people...")
            people = session.query(Person).all()
            current_app.logger.debug(f"Found {len(people)} people")
            
            current_app.logger.debug("Querying database for churches...")
            churches = session.query(Church).all()
            current_app.logger.debug(f"Found {len(churches)} churches")
            
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

@tasks_bp.route('/add_task', methods=['POST'])
def add_task():
    try:
        # Log incoming form data for debugging
        current_app.logger.info("Received task form data: %s", request.form)
        
        # Get the due date from form
        due_date = request.form.get('due_date')
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
            'due_date': due_date,  # Keep as string, schema will handle conversion
            'priority': request.form.get('priority', 'Medium'),
            'status': request.form['status'],
            'person_id': request.form.get('person_id') or None,
            'church_id': request.form.get('church_id') or None,
            'google_calendar_sync_enabled': bool(request.form.get('google_calendar_sync_enabled'))
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
            flash(f'{field}: {", ".join(errors)}', 'error')
        return redirect(url_for('tasks_bp.tasks'))
    except Exception as e:
        current_app.logger.error('Unexpected error in task creation: %s', str(e), exc_info=True)
        flash('An unexpected error occurred while creating the task.', 'error')
        return redirect(url_for('tasks_bp.tasks'))

@tasks_bp.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    try:
        # Log incoming form data for debugging
        current_app.logger.info("Received edit task form data: %s", request.form)
        
        # Get the due date from form
        due_date = request.form.get('due_date')
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
            'due_date': due_date,  # Keep as string, schema will handle conversion
            'priority': request.form.get('priority', 'Medium'),
            'status': request.form['status'],
            'person_id': request.form.get('person_id') or None,
            'church_id': request.form.get('church_id') or None,
            'google_calendar_sync_enabled': bool(request.form.get('google_calendar_sync_enabled'))
        }
        
        # Log the processed data
        current_app.logger.debug("Processing task data: %s", data)
        
        # Validate data using schema
        try:
            validated_data = task_schema.load(data, partial=True)
            current_app.logger.debug("Data validated successfully: %s", validated_data)
        except ValidationError as err:
            current_app.logger.error("Validation error: %s", err.messages)
            for field, errors in err.messages.items():
                flash(f"{field}: {', '.join(errors)}", 'error')
            return redirect(url_for('tasks_bp.tasks'))
        
        with session_scope() as session:
            task = session.query(Task).get(task_id)
            if not task:
                flash('Task not found', 'error')
                return redirect(url_for('tasks_bp.tasks'))
                
            # Update task with validated data
            for key, value in validated_data.items():
                setattr(task, key, value)
            
            flash('Task updated successfully', 'success')
            return redirect(url_for('tasks_bp.tasks'))
            
    except Exception as e:
        current_app.logger.error(f"Error updating task: {e}")
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(url_for('tasks_bp.tasks'))
