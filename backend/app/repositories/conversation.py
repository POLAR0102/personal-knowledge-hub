from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Conversation,
    Message,
    MessageRequestStatus,
    MessageRole,
)


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        title: str,
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            title=title,
        )
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def list_owned(
        self,
        *,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def count_owned(self, *, user_id: int) -> int:
        statement = select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id
        )
        return self.db.execute(statement).scalar_one()

    def get_owned(
        self,
        *,
        conversation_id: int,
        user_id: int,
        with_messages: bool = False,
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        if with_messages:
            statement = statement.options(selectinload(Conversation.messages))
        return self.db.execute(statement).scalar_one_or_none()

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)

    def touch(self, conversation: Conversation) -> None:
        conversation.updated_at = func.now()

    def rollback(self) -> None:
        self.db.rollback()


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_client_request_id(
        self,
        *,
        conversation_id: int,
        client_request_id: str,
    ) -> Message | None:
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.client_request_id == client_request_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_assistant_after(
        self,
        *,
        conversation_id: int,
        user_sequence_number: int,
    ) -> Message | None:
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sequence_number == user_sequence_number + 1,
            Message.role == MessageRole.ASSISTANT,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_last(self, *, conversation_id: int) -> Message | None:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number.desc())
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def next_sequence_number(self, *, conversation_id: int) -> int:
        statement = select(func.max(Message.sequence_number)).where(
            Message.conversation_id == conversation_id
        )
        return (self.db.execute(statement).scalar_one() or 0) + 1

    def create_user(
        self,
        *,
        conversation_id: int,
        content: str,
        sequence_number: int,
        client_request_id: str,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            sequence_number=sequence_number,
            client_request_id=client_request_id,
            request_status=MessageRequestStatus.PROCESSING,
        )
        self.db.add(message)
        self.db.flush()
        return message

    def create_assistant(
        self,
        *,
        conversation_id: int,
        content: str,
        citations_json: list[dict[str, object]],
        model: str,
        sequence_number: int,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            citations_json=citations_json,
            model=model,
            sequence_number=sequence_number,
        )
        self.db.add(message)
        self.db.flush()
        return message
