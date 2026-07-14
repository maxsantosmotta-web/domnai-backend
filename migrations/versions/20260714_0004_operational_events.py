"""Add operational error events.

Revision ID: 20260714_0004
Revises: 20260714_0003
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260714_0004"
down_revision = "20260714_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=12), nullable=False),
        sa.Column("occurrences", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index("ix_operational_events_fingerprint", "operational_events", ["fingerprint"], unique=True)
    op.create_index("ix_operational_events_module", "operational_events", ["module"], unique=False)
    op.create_index("ix_operational_events_severity", "operational_events", ["severity"], unique=False)
    op.create_index("ix_operational_events_last_seen_at", "operational_events", ["last_seen_at"], unique=False)
    op.create_index("ix_operational_events_resolved_at", "operational_events", ["resolved_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operational_events_resolved_at", table_name="operational_events")
    op.drop_index("ix_operational_events_last_seen_at", table_name="operational_events")
    op.drop_index("ix_operational_events_severity", table_name="operational_events")
    op.drop_index("ix_operational_events_module", table_name="operational_events")
    op.drop_index("ix_operational_events_fingerprint", table_name="operational_events")
    op.drop_table("operational_events")
