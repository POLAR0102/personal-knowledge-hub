import logging
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingConfigurationError, EmbeddingProvider
from app.ai.llm import (
    ChatModelConfigurationError,
    ChatModelProvider,
)
from app.ai.vector_store import (
    VectorStore,
    VectorStoreConfigurationError,
)
from app.db.models import (
    Conversation,
    Message,
    MessageRequestStatus,
    MessageRole,
    User,
)
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.services.rag_query import (
    RAGQueryDatabaseError,
    RAGQueryDependencyError,
    RAGQueryInputError,
    RAGQueryResult,
    answer_question,
)
from app.services.semantic_search import KnowledgeBaseNotFoundError

logger = logging.getLogger(__name__)


class ConversationNotFoundError(Exception):
    pass


class ConversationConflictError(Exception):
    pass


class ConversationDatabaseError(Exception):
    pass


class ConversationRAGDependencyError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MessagePair:
    user_message: Message
    assistant_message: Message


def _get_owned_conversation(
    repository: ConversationRepository,
    *,
    conversation_id: int,
    user_id: int,
    with_messages: bool = False,
) -> Conversation:
    conversation = repository.get_owned(
        conversation_id=conversation_id,
        user_id=user_id,
        with_messages=with_messages,
    )
    if conversation is None:
        raise ConversationNotFoundError
    return conversation


def _ensure_owned_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: int,
    user_id: int,
) -> None:
    knowledge_base = KnowledgeBaseRepository(db).get_owned(
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
    )
    if knowledge_base is None:
        raise ConversationNotFoundError


def create_conversation(
    db: Session,
    owner: User,
    data: ConversationCreate,
) -> Conversation:
    repository = ConversationRepository(db)
    try:
        _ensure_owned_knowledge_base(
            db,
            knowledge_base_id=data.knowledge_base_id,
            user_id=owner.id,
        )
        conversation = repository.create(
            user_id=owner.id,
            knowledge_base_id=data.knowledge_base_id,
            title=data.title,
        )
        db.commit()
        db.refresh(conversation)
        return conversation
    except ConversationNotFoundError:
        repository.rollback()
        raise
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while creating a conversation")
        raise ConversationDatabaseError from exc


