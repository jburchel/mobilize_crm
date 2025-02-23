from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
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
    try:
        with session_scope() as session:
            tasks = session.query(Task).all()
            people = session.query(Person).all()
            churches = session.query(Church).all()
            return render_template('tasks.html', 
                                tasks=tasks, 
                                people=people, 
                                churches=churches)
    except Exception as e:
        current_app.logger.error(f'Error in tasks page: {str(e)}')
        return render_template('500.html'), 500

@tasks_bp.route('/add_task', methods=['POST'])
def add_task():
    try:
        data = {
            'title': request.form['title'],
            'description': request.form.get('description'),
            'due_date': datetime.strptime(request.form['due_date'], '%Y-%m-%d').date() if request.form.get('due_date') else None,
            'priority': request.form.get('priority', 'Medium'),
            'status': request.form['status'],
            'person_id': request.form.get('person_id') or None,
            'church_id': request.form.get('church_id') or None
        }
        
        # Validate data
        task_schema.load(data)
        
        with session_scope() as session:
            new_task = Task(**data)
            session.add(new_task)
            current_app.logger.info(f'Task created via web interface: {data["title"]}')
        
        return redirect(url_for('tasks_bp.tasks'))
    except ValidationError as err:
        current_app.logger.warning(f'Validation error in web task creation: {err.messages}')
        # Flash error messages would go here if we had Flask-Flash set up
        return redirect(url_for('tasks_bp.tasks'))
    except Exception as e:
        current_app.logger.error(f'Error in web task creation: {str(e)}')
        return render_template('500.html'), 500
