"""add document index status

Revision ID: d3f6a1c8b204
Revises: e8b2c7d4f106
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3f6a1c8b204"
down_revision: Union[str, None] = "e8b2c7d4f106"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "index_status",
                sa.String(length=11),
                server_default="not_indexed",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("index_error_message", sa.String(length=1000), nullable=True)
        )
        batch_op.add_column(
            sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("embedding_model", sa.String(length=255), nullable=True)
        )
        batch_op.create_check_constraint(
            "document_index_status",
            "index_status IN ('not_indexed', 'indexing', 'indexed', 'failed')",
        )


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("document_index_status", type_="check")
        batch_op.drop_column("embedding_model")
        batch_op.drop_column("indexed_at")
        batch_op.drop_column("index_error_message")
        batch_op.drop_column("index_status")
