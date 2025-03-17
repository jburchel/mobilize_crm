"""
Background jobs for Mobilize CRM
This module provides functions for running background tasks
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from models import Task
from database import db, session_scope
from utils.google_calendar import build_calendar_service, update_event_from_task, create_event_from_task
from routes.google_auth import get_user_tokens, get_all_user_tokens
import logging
from datetime import datetime, timedelta
import atexit
from flask import current_app
import requests
import threading
import time
import traceback

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

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
    logger.info("This job will sync both emails received FROM contacts and emails sent TO contacts in the CRM")
    
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
                
            user_email = tokens.get('user_email')
            logger.info(f"Syncing emails for user {user_id} with email {user_email}")
            
            try:
                # Check if we have a BASE_URL configured
                base_url = current_app.config.get('BASE_URL')
                
                if not base_url:
                    # Default to localhost if BASE_URL is not configured
                    base_url = "http://localhost:8000"
                    logger.warning(f"BASE_URL not configured, using default: {base_url}")
                
                # Call the sync_emails endpoint
                response = requests.post(
                    f"{base_url}/api/gmail/sync-emails",
                    headers={
                        # Use X-Google-Token header which is explicitly allowed in auth_required
                        'X-Google-Token': tokens["access_token"],
                        # Pass the user ID in the custom header
                        'X-User-ID': user_id,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'user_id': user_id,  # Also include in the request body for redundancy
                        'user_email': user_email  # Include the user's email
                    }
                )
                
                logger.info(f"Sync result: {response}")
                
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

def is_job_running(job_id):
    """
    Check if a specific background job is currently running
    
    Args:
        job_id: ID of the job to check
        
    Returns:
        bool: True if the job is running, False otherwise
    """
    global scheduler
    
    if not scheduler:
        return False
        
    try:
        job = scheduler.get_job(job_id)
        if not job:
            return False
            
        # Check if the job is currently executing
        # This is a bit of a hack since APScheduler doesn't provide a direct way to check
        # We'll consider the job running if it's 5 minutes from the last execution
        now = datetime.now(job.next_run_time.tzinfo)  # Use the same timezone as next_run_time
        if job.next_run_time and job.next_run_time > now:
            # The job is scheduled to run in the future
            # Get the interval in seconds and convert to minutes
            interval_seconds = job.trigger.interval.total_seconds()
            interval_minutes = interval_seconds / 60
            last_run = job.next_run_time - timedelta(seconds=interval_minutes * 60)
            # If it was supposed to run within the last 5 minutes, consider it running
            return (now - last_run).total_seconds() < 300  # 5 minutes in seconds
            
        return False
    except Exception as e:
        logger.error(f"Error checking if job {job_id} is running: {str(e)}")
        return False

def start_background_jobs(app=None):
    """
    Start all background jobs
    
    Args:
        app: Flask application instance
    """
    logger.info("Starting background jobs")
    
    # Create scheduler
    global scheduler
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