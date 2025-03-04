# Updating Your .env File for Database Migration

To migrate data from your Render PostgreSQL database to your new database, you need to add the following environment variables to your existing `.env` file. We'll use direct connection strings for simplicity.

## Source Database (Render PostgreSQL) Connection String

Add this variable to your `.env` file to connect to your Render PostgreSQL database:

```
# Source Database (Render PostgreSQL) - For Migration
SOURCE_DB_CONNECTION_STRING=postgresql://postgres:your_render_password@your-render-db-host.render.com:5432/your_render_db_name
```

## Finding Your Render PostgreSQL Connection String

1. Log in to your Render dashboard
2. Navigate to your PostgreSQL database
3. Click on "Connect" to view the connection details
4. Look for the "External Connection String" or "PSQL Command"
5. The connection string format should be: `postgresql://username:password@host:port/database_name`

## Target Database Connection String

Make sure your target database connection string is correctly set:

```
# Database (Production - Google Cloud SQL or other)
DB_CONNECTION_STRING=postgresql://postgres:your_db_password@your-db-host:5432/postgres
```

If you're using Google Cloud SQL with Cloud Run, your connection string might look like:
```
DB_CONNECTION_STRING=postgresql://postgres:your_password@10.123.456.789:5432/postgres
```

## Example of a Complete Migration Section

Here's an example of what the database section in your `.env` file might look like after adding these variables:

```
# Database (Development - SQLite)
# No need to change these for local development

# Database (Production)
DB_CONNECTION_STRING=postgresql://postgres:your_actual_password@10.123.456.789:5432/postgres

# Source Database (Render PostgreSQL) - For Migration
SOURCE_DB_CONNECTION_STRING=postgresql://postgres:your_render_password@mobilize-crm-db.render.com:5432/mobilize_crm_db
```

## Running the Migration

After updating your `.env` file with these connection strings, you can run the migration script:

```bash
./run_migration.sh
```

Or if you prefer to run the steps individually:

```bash
# Migrate the data
python migrate_from_render.py

# Reset sequences
python reset_sequences.py

# Verify the migration
python verify_migration.py
```

## Important Security Note

Remember that connection strings contain your database passwords. Make sure your `.env` file is:
- Not committed to version control
- Has restricted file permissions
- Is only accessible to authorized users 