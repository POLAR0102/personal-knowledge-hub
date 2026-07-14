"""add document tags and favorites

Revision ID: b8d4f2a6c703
Revises: a7c3e9f1b602
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d4f2a6c703"
down_revision: Union[str, None] = "a7c3e9f1b602"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "is_favorite",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_documents_is_favorite"),
        "documents",
        ["is_favorite"],
        unique=False,
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(name) BETWEEN 1 AND 30",
            name="ck_tags_name_length",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_id_name"),
    )
    op.create_index(
        op.f("ix_tags_user_id"),
        "tags",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "document_tags",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("document_tags")
    op.drop_index(op.f("ix_tags_user_id"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_documents_is_favorite"), table_name="documents")
    op.drop_column("documents", "is_favorite")
