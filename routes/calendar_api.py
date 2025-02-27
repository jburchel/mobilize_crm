"""
Blueprint for Google Calendar integration with Tasks
"""
from flask import Blueprint, request, jsonify, current_app
from models import Task, session_scope
from utils.google_calendar import (
    build_calendar_service, 
    create_event_from_task, 
    update_event_from_task, 
    delete_event,
    get_events
)
from routes.google_auth import auth_required, get_access_token_from_header
import logging
from datetime import datetime, timedelta

calendar_api = Blueprint('calendar_api', __name__)
logger = logging.getLogger(__name__)

@calendar_api.route('/api/calendar/sync-task/<int:task_id>', methods=['POST'])
@auth_required
def sync_task_to_calendar(task_id):
    """Sync a specific task to Google Calendar"""
    # Get Google access token from header
    token = get_access_token_from_header()
    if not token:
        return jsonify({
            'success': False,
            'message': 'Google access token required'
        }), 401
    
    try:
        # Build the Calendar service
        calendar_service = build_calendar_service(token)
        
        with session_scope() as session:
            # Get the task
            task = session.query(Task).get(task_id)
            if not task:
                return jsonify({
                    'success': False,
                    'message': f'Task with ID {task_id} not found'
                }), 404
            
            # Validate due_date before proceeding
            if not task.due_date:
                logger.error(f"Task {task_id} has no due date")
                return jsonify({
                    'success': False,
                    'message': 'due_date: Not a valid date. Please set a due date for this task before syncing.'
                }), 400
            
            try:
                # Check if the task already has a Google Calendar event
                if task.google_calendar_event_id:
                    # Update existing event
                    event = update_event_from_task(
                        calendar_service, 
                        task, 
                        task.google_calendar_event_id
                    )
                else:
                    # Create new event
                    event = create_event_from_task(calendar_service, task)
                    # Store the event ID
                    task.google_calendar_event_id = event['id']
                
                # Update sync status
                task.google_calendar_sync_enabled = True
                task.last_synced_at = datetime.now()
                
                return jsonify({
                    'success': True,
                    'message': f'Task successfully synced to Google Calendar',
                    'event_id': task.google_calendar_event_id
                })
            except ValueError as e:
                # Handle specific value errors (like missing due date)
                logger.error(f"Value error syncing task to calendar: {e}")
                return jsonify({
                    'success': False,
                    'message': str(e)
                }), 400
            
    except Exception as e:
        logger.error(f"Error syncing task to calendar: {e}")
        return jsonify({
            'success': False,
            'message': f'Error syncing task to Google Calendar: {str(e)}'
        }), 500

@calendar_api.route('/api/calendar/unsync-task/<int:task_id>', methods=['POST'])
@auth_required
def unsync_task_from_calendar(task_id):
    """Remove a task from Google Calendar and disable sync"""
    # Get Google access token from header
    token = get_access_token_from_header()
    if not token:
        return jsonify({
            'success': False,
            'message': 'Google access token required'
        }), 401
    
    try:
        # Build the Calendar service
        calendar_service = build_calendar_service(token)
        
        with session_scope() as session:
            # Get the task
            task = session.query(Task).get(task_id)
            if not task:
                return jsonify({
                    'success': False,
                    'message': f'Task with ID {task_id} not found'
                }), 404
            
            # Check if the task has a Google Calendar event
            if task.google_calendar_event_id:
                # Delete the event
                delete_event(calendar_service, task.google_calendar_event_id)
                
                # Update task record
                task.google_calendar_event_id = None
                task.google_calendar_sync_enabled = False
                task.last_synced_at = datetime.now()
                
                return jsonify({
                    'success': True,
                    'message': f'Task successfully unsynced from Google Calendar'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': f'Task was not synced to Google Calendar'
                })
            
    except Exception as e:
        logger.error(f"Error unsyncing task from calendar: {e}")
        return jsonify({
            'success': False,
            'message': f'Error unsyncing task from Google Calendar: {str(e)}'
        }), 500

