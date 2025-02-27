"""
Add Google Calendar fields to Task model
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add Google Calendar fields to tasks table
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_calendar_event_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('google_calendar_sync_enabled', sa.Boolean(), default=False, nullable=True))
        batch_op.add_column(sa.Column('last_synced_at', sa.DateTime(), nullable=True))
        # Create an index for faster lookups by event ID
        batch_op.create_index('ix_tasks_google_calendar_event_id', ['google_calendar_event_id'], unique=True)

def downgrade():
    # Remove Google Calendar fields from tasks table
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_index('ix_tasks_google_calendar_event_id')
        batch_op.drop_column('last_synced_at')
        batch_op.drop_column('google_calendar_sync_enabled')
        batch_op.drop_column('google_calendar_event_id')