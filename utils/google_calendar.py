"""
Google Calendar integration for Mobilize CRM
This module provides functions to interact with Google Calendar API
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta, time
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def build_calendar_service(token):
    """Build a Google Calendar service object with the provided token"""
    try:
        if not token:
            logger.error("No token provided to build calendar service")
            return None
            
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
        return None

def get_calendar_list(service):
    """Get list of calendars for the authenticated user"""
    try:
        if not service:
            logger.error("Calendar service is not available")
            return []
            
        calendar_list = service.calendarList().list().execute()
        return calendar_list.get('items', [])
    except HttpError as error:
        logger.error(f"Error retrieving calendar list: {error}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving calendar list: {e}")
        return []

def create_event_from_task(service, task):
    """
    Create a Google Calendar event from a task
    
    Args:
        service: Google Calendar service object
        task: Task object to create event from
        
    Returns:
        Created event object from Google Calendar API
    """
    try:
        # Get task details
        title = task.title
        description = task.description or ''
        due_date = task.due_date
        
        # Handle time component
        start_datetime = None
        end_datetime = None
        
        if due_date:
            # If we have a due_time, use it to create a datetime event
            if task.due_time:
                # Parse the time string (HH:MM)
                hour, minute = map(int, task.due_time.split(':'))
                
                # Create datetime objects for start and end
                start_datetime = datetime.combine(due_date, time(hour, minute, 0))
                end_datetime = start_datetime + timedelta(hours=1)  # Default to 1 hour duration
                
                # Format for Google Calendar API
                start = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'America/Los_Angeles'  # Use appropriate timezone
                }
                end = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/Los_Angeles'  # Use appropriate timezone
                }
            else:
                # All-day event
                start = {
                    'date': due_date.isoformat()
                }
                end = {
                    'date': due_date.isoformat()
                }
        else:
            # If no due date, default to today
            today = datetime.now().date()
            start = {
                'date': today.isoformat()
            }
            end = {
                'date': today.isoformat()
            }
        
        # Create event object
        event = {
            'summary': title,
            'description': description,
            'start': start,
            'end': end,
            'extendedProperties': {
                'private': {
                    'mobilizeCrmTaskId': str(task.id),
                    'mobilizeCrmTaskStatus': task.status,
                    'mobilizeCrmTaskPriority': task.priority
                }
            }
        }
        
        # Add reminder if specified
        if task.reminder_time and task.reminder_time != '':
            # Convert reminder_time to minutes before event
            minutes = int(task.reminder_time)
            
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': minutes}
                ]
            }
        else:
            # Use default reminders
            event['reminders'] = {
                'useDefault': True
            }
        
        # Create the event
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {created_event.get('htmlLink')}")
        
        return created_event
        
    except HttpError as error:
        logger.error(f"Error creating calendar event: {error}")
        raise

def update_event_from_task(service, task, event_id):
    """
    Update a Google Calendar event from a task
    
    Args:
        service: Google Calendar service object
        task: Task object to update event from
        event_id: ID of the event to update
        
    Returns:
        Updated event object from Google Calendar API
    """
    try:
        # Get task details
        title = task.title
        description = task.description or ''
        due_date = task.due_date
        
        # Handle time component
        start_datetime = None
        end_datetime = None
        
        if due_date:
            # If we have a due_time, use it to create a datetime event
            if task.due_time:
                # Parse the time string (HH:MM)
                hour, minute = map(int, task.due_time.split(':'))
                
                # Create datetime objects for start and end
                start_datetime = datetime.combine(due_date, time(hour, minute, 0))
                end_datetime = start_datetime + timedelta(hours=1)  # Default to 1 hour duration
                
                # Format for Google Calendar API
                start = {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'America/Los_Angeles'  # Use appropriate timezone
                }
                end = {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/Los_Angeles'  # Use appropriate timezone
                }
            else:
                # All-day event
                start = {
                    'date': due_date.isoformat()
                }
                end = {
                    'date': due_date.isoformat()
                }
        else:
            # If no due date, default to today
            today = datetime.now().date()
            start = {
                'date': today.isoformat()
            }
            end = {
                'date': today.isoformat()
            }
        
        # Create event object
        event = {
            'summary': title,
            'description': description,
            'start': start,
            'end': end,
            'extendedProperties': {
                'private': {
                    'mobilizeCrmTaskId': str(task.id),
                    'mobilizeCrmTaskStatus': task.status,
                    'mobilizeCrmTaskPriority': task.priority
                }
            }
        }
        
        # Add reminder if specified
        if task.reminder_time and task.reminder_time != '':
            # Convert reminder_time to minutes before event
            minutes = int(task.reminder_time)
            
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': minutes}
                ]
            }
        else:
            # Use default reminders
            event['reminders'] = {
                'useDefault': True
            }
        
        # Update the event
        updated_event = service.events().update(
            calendarId='primary', 
            eventId=event_id, 
            body=event
        ).execute()
        
        logger.info(f"Event updated: {updated_event.get('htmlLink')}")
        
        return updated_event
        
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
        
        if not service:
            logger.error("Calendar service is not available")
            return []
            
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
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting calendar events: {e}")
        return []