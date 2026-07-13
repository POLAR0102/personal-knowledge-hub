from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.knowledge_base import KnowledgeBase
    from app.db.models.note import Note
    from app.db.models.user import User


class AgentTaskType(str, Enum):
    SUMMARY = "summary"
    STUDY_PLAN = "study_plan"
    TOPIC_NOTE = "topic_note"


class AgentTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        CheckConstraint(
            "length(task_input) > 0",
            name="ck_agent_tasks_input_not_empty",
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
    task_type: Mapped[AgentTaskType] = mapped_column(
        SqlEnum(
            AgentTaskType,
            name="agent_task_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
    )
    task_input: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AgentTaskStatus] = mapped_column(
        SqlEnum(
            AgentTaskStatus,
            name="agent_task_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
        default=AgentTaskStatus.PENDING,
        server_default=AgentTaskStatus.PENDING.value,
    )
    result_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations_json: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    owner: Mapped["User"] = relationship(back_populates="agent_tasks")
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        back_populates="agent_tasks"
    )
    note: Mapped["Note | None"] = relationship(
        back_populates="source_agent_task",
        uselist=False,
        passive_deletes=True,
    )
