"""create conversations and messages

Revision ID: f2a9c4e7d105
Revises: d3f6a1c8b204
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a9c4e7d105"
down_revision: Union[str, None] = "d3f6a1c8b204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
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
            "length(title) BETWEEN 1 AND 100",
            name="ck_conversations_title_length",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversations_knowledge_base_id"),
        "conversations",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversations_user_id"),
        "conversations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=9), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("client_request_id", sa.String(length=36), nullable=True),
        sa.Column("request_status", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(content) > 0",
            name="ck_messages_content_not_empty",
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_messages_sequence_number_positive",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="message_role",
        ),
        sa.CheckConstraint(
            "request_status IS NULL OR request_status IN "
            "('processing', 'completed', 'failed')",
            name="message_request_status",
        ),
        sa.CheckConstraint(
            "(role = 'user' AND client_request_id IS NOT NULL "
            "AND request_status IS NOT NULL) OR "
            "(role = 'assistant' AND client_request_id IS NULL "
            "AND request_status IS NULL)",
            name="ck_messages_request_fields_by_role",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "client_request_id",
            name="uq_messages_conversation_id_client_request_id",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_messages_conversation_id_sequence_number",
        ),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"),
        "messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_index(
        op.f("ix_conversations_knowledge_base_id"),
        table_name="conversations",
    )
    op.drop_table("conversations")
