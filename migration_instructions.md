# Database Migration Instructions

This guide will help you migrate your data from your existing Render PostgreSQL database to your new database on Google Cloud Run.

## Prerequisites

1. Access to your Render PostgreSQL database credentials
2. Access to your new database credentials (Google Cloud SQL or other)
3. Python 3.6+ installed on your machine

## Setup

1. Make sure you have the required Python packages installed:

```bash
pip install sqlalchemy psycopg2-binary python-dotenv tabulate
```

2. Set up your environment variables in a `.env` file:

```
# Source database (Render PostgreSQL)
SOURCE_DB_CONNECTION_STRING=postgresql://username:password@host:port/database
# OR individual variables
SOURCE_DB_USER=username
SOURCE_DB_PASS=password
SOURCE_DB_HOST=host
SOURCE_DB_PORT=port
SOURCE_DB_NAME=database

# Target database (Google Cloud SQL or other)
DB_CONNECTION_STRING=postgresql://username:password@host:port/database
# OR individual variables
DB_USER=username
DB_PASS=password
DB_HOST=host
DB_PORT=port
DB_NAME=database
```

## Finding Your Render PostgreSQL Credentials

1. Log in to your Render dashboard
2. Navigate to your PostgreSQL database
3. Click on "Connect" to view the connection details
4. Use these details to set up your source database environment variables

## Migration Process

### Option 1: Automated Migration (Recommended)

For a streamlined migration process, use the provided shell script:

```bash
./run_migration.sh
```

This script will:
1. Check for required dependencies
2. Run the data migration
3. Reset PostgreSQL sequences
4. Verify the migration was successful
5. Provide a summary of the results

You can also pass options to the script:

```bash
# Migrate only specific tables
./run_migration.sh --tables="contacts,people,churches,tasks,communications"

# Specify source database connection string directly
./run_migration.sh --source="postgresql://username:password@host:port/database"

# Clear target tables before migration
./run_migration.sh --clear-target-tables
```

### Option 2: Step-by-Step Migration

If you prefer to run each step manually, follow these instructions:

#### Step 1: Run the Migration Script

```bash
python migrate_from_render.py
```

The script will:
- Connect to both databases
- List all tables in both databases
- Migrate data from matching tables
- Report on the migration progress

#### Step 2: Reset PostgreSQL Sequences

After migrating data, you need to reset the PostgreSQL sequences for auto-incrementing IDs:

```bash
python reset_sequences.py
```

This ensures that new records will use the correct ID values and won't conflict with existing data.

#### Step 3: Verify the Migration

To verify that the migration was successful, run the verification script:

```bash
python verify_migration.py
```

This script will:
- Connect to both databases
- Compare record counts for each table
- Generate a report showing which tables match and which don't
- Provide a summary of the verification results

## Advanced Options

### Migration Script Options

```bash
# Specify source database connection string directly
python migrate_from_render.py --source "postgresql://username:password@host:port/database"

# Migrate only specific tables
python migrate_from_render.py --tables "contacts,people,churches,tasks,communications"

# Clear target tables before migration (WARNING: This will delete existing data!)
python migrate_from_render.py --clear-target-tables
```

### Sequence Reset Options

```bash
# Specify database connection string directly
python reset_sequences.py --connection "postgresql://username:password@host:port/database"

# Reset sequences for specific tables only
python reset_sequences.py --tables "contacts,people,churches,tasks,communications"
```

### Verification Options

```bash
# Specify source database connection string directly
python verify_migration.py --source "postgresql://username:password@host:port/database"

# Verify only specific tables
python verify_migration.py --tables "contacts,people,churches,tasks,communications"
```

## Troubleshooting

### Connection Issues

If you encounter connection issues:

1. Verify your database credentials are correct
2. Check if your IP address is allowed in the database firewall rules
3. For Render PostgreSQL, ensure your database is not in a suspended state
4. For Google Cloud SQL, check that the instance is running and accessible

### Schema Differences

If you encounter schema differences:

1. Make sure you've run all migrations on your new database
2. Check for any column type differences between the databases
3. You may need to modify the migration script to handle specific data transformations

### Sequence Issues

If you encounter issues with auto-incrementing IDs after migration:

1. Make sure you've run the `reset_sequences.py` script
2. Check if the sequence names match the expected format (`table_name_id_seq`)
3. You may need to manually adjust sequences for tables with custom sequence names

### Verification Failures

If the verification script reports mismatches:

1. Check if there are any constraints in the target database that might be preventing some records from being inserted
2. Look for any error messages during the migration process
3. Consider running the migration again with the `--clear-target-tables` option
4. For specific tables with mismatches, you can try migrating just those tables

## Post-Migration Steps

After migrating your data:

1. Verify the data in your new database
2. Update your application's environment variables to point to the new database
3. Test your application thoroughly with the migrated data
4. Once confirmed working, you can decommission your old Render database

## Need Help?

If you encounter any issues during migration, check the error messages for specific details about what went wrong. Common issues include:

- Connection problems (wrong credentials, network issues)
- Schema differences between databases
- Data type incompatibilities
- Foreign key constraint violations

For complex migrations with custom requirements, you may need to modify the migration script to handle specific transformations or relationships between tables. 