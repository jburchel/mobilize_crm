# Mobilize CRM Scripts

This directory contains utility scripts for the Mobilize CRM application.

## Database Synchronization Scripts

### `direct_sync.py`

Synchronizes data from PostgreSQL to SQLite database.

```bash
python scripts/direct_sync.py
```

This script:
- Connects to both PostgreSQL and SQLite databases
- Transfers data from PostgreSQL to SQLite for the following tables:
  - people
  - churches
  - contacts
  - communications
  - tasks
  - offices
  - user_offices
  - users (if available)

### `migrate_pg_to_sqlite.py`

Original migration script to transfer schema and data from PostgreSQL to SQLite.

### `sync_to_sqlite.py`

Original synchronization script using SQLAlchemy models.

## Database Backup Scripts

### `backup_database.py`

Creates timestamped backups of the SQLite database and manages backup retention.

```bash
# Create a backup with default settings
python scripts/backup_database.py

# Only sync databases without creating a backup
python scripts/backup_database.py --sync-only

# Specify custom backup directory and retention period
python scripts/backup_database.py --backup-dir /path/to/backups --keep-days 60
```

Options:
- `--source`: Source database path (default: instance/mobilize_crm.db)
- `--backup-dir`: Backup directory (default: backups)
- `--keep-days`: Days to keep backups (default: 30)
- `--sync-only`: Only sync databases without creating backup

### `setup_backup_cron.sh`

Helper script to set up automated backups using cron.

```bash
./scripts/setup_backup_cron.sh
```

This script:
- Helps set up a cron job to run daily backups
- Creates the backup directory if it doesn't exist
- Provides instructions for manual setup

## Utility Scripts

### `check_data_retrieval.py`

Checks if the application is correctly retrieving and displaying data.

```bash
# Check with default settings
python scripts/check_data_retrieval.py

# Specify custom base URL
python scripts/check_data_retrieval.py --base-url http://example.com
```

Options:
- `--base-url`: Base URL of the application (default: http://127.0.0.1:8000)
- `--timeout`: Request timeout in seconds (default: 5)
- `--retries`: Number of retry attempts (default: 3)

### `check_users_table.py`

Utility script to check the schema and content of the users table in PostgreSQL.

## Best Practices

1. Always create a backup before making significant changes to the database
2. Test synchronization on a development environment before applying to production
3. Set up automated backups using the provided scripts
4. Regularly check data retrieval to ensure the application is functioning correctly 