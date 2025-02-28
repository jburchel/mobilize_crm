"""
Background jobs for Mobilize CRM
This module provides functions for running background tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from models import Task, session_scope
from utils.google_calendar import build_calendar_service, update_event_from_task, create_event_from_task
from routes.google_auth import get_user_tokens, get_all_user_tokens
import logging
from datetime import datetime, timedelta
import atexit
from flask import current_app
import requests

logger = logging.getLogger(__name__)

def sync_calendar_tasks():
    """
    Synchronize tasks with Google Calendar
    This function will:
    1. Find all tasks with sync enabled
    2. For each task, check if it needs to be synced (new or updated)
    3. Sync the task with Google Calendar
    """
    logger.info("Running calendar sync background job")
    
    try:
        # Get tasks that need syncing
        with session_scope() as session:
            # Find tasks with sync enabled
            tasks_to_sync = session.query(Task).filter(
                Task.google_calendar_sync_enabled == True,
                # Either never synced or not synced in the last hour
                (
                    (Task.last_synced_at == None) | 
                    (Task.last_synced_at < datetime.now() - timedelta(hours=1))
                )
            ).all()
            
            if not tasks_to_sync:
                logger.info("No tasks need syncing")
                return
                
            logger.info(f"Found {len(tasks_to_sync)} tasks to sync")
            
            # Get user tokens - this assumes a single user system for now
            # In a multi-user system, you would need to determine which user's token to use
            tokens = get_user_tokens()
            if not tokens or not tokens.get('access_token'):
                logger.error("No access token available for calendar sync")
                return
                
            # Build calendar service
            calendar_service = build_calendar_service(tokens.get('access_token'))
            
            # Process each task
            for task in tasks_to_sync:
                try:
                    # Skip tasks without due dates
                    if not task.due_date:
                        logger.warning(f"Task {task.id} has no due date, skipping sync")
                        continue
                        
                    # Check if task has an event ID
                    if task.google_calendar_event_id:
                        # Check for conflicts before updating
                        try:
                            # Try to get the event to see if it still exists
                            event = calendar_service.events().get(
                                calendarId='primary', 
                                eventId=task.google_calendar_event_id
                            ).execute()
                            
                            # Check if the event has been modified in Google Calendar
                            # Compare last sync time with last modification time in Google Calendar
                            if task.last_synced_at:
                                updated_time = datetime.fromisoformat(event['updated'].replace('Z', '+00:00'))
                                
                                # If the event was updated in Google Calendar after our last sync
                                if task.last_synced_at < updated_time:
                                    # Conflict detected - event was modified in Google Calendar
                                    logger.info(f"Conflict detected for task {task.id}: Event modified in Google Calendar")
                                    
                                    # Resolve conflict based on strategy:
                                    # 1. CRM wins - always update Google Calendar with CRM data (current behavior)
                                    # 2. Google Calendar wins - update CRM with Google Calendar data
                                    # 3. Last modified wins - compare timestamps and use the most recent
                                    # 4. Prompt user - not possible in background job
                                    
                                    # For this implementation, we'll use strategy 1: CRM wins
                                    logger.info(f"Resolving conflict: CRM data takes precedence")
                                    
                                    # Continue with update as normal
                                    update_event_from_task(
                                        calendar_service, 
                                        task, 
                                        task.google_calendar_event_id
                                    )
                                else:
                                    # No conflict, proceed with normal update
                                    update_event_from_task(
                                        calendar_service, 
                                        task, 
                                        task.google_calendar_event_id
                                    )
                            else:
                                # No last sync time, just update
                                update_event_from_task(
                                    calendar_service, 
                                    task, 
                                    task.google_calendar_event_id
                                )
                                
                        except Exception as e:
                            # Event might have been deleted in Google Calendar
                            logger.warning(f"Event {task.google_calendar_event_id} not found in Google Calendar: {e}")
                            logger.info(f"Creating new event for task {task.id}")
                            
                            # Create a new event
                            event = create_event_from_task(calendar_service, task)
                            task.google_calendar_event_id = event['id']
                    else:
                        # Create new event
                        logger.info(f"Creating new calendar event for task {task.id}")
                        event = create_event_from_task(calendar_service, task)
                        task.google_calendar_event_id = event['id']
                    
                    # Update sync timestamp
                    task.last_synced_at = datetime.now()
                    
                except Exception as e:
                    logger.error(f"Error syncing task {task.id}: {str(e)}")
                    # Continue with next task
                    continue
    
    except Exception as e:
        logger.error(f"Error in calendar sync job: {str(e)}")

def sync_gmail_emails():
    """
    Background job to sync emails from Gmail for all users with Google integration
    """
    logger.info("Starting Gmail email synchronization job")
    
    try:
        # Get all users with Google tokens
        user_tokens = get_all_user_tokens()
        
        if not user_tokens:
            logger.info("No users with Google tokens found")
            return
        
        # For each user with tokens, sync their emails
        for user_id, tokens in user_tokens.items():
            if not tokens.get('access_token'):
                logger.warning(f"User {user_id} has no access token")
                continue
                
            logger.info(f"Syncing emails for user {user_id}")
            
            try:
                # Check if we have a BASE_URL configured
                base_url = current_app.config.get('BASE_URL')
                
                if not base_url:
                    # Default to localhost if BASE_URL is not configured
                    base_url = "http://localhost:5000"
                    logger.warning(f"BASE_URL not configured, using default: {base_url}")
                
                # Call the sync_emails endpoint
                response = requests.post(
                    f"{base_url}/api/gmail/sync-emails",
                    headers={'Authorization': f'Bearer {tokens["access_token"]}'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully synced {result.get('synced_count', 0)} emails for user {user_id}")
                else:
                    logger.error(f"Failed to sync emails for user {user_id}: {response.text}")
            except Exception as e:
                logger.error(f"Error syncing emails for user {user_id}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in Gmail email sync job: {str(e)}")
    
    logger.info("Completed Gmail email synchronization job")

def start_background_jobs(app=None):
    """
    Start all background jobs
    
    Args:
        app: Flask application instance
    """
    logger.info("Starting background jobs")
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Create wrapper functions that run in the app context
    def run_sync_calendar_tasks():
        with app.app_context():
            sync_calendar_tasks()
    
    def run_sync_gmail_emails():
        with app.app_context():
            sync_gmail_emails()
    
    # Add calendar sync job - run every 30 minutes
    scheduler.add_job(
        func=run_sync_calendar_tasks,
        trigger=IntervalTrigger(minutes=30),
        id='sync_calendar_tasks',
        name='Sync Google Calendar with Tasks',
        replace_existing=True
    )
    
    # Add Gmail sync job - run every 15 minutes
    scheduler.add_job(
        func=run_sync_gmail_emails,
        trigger=IntervalTrigger(minutes=15),
        id='sync_gmail_emails',
        name='Sync Gmail with Communications',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    
    logger.info("Background jobs started") 