from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.agent_task import AgentTask
    from app.db.models.knowledge_base import KnowledgeBase
    from app.db.models.user import User


class NoteSourceType(str, Enum):
    MANUAL = "manual"
    AGENT = "agent"


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint(
            "length(title) BETWEEN 1 AND 100",
            name="ck_notes_title_length",
        ),
        CheckConstraint(
            "length(content) > 0",
            name="ck_notes_content_not_empty",
        ),
        CheckConstraint(
            "(source_type = 'manual' AND source_agent_task_id IS NULL) "
            "OR (source_type = 'agent' AND source_agent_task_id IS NOT NULL)",
            name="ck_notes_source_fields",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[NoteSourceType] = mapped_column(
        SqlEnum(
            NoteSourceType,
            name="note_source_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=NoteSourceType.MANUAL,
        server_default=NoteSourceType.MANUAL.value,
    )
    source_agent_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped["User"] = relationship(back_populates="notes")
    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="notes")
    source_agent_task: Mapped["AgentTask | None"] = relationship(
        back_populates="note"
    )
