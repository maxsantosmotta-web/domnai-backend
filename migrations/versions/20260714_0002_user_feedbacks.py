"""Create persistent user feedbacks.

Revision ID: 20260714_0002
Revises: 20260713_0001
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260714_0002"
down_revision = "20260713_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_feedbacks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="received"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "category IN ('suggestion', 'problem', 'praise')",
            name="ck_user_feedbacks_category",
        ),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_user_feedbacks_rating",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_feedbacks_user_id", "user_feedbacks", ["user_id"], unique=False)
    op.create_index("ix_user_feedbacks_category", "user_feedbacks", ["category"], unique=False)
    op.create_index("ix_user_feedbacks_status", "user_feedbacks", ["status"], unique=False)
    op.create_index("ix_user_feedbacks_created_at", "user_feedbacks", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_feedbacks_created_at", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_status", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_category", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_user_id", table_name="user_feedbacks")
    op.drop_table("user_feedbacks")
