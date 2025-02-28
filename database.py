from flask_sqlalchemy import SQLAlchemy
from contextlib import contextmanager

# Create the SQLAlchemy object
db = SQLAlchemy()

def init_db(app):
    """Initialize the database with the app"""
    db.init_app(app) 

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = db.session
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close() 