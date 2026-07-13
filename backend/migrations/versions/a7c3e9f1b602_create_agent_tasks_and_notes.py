"""create agent tasks and notes

Revision ID: a7c3e9f1b602
Revises: f2a9c4e7d105
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c3e9f1b602"
down_revision: Union[str, None] = "f2a9c4e7d105"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=10), nullable=False),
        sa.Column("task_input", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=9),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("result_content", sa.Text(), nullable=True),
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "task_type IN ('summary', 'study_plan', 'topic_note')",
            name="agent_task_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="agent_task_status",
        ),
        sa.CheckConstraint(
            "length(task_input) > 0",
            name="ck_agent_tasks_input_not_empty",
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
        op.f("ix_agent_tasks_knowledge_base_id"),
        "agent_tasks",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_tasks_user_id"),
        "agent_tasks",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "source_type",
            sa.String(length=6),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("source_agent_task_id", sa.Integer(), nullable=True),
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
            name="ck_notes_title_length",
        ),
        sa.CheckConstraint(
            "length(content) > 0",
            name="ck_notes_content_not_empty",
        ),
        sa.CheckConstraint(
            "source_type IN ('manual', 'agent')",
            name="note_source_type",
        ),
        sa.CheckConstraint(
            "(source_type = 'manual' AND source_agent_task_id IS NULL) "
            "OR (source_type = 'agent' AND source_agent_task_id IS NOT NULL)",
            name="ck_notes_source_fields",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_agent_task_id"],
            ["agent_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_agent_task_id",
            name="uq_notes_source_agent_task_id",
        ),
    )
    op.create_index(
        op.f("ix_notes_knowledge_base_id"),
        "notes",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notes_user_id"),
        "notes",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notes_user_id"), table_name="notes")
    op.drop_index(op.f("ix_notes_knowledge_base_id"), table_name="notes")
    op.drop_table("notes")
    op.drop_index(op.f("ix_agent_tasks_user_id"), table_name="agent_tasks")
    op.drop_index(
        op.f("ix_agent_tasks_knowledge_base_id"),
        table_name="agent_tasks",
    )
    op.drop_table("agent_tasks")
