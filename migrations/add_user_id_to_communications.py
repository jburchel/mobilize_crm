from sqlalchemy import Column, String
from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    """Add user_id column to communications table."""
    op.add_column('communications', Column('user_id', String(128), nullable=True))
    
    # Optionally, you could populate the user_id field based on the person's user_id
    # This is a more complex operation that would require a data migration
    # connection = op.get_bind()
    # connection.execute("""
    #     UPDATE communications c
    #     SET user_id = (
    #         SELECT p.user_id 
    #         FROM people p 
    #         WHERE p.id = c.person_id
    #     )
    #     WHERE c.person_id IS NOT NULL
    # """)

def downgrade():
    """Remove user_id column from communications table."""
    op.drop_column('communications', 'user_id') 