def list_conversations(
    db: Session,
    owner: User,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Conversation], int]:
    repository = ConversationRepository(db)
    try:
        items = repository.list_owned(
            user_id=owner.id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = repository.count_owned(user_id=owner.id)
        return items, total
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing conversations")
        raise ConversationDatabaseError from exc


def get_conversation(
    db: Session,
    owner: User,
    conversation_id: int,
) -> Conversation:
    repository = ConversationRepository(db)
    try:
        return _get_owned_conversation(
            repository,
            conversation_id=conversation_id,
            user_id=owner.id,
            with_messages=True,
        )
    except ConversationNotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading a conversation")
        raise ConversationDatabaseError from exc


def delete_conversation(
    db: Session,
    owner: User,
    conversation_id: int,
) -> None:
    repository = ConversationRepository(db)
    try:
        conversation = _get_owned_conversation(
            repository,
            conversation_id=conversation_id,
            user_id=owner.id,
        )
        repository.delete(conversation)
        db.commit()
    except ConversationNotFoundError:
        repository.rollback()
        raise
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while deleting a conversation")
        raise ConversationDatabaseError from exc


def _citation_snapshots(result: RAGQueryResult) -> list[dict[str, object]]:
    return [
        {
            "source_number": citation.source_number,
            "chunk_id": citation.result.chunk_id,
            "document_id": citation.result.document_id,
            "filename": citation.result.filename,
            "content": citation.result.content,
            "chunk_index": citation.result.chunk_index,
            "page_number": citation.result.page_number,
            "section_title": citation.result.section_title,
            "distance": citation.result.distance,
        }
        for citation in result.citations
    ]


def _mark_user_message_failed(db: Session, message_id: int) -> None:
    db.rollback()
    try:
        message = db.get(Message, message_id)
        if message is None:
            raise ConversationDatabaseError
        message.request_status = MessageRequestStatus.FAILED
        conversation = db.get(Conversation, message.conversation_id)
        if conversation is not None:
            ConversationRepository(db).touch(conversation)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to mark a failed conversation message")
        raise ConversationDatabaseError from exc


def _completed_pair(
    message_repository: MessageRepository,
    user_message: Message,
) -> MessagePair:
    assistant_message = message_repository.get_assistant_after(
        conversation_id=user_message.conversation_id,
        user_sequence_number=user_message.sequence_number,
    )
    if assistant_message is None:
        logger.error(
            "Completed user message %s has no assistant response",
            user_message.id,
        )
        raise ConversationDatabaseError
    return MessagePair(
        user_message=user_message,
        assistant_message=assistant_message,
    )


def send_message(
    db: Session,
    owner: User,
    conversation_id: int,
    data: MessageCreate,
    *,
    provider_loader: Callable[
        [],
        tuple[EmbeddingProvider, VectorStore, ChatModelProvider],
    ],
) -> MessagePair:
    conversation_repository = ConversationRepository(db)
    message_repository = MessageRepository(db)
    provided_request_id = (
        str(data.client_request_id) if data.client_request_id is not None else None
    )
    request_id = provided_request_id or str(uuid4())

    try:
        conversation = _get_owned_conversation(
            conversation_repository,
            conversation_id=conversation_id,
            user_id=owner.id,
        )
        _ensure_owned_knowledge_base(
            db,
            knowledge_base_id=conversation.knowledge_base_id,
            user_id=owner.id,
        )

        user_message = (
            message_repository.get_by_client_request_id(
                conversation_id=conversation.id,
                client_request_id=provided_request_id,
            )
            if provided_request_id is not None
            else None
        )
        if user_message is not None:
            if user_message.content != data.content:
                raise ConversationConflictError(
                    "client_request_id was already used for different content"
                )
            if user_message.request_status == MessageRequestStatus.COMPLETED:
                return _completed_pair(message_repository, user_message)
            if user_message.request_status == MessageRequestStatus.PROCESSING:
                raise ConversationConflictError("Message request is already processing")
            user_message.request_status = MessageRequestStatus.PROCESSING
        else:
            last_message = message_repository.get_last(
                conversation_id=conversation.id
            )
            if last_message is not None and last_message.role == MessageRole.USER:
                if (
                    provided_request_id is None
                    and last_message.request_status == MessageRequestStatus.FAILED
                    and last_message.content == data.content
                ):
                    user_message = last_message
                    user_message.request_status = MessageRequestStatus.PROCESSING
                else:
                    raise ConversationConflictError(
                        "Previous message must be retried before sending a new question"
                    )
            else:
                user_message = message_repository.create_user(
                    conversation_id=conversation.id,
                    content=data.content,
                    sequence_number=message_repository.next_sequence_number(
                        conversation_id=conversation.id
                    ),
                    client_request_id=request_id,
                )

        conversation_repository.touch(conversation)
        db.commit()
        db.refresh(user_message)
    except ConversationConflictError:
        db.rollback()
        raise
    except ConversationNotFoundError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.info("Concurrent conversation message request was rejected")
        raise ConversationConflictError("Duplicate message request") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while saving a user message")
        raise ConversationDatabaseError from exc

    try:
        embedding_provider, vector_store, chat_model = provider_loader()
    except (
        EmbeddingConfigurationError,
        VectorStoreConfigurationError,
        ChatModelConfigurationError,
    ) as exc:
        _mark_user_message_failed(db, user_message.id)
        raise ConversationRAGDependencyError(
            "RAG service is not configured"
        ) from exc
    except Exception as exc:
        _mark_user_message_failed(db, user_message.id)
        logger.exception("Unexpected error while loading RAG providers")
        raise ConversationRAGDependencyError(
            "Unable to load RAG services"
        ) from exc

    try:
        rag_result = answer_question(
            db,
            owner,
            knowledge_base_id=conversation.knowledge_base_id,
            question=user_message.content,
            top_k=data.top_k,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            chat_model=chat_model,
        )
    except KnowledgeBaseNotFoundError as exc:
        _mark_user_message_failed(db, user_message.id)
        raise ConversationNotFoundError from exc
    except RAGQueryInputError as exc:
        _mark_user_message_failed(db, user_message.id)
        raise ConversationConflictError(str(exc)) from exc
    except RAGQueryDependencyError as exc:
        _mark_user_message_failed(db, user_message.id)
        raise ConversationRAGDependencyError(str(exc)) from exc
    except RAGQueryDatabaseError as exc:
        _mark_user_message_failed(db, user_message.id)
        raise ConversationDatabaseError from exc
    except Exception as exc:
        _mark_user_message_failed(db, user_message.id)
        logger.exception("Unexpected error while answering a conversation message")
        raise ConversationRAGDependencyError(
            "Unable to generate conversation response"
        ) from exc

    try:
        assistant_message = message_repository.create_assistant(
            conversation_id=conversation.id,
            content=rag_result.answer,
            citations_json=_citation_snapshots(rag_result),
            model=rag_result.model,
            sequence_number=user_message.sequence_number + 1,
        )
        user_message.request_status = MessageRequestStatus.COMPLETED
        conversation_repository.touch(conversation)
        db.commit()
        db.refresh(user_message)
        db.refresh(assistant_message)
        return MessagePair(
            user_message=user_message,
            assistant_message=assistant_message,
        )
    except SQLAlchemyError as exc:
        _mark_user_message_failed(db, user_message.id)
        logger.exception("Database error while saving an assistant message")
        raise ConversationDatabaseError from exc
