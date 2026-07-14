"""Add focused audit events.

Revision ID: 20260714_0005
Revises: 20260714_0004
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260714_0005"
down_revision = "20260714_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"], unique=False)
    op.create_index("ix_audit_events_category", "audit_events", ["category"], unique=False)
    op.create_index("ix_audit_events_module", "audit_events", ["module"], unique=False)
    op.create_index("ix_audit_events_action", "audit_events", ["action"], unique=False)
    op.create_index("ix_audit_events_result", "audit_events", ["result"], unique=False)
    op.create_index("ix_audit_events_source_key", "audit_events", ["source_key"], unique=True)
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_source_key", table_name="audit_events")
    op.drop_index("ix_audit_events_result", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_module", table_name="audit_events")
    op.drop_index("ix_audit_events_category", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_table("audit_events")
