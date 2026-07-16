"""Merge the audit and persistent chat migration branches.

Revision ID: 20260716_0006
Revises: 20260714_chat_tasks, 20260714_0005
Create Date: 2026-07-16
"""

revision = "20260716_0006"
down_revision = ("20260714_chat_tasks", "20260714_0005")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join both existing branches without changing the database schema."""


def downgrade() -> None:
    """Split the revision graph back into the two previous heads."""
