"""Create initial schema with servers, ping_results, and daily_availability tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-31 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create servers table
    op.create_table(
        'servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('group_name', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('ping_interval', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ping_results table with sequence for id
    op.execute("CREATE SEQUENCE ping_results_id_seq AS BIGINT START 1")
    op.create_table(
        'ping_results',
        sa.Column('id', sa.BigInteger(), nullable=False, server_default=sa.text("nextval('ping_results_id_seq')")),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_up', sa.Boolean(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ping_results_server_timestamp', 'ping_results', ['server_id', 'timestamp'])

    # Create daily_availability table with sequence for id
    op.execute("CREATE SEQUENCE daily_availability_id_seq AS BIGINT START 1")
    op.create_table(
        'daily_availability',
        sa.Column('id', sa.BigInteger(), nullable=False, server_default=sa.text("nextval('daily_availability_id_seq')")),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_pings', sa.Integer(), nullable=False),
        sa.Column('success_pings', sa.Integer(), nullable=False),
        sa.Column('availability_pct', sa.Float(), nullable=False),
        sa.Column('avg_latency', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_availability_server_date', 'daily_availability', ['server_id', 'date'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_daily_availability_server_date', table_name='daily_availability')
    op.drop_table('daily_availability')
    op.drop_index('ix_ping_results_server_timestamp', table_name='ping_results')
    op.drop_table('ping_results')
    op.execute("DROP SEQUENCE IF EXISTS ping_results_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS daily_availability_id_seq")
    op.drop_table('servers')
