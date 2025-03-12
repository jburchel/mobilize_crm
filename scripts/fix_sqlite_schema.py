import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SQLite database path
sqlite_db_path = 'mobilize_crm.db'

# Connect to SQLite database
try:
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_cursor = sqlite_conn.cursor()
    print(f"✅ Connected to SQLite database at {sqlite_db_path}")
except Exception as e:
    print(f"❌ Failed to connect to SQLite database: {e}")
    exit(1)

# Create a backup of the database
try:
    import shutil
    backup_path = f"{sqlite_db_path}.backup"
    shutil.copy2(sqlite_db_path, backup_path)
    print(f"✅ Created backup of database at {backup_path}")
except Exception as e:
    print(f"❌ Failed to create backup: {e}")
    exit(1)

# Check if the tables exist
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
contacts_exists = sqlite_cursor.fetchone() is not None

sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='people'")
people_exists = sqlite_cursor.fetchone() is not None

sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='churches'")
churches_exists = sqlite_cursor.fetchone() is not None

# Create a temporary table to hold contacts data
if contacts_exists:
    try:
        print("Creating temporary table for contacts data...")
        sqlite_cursor.execute("CREATE TABLE contacts_temp AS SELECT * FROM contacts")
        print("✅ Created temporary table for contacts data")
    except Exception as e:
        print(f"❌ Failed to create temporary table: {e}")
        exit(1)

# Create a temporary table to hold people data
if people_exists:
    try:
        print("Creating temporary table for people data...")
        sqlite_cursor.execute("CREATE TABLE people_temp AS SELECT * FROM people")
        print("✅ Created temporary table for people data")
    except Exception as e:
        print(f"❌ Failed to create temporary table: {e}")
        exit(1)

# Create a temporary table to hold churches data
if churches_exists:
    try:
        print("Creating temporary table for churches data...")
        sqlite_cursor.execute("CREATE TABLE churches_temp AS SELECT * FROM churches")
        print("✅ Created temporary table for churches data")
    except Exception as e:
        print(f"❌ Failed to create temporary table: {e}")
        exit(1)

# Drop the existing tables
if contacts_exists:
    try:
        print("Dropping contacts table...")
        sqlite_cursor.execute("DROP TABLE contacts")
        print("✅ Dropped contacts table")
    except Exception as e:
        print(f"❌ Failed to drop contacts table: {e}")
        exit(1)

if people_exists:
    try:
        print("Dropping people table...")
        sqlite_cursor.execute("DROP TABLE people")
        print("✅ Dropped people table")
    except Exception as e:
        print(f"❌ Failed to drop people table: {e}")
        exit(1)

if churches_exists:
    try:
        print("Dropping churches table...")
        sqlite_cursor.execute("DROP TABLE churches")
        print("✅ Dropped churches table")
    except Exception as e:
        print(f"❌ Failed to drop churches table: {e}")
        exit(1)

# Create the tables with the correct schema
try:
    print("Creating contacts table with correct schema...")
    sqlite_cursor.execute('''
    CREATE TABLE contacts (
        id INTEGER PRIMARY KEY,
        church_name VARCHAR(100),
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        image VARCHAR,
        preferred_contact_method VARCHAR(100),
        phone VARCHAR(50),
        email VARCHAR,
        street_address VARCHAR(200),
        city VARCHAR(100),
        state VARCHAR(2),
        zip_code VARCHAR(10),
        initial_notes TEXT,
        date_created DATE,
        date_modified DATE,
        google_resource_name VARCHAR,
        type VARCHAR(50)
    )
    ''')
    print("✅ Created contacts table with correct schema")
except Exception as e:
    print(f"❌ Failed to create contacts table: {e}")
    exit(1)

try:
    print("Creating people table with correct schema...")
    sqlite_cursor.execute('''
    CREATE TABLE people (
        id INTEGER PRIMARY KEY,
        church_role VARCHAR,
        church_id INTEGER,
        spouse_first_name VARCHAR(100),
        spouse_last_name VARCHAR(100),
        virtuous BOOLEAN,
        title VARCHAR(100),
        home_country VARCHAR(100),
        marital_status VARCHAR(100),
        people_pipeline VARCHAR(100),
        priority VARCHAR(100),
        assigned_to VARCHAR(100),
        source VARCHAR(100),
        referred_by VARCHAR(100),
        info_given TEXT,
        desired_service TEXT,
        reason_closed TEXT,
        date_closed DATE,
        user_id VARCHAR(128),
        FOREIGN KEY (id) REFERENCES contacts(id) ON DELETE CASCADE,
        FOREIGN KEY (church_id) REFERENCES churches(id)
    )
    ''')
    print("✅ Created people table with correct schema")
except Exception as e:
    print(f"❌ Failed to create people table: {e}")
    exit(1)

