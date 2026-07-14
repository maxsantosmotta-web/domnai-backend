"""Add administrative hiding to feedbacks.

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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_feedbacks")}
    if "admin_hidden_at" not in columns:
        op.add_column(
            "user_feedbacks",
            sa.Column("admin_hidden_at", sa.DateTime(timezone=True), nullable=True),
        )

    indexes = {index["name"] for index in inspector.get_indexes("user_feedbacks")}
    if "ix_user_feedbacks_admin_hidden_at" not in indexes:
        op.create_index(
            "ix_user_feedbacks_admin_hidden_at",
            "user_feedbacks",
            ["admin_hidden_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("user_feedbacks")}
    if "ix_user_feedbacks_admin_hidden_at" in indexes:
        op.drop_index("ix_user_feedbacks_admin_hidden_at", table_name="user_feedbacks")

    columns = {column["name"] for column in inspector.get_columns("user_feedbacks")}
    if "admin_hidden_at" in columns:
        op.drop_column("user_feedbacks", "admin_hidden_at")
