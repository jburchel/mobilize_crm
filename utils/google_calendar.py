"""
Google Calendar integration for Mobilize CRM
This module provides functions to interact with Google Calendar API
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def build_calendar_service(token):
    """Build a Google Calendar service object with the provided token"""
    try:
        credentials = Credentials(
            token=token,
            refresh_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=current_app.config['GOOGLE_CLIENT_ID'],
            client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Error building calendar service: {e}")
        raise

def get_calendar_list(service):
    """Get list of calendars for the authenticated user"""
    try:
        calendar_list = service.calendarList().list().execute()
        return calendar_list.get('items', [])
    except HttpError as error:
        logger.error(f"Error retrieving calendar list: {error}")
        raise

def create_event_from_task(service, task, calendar_id='primary'):
    """
    Create a Google Calendar event from a task
    
    Args:
        service: Google Calendar service object
        task: Task model instance
        calendar_id: ID of the calendar to create the event in (default: primary)
        
    Returns:
        Created event object from Google Calendar API
    """
    try:
        # Ensure we have a valid date
        if not task.due_date:
            logger.error(f"Task {task.id} has no due date")
            raise ValueError("Task must have a due date to create a calendar event")
        
        # Format event data from task
        event_data = {
            'summary': task.title,
            'description': task.description or '',
            'start': {
                'date': task.due_date.isoformat() if task.due_date else datetime.now().date().isoformat(),
            },
            'end': {
                'date': task.due_date.isoformat() if task.due_date else 
                      (datetime.now() + timedelta(days=1)).date().isoformat(),
            },
        }
        
        # Add metadata to link back to the CRM task
        event_data['extendedProperties'] = {
            'private': {
                'mobilizeCrmTaskId': str(task.id),
                'mobilizeCrmTaskStatus': task.status,
                'mobilizeCrmTaskPriority': task.priority,
            }
        }
        
        # Create the event
        event = service.events().insert(calendarId=calendar_id, body=event_data).execute()
        
        logger.info(f"Created calendar event with ID: {event.get('id')} for task: {task.id}")
        return event
    
    except HttpError as error:
        logger.error(f"Error creating calendar event: {error}")
        raise

def update_event_from_task(service, task, event_id, calendar_id='primary'):
    """
    Update a Google Calendar event from a task
    
    Args:
        service: Google Calendar service object
        task: Task model instance
        event_id: Google Calendar event ID to update
        calendar_id: ID of the calendar containing the event (default: primary)
        
    Returns:
        Updated event object from Google Calendar API
    """
    try:
        # Ensure we have a valid date
        if not task.due_date:
            logger.error(f"Task {task.id} has no due date")
            raise ValueError("Task must have a due date to update a calendar event")
            
        # Format event data from task
        event_data = {
            'summary': task.title,
            'description': task.description or '',
            'start': {
                'date': task.due_date.isoformat() if task.due_date else datetime.now().date().isoformat(),
            },
            'end': {
                'date': task.due_date.isoformat() if task.due_date else 
                      (datetime.now() + timedelta(days=1)).date().isoformat(),
            },
        }
        
        # Update metadata
        event_data['extendedProperties'] = {
            'private': {
                'mobilizeCrmTaskId': str(task.id),
                'mobilizeCrmTaskStatus': task.status,
                'mobilizeCrmTaskPriority': task.priority,
            }
        }
        
        # Update the event
        event = service.events().update(
            calendarId=calendar_id, 
            eventId=event_id, 
            body=event_data
        ).execute()
        
        logger.info(f"Updated calendar event with ID: {event.get('id')} for task: {task.id}")
        return event
    
    except HttpError as error:
        logger.error(f"Error updating calendar event: {error}")
        raise

def delete_event(service, event_id, calendar_id='primary'):
    """
    Delete a Google Calendar event
    
    Args:
        service: Google Calendar service object
        event_id: Google Calendar event ID to delete
        calendar_id: ID of the calendar containing the event (default: primary)
    """
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info(f"Deleted calendar event with ID: {event_id}")
        return True
    except HttpError as error:
        logger.error(f"Error deleting calendar event: {error}")
        raise

def get_events(service, time_min=None, time_max=None, calendar_id='primary', max_results=100):
    """
    Get events from Google Calendar within a time range
    
    Args:
        service: Google Calendar service object
        time_min: Start time for events (default: now)
        time_max: End time for events (default: 30 days from now)
        calendar_id: ID of the calendar to get events from (default: primary)
        max_results: Maximum number of events to return (default: 100)
        
    Returns:
        List of events from Google Calendar API
    """
    try:
        # Default time range if not provided
        if time_min is None:
            time_min = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        if time_max is None:
            time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
    
    except HttpError as error:
        logger.error(f"Error getting calendar events: {error}")
        raise