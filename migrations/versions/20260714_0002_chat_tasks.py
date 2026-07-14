"""Persistent chat tasks.

Revision ID: 20260714_0003
Revises: 20260714_0002
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260714_0003"
down_revision = "20260714_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued", index=True),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("credit_transaction_key", sa.String(length=255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_chat_tasks_user_created", "chat_tasks", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_tasks_user_created", table_name="chat_tasks")
    op.drop_table("chat_tasks")
