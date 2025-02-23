"""Initial migration

Revision ID: e50efb40f8ac
Revises: 
Create Date: 2025-02-21 13:49:16.995008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e50efb40f8ac'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('people',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String()),
        sa.Column('phone', sa.String()),
        sa.Column('address', sa.String()),
        sa.Column('role', sa.String()),
        sa.Column('church_id', sa.Integer()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('churches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('location', sa.String()),
        sa.Column('phone', sa.String()),
        sa.Column('email', sa.String()),
        sa.Column('main_contact_id', sa.Integer()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['main_contact_id'], ['people.id'])
    )

    # Add foreign key for church_id in people table
    op.create_foreign_key(
        'fk_people_church_id', 'people', 'churches',
        ['church_id'], ['id']
    )

    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('due_date', sa.Date()),
        sa.Column('priority', sa.String()),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('person_id', sa.Integer()),
        sa.Column('church_id', sa.Integer()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['person_id'], ['people.id']),
        sa.ForeignKeyConstraint(['church_id'], ['churches.id'])
    )

    op.create_table('communications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('comm_type', sa.String(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('date_sent', sa.Date(), nullable=False),
        sa.Column('person_id', sa.Integer()),
        sa.Column('church_id', sa.Integer()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['person_id'], ['people.id']),
        sa.ForeignKeyConstraint(['church_id'], ['churches.id'])
    )


def downgrade() -> None:
    op.drop_table('communications')
    op.drop_table('tasks')
    op.drop_foreign_key('fk_people_church_id', 'people')
    op.drop_table('churches')
    op.drop_table('people')
