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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageRequestStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_messages_conversation_id_sequence_number",
        ),
        UniqueConstraint(
            "conversation_id",
            "client_request_id",
            name="uq_messages_conversation_id_client_request_id",
        ),
        CheckConstraint(
            "length(content) > 0",
            name="ck_messages_content_not_empty",
        ),
        CheckConstraint(
            "sequence_number > 0",
            name="ck_messages_sequence_number_positive",
        ),
        CheckConstraint(
            "(role = 'user' AND client_request_id IS NOT NULL "
            "AND request_status IS NOT NULL) OR "
            "(role = 'assistant' AND client_request_id IS NULL "
            "AND request_status IS NULL)",
            name="ck_messages_request_fields_by_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        SqlEnum(
            MessageRole,
            name="message_role",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    client_request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    request_status: Mapped[MessageRequestStatus | None] = mapped_column(
        SqlEnum(
            MessageRequestStatus,
            name="message_request_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
