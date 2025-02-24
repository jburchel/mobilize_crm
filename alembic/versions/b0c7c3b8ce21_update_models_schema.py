"""update_models_schema

Revision ID: b0c7c3b8ce21
Revises: c68b183aa062
Create Date: 2025-02-24 12:41:48.158909

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic.operations import ops

# revision identifiers, used by Alembic.
revision: str = 'b0c7c3b8ce21'
down_revision: Union[str, None] = 'c68b183aa062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('churches') as batch_op:
        batch_op.drop_column('name')
        batch_op.drop_column('email')
        batch_op.drop_column('phone')
        batch_op.create_foreign_key('fk_churches_contacts', 'contacts', ['id'], ['id'])

    with op.batch_alter_table('contacts') as batch_op:
        batch_op.add_column(sa.Column('church_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('first_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('last_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('image', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('preferred_contact_method', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('initial_notes', sa.Text(), nullable=True))
        batch_op.drop_column('name')
        batch_op.drop_column('notes')

    with op.batch_alter_table('people') as batch_op:
        batch_op.add_column(sa.Column('spouse_first_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('spouse_last_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('virtuous', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('title', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('home_country', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('marital_status', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('people_pipeline', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('priority', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('assigned_to', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('referred_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('info_given', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('desired_service', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('reason_closed', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('date_closed', sa.Date(), nullable=True))
        batch_op.create_foreign_key('fk_people_contacts', 'contacts', ['id'], ['id'])
        batch_op.drop_column('name')
        batch_op.drop_column('email')
        batch_op.drop_column('phone')
        batch_op.drop_column('address')
        batch_op.drop_column('google_resource_name')


def downgrade() -> None:
    # Use batch operations for SQLite compatibility
    with op.batch_alter_table('people') as batch_op:
        batch_op.add_column(sa.Column('google_resource_name', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('address', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('phone', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('email', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('name', sa.VARCHAR(), nullable=True))
        batch_op.drop_constraint('fk_people_contacts', type_='foreignkey')
        batch_op.drop_column('date_closed')
        batch_op.drop_column('reason_closed')
        batch_op.drop_column('desired_service')
        batch_op.drop_column('info_given')
        batch_op.drop_column('referred_by')
        batch_op.drop_column('source')
        batch_op.drop_column('assigned_to')
        batch_op.drop_column('priority')
        batch_op.drop_column('people_pipeline')
        batch_op.drop_column('marital_status')
        batch_op.drop_column('home_country')
        batch_op.drop_column('title')
        batch_op.drop_column('virtuous')
        batch_op.drop_column('spouse_last_name')
        batch_op.drop_column('spouse_first_name')

    with op.batch_alter_table('contacts') as batch_op:
        batch_op.add_column(sa.Column('notes', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('name', sa.VARCHAR(length=100), nullable=False))
        batch_op.drop_column('initial_notes')
        batch_op.drop_column('preferred_contact_method')
        batch_op.drop_column('image')
        batch_op.drop_column('last_name')
        batch_op.drop_column('first_name')
        batch_op.drop_column('church_name')

    with op.batch_alter_table('churches') as batch_op:
        batch_op.add_column(sa.Column('phone', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('email', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('name', sa.VARCHAR(), nullable=True))
        batch_op.drop_constraint('fk_churches_contacts', type_='foreignkey')
