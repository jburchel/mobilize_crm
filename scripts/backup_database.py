#!/usr/bin/env python
import os
import shutil
import datetime
import time
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_backup.log')
    ]
)
logger = logging.getLogger(__name__)

def backup_database(source_db_path, backup_dir, keep_days=30):
    """
    Create a backup of the SQLite database with timestamp
    
    Args:
        source_db_path: Path to the source database file
        backup_dir: Directory to store backups
        keep_days: Number of days to keep backups (default: 30)
    """
    try:
        # Create backup directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            logger.info(f"Created backup directory: {backup_dir}")
        
        # Generate timestamp for the backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"mobilize_crm_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(source_db_path, backup_path)
        logger.info(f"Database backup created: {backup_path}")
        
        # Clean up old backups
        cleanup_old_backups(backup_dir, keep_days)
        
        return True, backup_path
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False, str(e)

def cleanup_old_backups(backup_dir, keep_days):
    """
    Remove backup files older than keep_days
    
    Args:
        backup_dir: Directory containing backups
        keep_days: Number of days to keep backups
    """
    try:
        # Calculate the cutoff date
        cutoff_date = time.time() - (keep_days * 86400)  # 86400 seconds in a day
        
        # Get all backup files
        backup_files = [f for f in os.listdir(backup_dir) 
                        if f.startswith("mobilize_crm_backup_") and f.endswith(".db")]
        
        # Check each file's age
        for filename in backup_files:
            file_path = os.path.join(backup_dir, filename)
            file_mod_time = os.path.getmtime(file_path)
            
            # Remove if older than cutoff date
            if file_mod_time < cutoff_date:
                os.remove(file_path)
                logger.info(f"Removed old backup: {filename}")
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")

def sync_databases():
    """
    Sync the root database with the instance database
    """
    try:
        root_db = "mobilize_crm.db"
        instance_db = "instance/mobilize_crm.db"
        
        # Check if both files exist
        if os.path.exists(root_db) and os.path.exists(instance_db):
            # Get modification times
            root_mtime = os.path.getmtime(root_db)
            instance_mtime = os.path.getmtime(instance_db)
            
            # Determine which is newer
            if root_mtime > instance_mtime:
                logger.info("Root database is newer, copying to instance")
                shutil.copy2(root_db, instance_db)
            elif instance_mtime > root_mtime:
                logger.info("Instance database is newer, copying to root")
                shutil.copy2(instance_db, root_db)
            else:
                logger.info("Databases have the same modification time, no sync needed")
        else:
            if os.path.exists(root_db):
                # Create instance directory if it doesn't exist
                os.makedirs(os.path.dirname(instance_db), exist_ok=True)
                logger.info("Root database exists but instance doesn't, copying to instance")
                shutil.copy2(root_db, instance_db)
            elif os.path.exists(instance_db):
                logger.info("Instance database exists but root doesn't, copying to root")
                shutil.copy2(instance_db, root_db)
            else:
                logger.error("Neither database file exists!")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Database Backup Tool")
    parser.add_argument("--source", default="instance/mobilize_crm.db", 
                        help="Source database path (default: instance/mobilize_crm.db)")
    parser.add_argument("--backup-dir", default="backups", 
                        help="Backup directory (default: backups)")
    parser.add_argument("--keep-days", type=int, default=30, 
                        help="Days to keep backups (default: 30)")
    parser.add_argument("--sync-only", action="store_true", 
                        help="Only sync databases without creating backup")
    
    args = parser.parse_args()
    
    # Resolve relative paths
    source_path = Path(args.source).resolve()
    backup_dir = Path(args.backup_dir).resolve()
    
    if args.sync_only:
        logger.info("Syncing databases...")
        if sync_databases():
            logger.info("Database sync completed successfully")
        else:
            logger.error("Database sync failed")
    else:
        # First sync the databases
        logger.info("Syncing databases before backup...")
        if sync_databases():
            logger.info("Database sync completed successfully")
            
            # Then create backup
            logger.info(f"Creating backup of {source_path} in {backup_dir}...")
            success, result = backup_database(source_path, backup_dir, args.keep_days)
            
            if success:
                logger.info(f"Backup completed successfully: {result}")
            else:
                logger.error(f"Backup failed: {result}")
        else:
            logger.error("Database sync failed, backup aborted") 