@calendar_api.route('/api/calendar/toggle-sync/<int:task_id>', methods=['POST'])
@auth_required
def toggle_sync_status(task_id):
    """Toggle the sync status for a task"""
    try:
        with session_scope() as session:
            # Get the task
            task = session.query(Task).get(task_id)
            if not task:
                return jsonify({
                    'success': False,
                    'message': f'Task with ID {task_id} not found'
                }), 404
            
            # Toggle the sync status
            new_status = not task.google_calendar_sync_enabled
            task.google_calendar_sync_enabled = new_status
            
            # If enabling sync, we need to create the event
            if new_status and not task.google_calendar_event_id:
                return jsonify({
                    'success': True,
                    'message': 'Sync enabled. Please sync task to create calendar event.',
                    'sync_enabled': True,
                    'needs_sync': True
                })
            
            return jsonify({
                'success': True,
                'message': f'Sync {"enabled" if new_status else "disabled"} for task',
                'sync_enabled': new_status
            })
            
    except Exception as e:
        logger.error(f"Error toggling sync status: {e}")
        return jsonify({
            'success': False,
            'message': f'Error updating sync status: {str(e)}'
        }), 500

@calendar_api.route('/api/calendar/upcoming-events', methods=['GET'])
@auth_required
def get_upcoming_events():
    """Get upcoming events from Google Calendar and CRM tasks"""
    logger.info("Fetching upcoming events...")
    token = get_access_token_from_header()
    if not token:
        logger.error("No token found in request")
        return jsonify({
            'success': False,
            'message': 'Google access token required'
        }), 401
    
    try:
        calendar_service = build_calendar_service(token)
        logger.info("Calendar service built successfully")
        
        # Get events for next 7 days
        time_min = datetime.utcnow()
        time_max = time_min + timedelta(days=7)
        
        logger.info(f"Fetching events between {time_min} and {time_max}")
        
        # Get events from Google Calendar
        events = get_events(
            calendar_service,
            time_min=time_min.isoformat() + 'Z',
            time_max=time_max.isoformat() + 'Z'
        )
        logger.info(f"Found {len(events)} events in Google Calendar")
        
        # Get synced tasks from database
        with session_scope() as session:
            tasks = session.query(Task).filter(
                Task.google_calendar_sync_enabled == True,
                Task.due_date >= time_min.date(),
                Task.due_date <= time_max.date()
            ).all()
            logger.info(f"Found {len(tasks)} synced tasks in database")
            
            # Format events for response
            formatted_events = []
            
            # Add Google Calendar events
            for event in events:
                # Only include events that are linked to CRM tasks
                task_id = event.get('extendedProperties', {}).get('private', {}).get('mobilizeCrmTaskId')
                if task_id:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    formatted_events.append({
                        'id': event['id'],
                        'title': event['summary'],
                        'start': start,
                        'status': event.get('extendedProperties', {}).get('private', {}).get('mobilizeCrmTaskStatus', 'Not Started'),
                        'priority': event.get('extendedProperties', {}).get('private', {}).get('mobilizeCrmTaskPriority', 'Medium')
                    })
            
            # Add any tasks that should be synced but aren't yet
            for task in tasks:
                if not task.google_calendar_event_id:
                    formatted_events.append({
                        'id': f'task_{task.id}',
                        'title': task.title,
                        'start': task.due_date.isoformat() if task.due_date else datetime.now().isoformat(),
                        'status': task.status,
                        'priority': task.priority
                    })
            
            # Sort events by start time
            formatted_events.sort(key=lambda x: x['start'])
            logger.info(f"Returning {len(formatted_events)} formatted events")
            
            return jsonify({
                'success': True,
                'events': formatted_events
            })
            
    except Exception as e:
        logger.error(f"Error fetching upcoming events: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error fetching upcoming events: {str(e)}'
        }), 500