"""
Migration script to add admin features to the database schema.
This includes:
1. Creating a permissions table
2. Creating an offices table
3. Adding office_id field to churches table
4. Creating user_offices table for user-office associations
"""

from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker
from models import Base, Permission, Office, UserOffice, Church
import os

def check_column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table."""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def upgrade():
    """
    Upgrade the database schema to include admin features.
    """
    # Get database URI from environment or use default
    database_uri = os.environ.get('DATABASE_URL', 'sqlite:///instance/mobilize_crm.db')
    
    # Create engine and session
    engine = create_engine(database_uri)
    Session = sessionmaker(bind=engine)
    
    # Create tables
    Base.metadata.create_all(engine, tables=[
        Permission.__table__,
        Office.__table__,
        UserOffice.__table__
    ])
    
    # Create default permissions
    with Session() as session:
        # Create default permissions if they don't exist
        default_permissions = [
            {"name": "view_churches", "description": "Can view churches"},
            {"name": "add_church", "description": "Can add new churches"},
            {"name": "edit_church", "description": "Can edit existing churches"},
            {"name": "delete_church", "description": "Can delete churches"},
            {"name": "view_people", "description": "Can view people"},
            {"name": "add_person", "description": "Can add new people"},
            {"name": "edit_person", "description": "Can edit existing people"},
            {"name": "delete_person", "description": "Can delete people"},
            {"name": "view_communications", "description": "Can view communications"},
            {"name": "add_communication", "description": "Can add new communications"},
            {"name": "edit_communication", "description": "Can edit existing communications"},
            {"name": "delete_communication", "description": "Can delete communications"},
            {"name": "view_tasks", "description": "Can view tasks"},
            {"name": "add_task", "description": "Can add new tasks"},
            {"name": "edit_task", "description": "Can edit existing tasks"},
            {"name": "delete_task", "description": "Can delete tasks"},
            {"name": "manage_users", "description": "Can manage users"},
            {"name": "manage_offices", "description": "Can manage offices"},
            {"name": "manage_permissions", "description": "Can manage permissions"},
        ]
        
        for perm in default_permissions:
            # Check if permission already exists
            existing = session.query(Permission).filter_by(name=perm["name"]).first()
            if not existing:
                session.add(Permission(name=perm["name"], description=perm["description"]))
        
        # Create default office
        default_office = session.query(Office).filter_by(name="Main Office").first()
        if not default_office:
            default_office = Office(name="Main Office")
            session.add(default_office)
            session.flush()  # Flush to get the ID
        
        # Commit changes
        session.commit()
        
        # Now let's manually add the office_id column to the churches table
        # This is a workaround for SQLite's limitations
        inspector = inspect(engine)
        if not check_column_exists(inspector, 'churches', 'office_id'):
            # For SQLite, we need to create a new table with the additional column
            # and copy the data over
            if database_uri.startswith('sqlite'):
                # Create a backup of the churches table
                with engine.connect() as conn:
                    conn.execute(text("CREATE TABLE churches_backup AS SELECT * FROM churches"))
                    conn.commit()
                
                # Drop the churches table and recreate it with the office_id column
                # We'll use the Church model which now has the office_id column
                Base.metadata.drop_all(engine, tables=[Church.__table__])
                Base.metadata.create_all(engine, tables=[Church.__table__])
                
                # Copy the data back from the backup table
                with engine.connect() as conn:
                    conn.execute(text("""
                    INSERT INTO churches (
                        id, location, main_contact_id, virtuous, 
                        senior_pastor_first_name, senior_pastor_last_name, 
                        senior_pastor_phone, senior_pastor_email, 
                        missions_pastor_first_name, missions_pastor_last_name, 
                        mission_pastor_phone, mission_pastor_email, 
                        primary_contact_first_name, primary_contact_last_name, 
                        primary_contact_phone, primary_contact_email, 
                        website, denomination, congregation_size, 
                        church_pipeline, priority, assigned_to, 
                        source, referred_by, info_given, 
                        reason_closed, year_founded, date_closed
                    )
                    SELECT 
                        id, location, main_contact_id, virtuous, 
                        senior_pastor_first_name, senior_pastor_last_name, 
                        senior_pastor_phone, senior_pastor_email, 
                        missions_pastor_first_name, missions_pastor_last_name, 
                        mission_pastor_phone, mission_pastor_email, 
                        primary_contact_first_name, primary_contact_last_name, 
                        primary_contact_phone, primary_contact_email, 
                        website, denomination, congregation_size, 
                        church_pipeline, priority, assigned_to, 
                        source, referred_by, info_given, 
                        reason_closed, year_founded, date_closed
                    FROM churches_backup
                    """))
                    conn.commit()
                
                # Drop the backup table
                with engine.connect() as conn:
                    conn.execute(text("DROP TABLE churches_backup"))
                    conn.commit()
            else:
                # For PostgreSQL, we can use ALTER TABLE
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE churches ADD COLUMN office_id INTEGER REFERENCES offices(id)"))
                    conn.commit()
        
        # Associate all existing churches with the default office
        churches = session.query(Church).all()
        for church in churches:
            if church.office_id is None:
                church.office_id = default_office.id
        
        # Commit changes
        session.commit()

def downgrade():
    """
    Downgrade the database schema by removing admin features.
    """
    # Get database URI from environment or use default
    database_uri = os.environ.get('DATABASE_URL', 'sqlite:///instance/mobilize_crm.db')
    
    # Create engine
    engine = create_engine(database_uri)
    
    # Remove office_id column from churches table
    inspector = inspect(engine)
    if check_column_exists(inspector, 'churches', 'office_id'):
        with engine.connect() as conn:
            if database_uri.startswith('sqlite'):
                # SQLite doesn't support DROP COLUMN, so we'll just set values to NULL
                conn.execute(text("UPDATE churches SET office_id = NULL"))
            else:
                conn.execute(text("ALTER TABLE churches DROP COLUMN office_id"))
            conn.commit()
    
    # Drop tables in reverse order
    Base.metadata.drop_all(engine, tables=[
        UserOffice.__table__,
        Office.__table__,
        Permission.__table__
    ]) 