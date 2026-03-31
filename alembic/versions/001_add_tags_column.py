"""Add tags column to servers table

Revision ID: 001
Revises: 
Create Date: 2026-03-31 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('servers', sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.alter_column('servers', 'tags', server_default=None)


def downgrade() -> None:
    op.drop_column('servers', 'tags')