try:
    print("Creating churches table with correct schema...")
    sqlite_cursor.execute('''
    CREATE TABLE churches (
        id INTEGER PRIMARY KEY,
        location VARCHAR,
        main_contact_id INTEGER,
        virtuous BOOLEAN,
        senior_pastor_first_name VARCHAR(100),
        senior_pastor_last_name VARCHAR(100),
        senior_pastor_phone VARCHAR(50),
        senior_pastor_email VARCHAR,
        missions_pastor_first_name VARCHAR(100),
        missions_pastor_last_name VARCHAR(100),
        mission_pastor_phone VARCHAR(50),
        mission_pastor_email VARCHAR,
        primary_contact_first_name VARCHAR(100),
        primary_contact_last_name VARCHAR(100),
        primary_contact_phone VARCHAR(50),
        primary_contact_email VARCHAR,
        website VARCHAR,
        denomination VARCHAR(100),
        congregation_size INTEGER,
        church_pipeline VARCHAR(100),
        priority VARCHAR(100),
        assigned_to VARCHAR(100),
        source VARCHAR(100),
        referred_by VARCHAR(100),
        info_given TEXT,
        reason_closed TEXT,
        year_founded INTEGER,
        date_closed DATE,
        office_id INTEGER,
        FOREIGN KEY (id) REFERENCES contacts(id) ON DELETE CASCADE,
        FOREIGN KEY (main_contact_id) REFERENCES people(id),
        FOREIGN KEY (office_id) REFERENCES offices(id)
    )
    ''')
    print("✅ Created churches table with correct schema")
except Exception as e:
    print(f"❌ Failed to create churches table: {e}")
    exit(1)

# Insert data from temporary tables
if contacts_exists:
    try:
        print("Inserting data into contacts table...")
        sqlite_cursor.execute('''
        INSERT INTO contacts (id, church_name, first_name, last_name, image, preferred_contact_method, 
                             phone, email, street_address, city, state, zip_code, initial_notes, 
                             date_created, date_modified, google_resource_name, type)
        SELECT id, church_name, first_name, last_name, image, preferred_contact_method, 
               phone, email, street_address, city, state, zip_code, initial_notes, 
               date_created, date_modified, google_resource_name, type
        FROM contacts_temp
        ''')
        print(f"✅ Inserted {sqlite_cursor.rowcount} records into contacts table")
    except Exception as e:
        print(f"❌ Failed to insert data into contacts table: {e}")
        exit(1)

if people_exists:
    try:
        print("Inserting data into people table...")
        sqlite_cursor.execute('''
        INSERT INTO people (id, church_role, church_id, spouse_first_name, spouse_last_name, 
                           virtuous, title, home_country, marital_status, people_pipeline, 
                           priority, assigned_to, source, referred_by, info_given, 
                           desired_service, reason_closed, date_closed, user_id)
        SELECT id, church_role, church_id, spouse_first_name, spouse_last_name, 
               virtuous, title, home_country, marital_status, people_pipeline, 
               priority, assigned_to, source, referred_by, info_given, 
               desired_service, reason_closed, date_closed, user_id
        FROM people_temp
        ''')
        print(f"✅ Inserted {sqlite_cursor.rowcount} records into people table")
    except Exception as e:
        print(f"❌ Failed to insert data into people table: {e}")
        exit(1)

if churches_exists:
    try:
        print("Inserting data into churches table...")
        sqlite_cursor.execute('''
        INSERT INTO churches (id, location, main_contact_id, virtuous, senior_pastor_first_name, 
                             senior_pastor_last_name, senior_pastor_phone, senior_pastor_email, 
                             missions_pastor_first_name, missions_pastor_last_name, mission_pastor_phone, 
                             mission_pastor_email, primary_contact_first_name, primary_contact_last_name, 
                             primary_contact_phone, primary_contact_email, website, denomination, 
                             congregation_size, church_pipeline, priority, assigned_to, source, 
                             referred_by, info_given, reason_closed, year_founded, date_closed, office_id)
        SELECT id, location, main_contact_id, virtuous, senior_pastor_first_name, 
               senior_pastor_last_name, senior_pastor_phone, senior_pastor_email, 
               missions_pastor_first_name, missions_pastor_last_name, mission_pastor_phone, 
               mission_pastor_email, primary_contact_first_name, primary_contact_last_name, 
               primary_contact_phone, primary_contact_email, website, denomination, 
               congregation_size, church_pipeline, priority, assigned_to, source, 
               referred_by, info_given, reason_closed, year_founded, date_closed, office_id
        FROM churches_temp
        ''')
        print(f"✅ Inserted {sqlite_cursor.rowcount} records into churches table")
    except Exception as e:
        print(f"❌ Failed to insert data into churches table: {e}")
        exit(1)

# Drop temporary tables
if contacts_exists:
    try:
        print("Dropping temporary contacts table...")
        sqlite_cursor.execute("DROP TABLE contacts_temp")
        print("✅ Dropped temporary contacts table")
    except Exception as e:
        print(f"❌ Failed to drop temporary contacts table: {e}")

if people_exists:
    try:
        print("Dropping temporary people table...")
        sqlite_cursor.execute("DROP TABLE people_temp")
        print("✅ Dropped temporary people table")
    except Exception as e:
        print(f"❌ Failed to drop temporary people table: {e}")

if churches_exists:
    try:
        print("Dropping temporary churches table...")
        sqlite_cursor.execute("DROP TABLE churches_temp")
        print("✅ Dropped temporary churches table")
    except Exception as e:
        print(f"❌ Failed to drop temporary churches table: {e}")

# Commit changes
sqlite_conn.commit()
print("✅ Committed changes to database")

# Close connection
sqlite_conn.close()
print("✅ Closed database connection")

print("\n✅ Schema fix complete. Please run the application again to see if the issue is resolved.") 