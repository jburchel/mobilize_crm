#!/bin/bash

# Setup script for database backup cron job
# This script helps set up a cron job to run the backup_database.py script

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_database.py"
PYTHON_ENV="$PROJECT_DIR/venv/bin/python"

# Check if the backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "Error: Backup script not found at $BACKUP_SCRIPT"
    exit 1
fi

# Check if the Python environment exists
if [ ! -f "$PYTHON_ENV" ]; then
    echo "Warning: Python virtual environment not found at $PYTHON_ENV"
    echo "Using system Python instead"
    PYTHON_ENV="python"
fi

# Create the cron job command
CRON_CMD="0 0 * * * cd $PROJECT_DIR && $PYTHON_ENV $BACKUP_SCRIPT --backup-dir $PROJECT_DIR/backups >> $PROJECT_DIR/cron_backup.log 2>&1"

# Display instructions
echo "===== Database Backup Cron Setup ====="
echo ""
echo "To set up automatic daily backups at midnight, run:"
echo ""
echo "  (crontab -l 2>/dev/null; echo \"$CRON_CMD\") | crontab -"
echo ""
echo "To set up automatic backups at a different time, edit the cron schedule."
echo "Current cron schedule: 0 0 * * * (midnight every day)"
echo ""
echo "To manually run a backup now, run:"
echo ""
echo "  $PYTHON_ENV $BACKUP_SCRIPT"
echo ""
echo "To only sync the databases without creating a backup, run:"
echo ""
echo "  $PYTHON_ENV $BACKUP_SCRIPT --sync-only"
echo ""
echo "====================================="

# Ask if the user wants to set up the cron job now
read -p "Would you like to set up the cron job now? (y/n): " SETUP_NOW

if [[ "$SETUP_NOW" =~ ^[Yy]$ ]]; then
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "Cron job has been set up successfully!"
    echo "Backups will run daily at midnight."
else
    echo "No changes made to crontab."
    echo "You can set up the cron job manually using the command above."
fi

# Create the backup directory if it doesn't exist
BACKUP_DIR="$PROJECT_DIR/backups"
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    echo "Created backup directory: $BACKUP_DIR"
fi

echo "Setup complete!" 