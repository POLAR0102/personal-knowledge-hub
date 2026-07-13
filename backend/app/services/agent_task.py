import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.agent import (
    build_agent_citations,
    build_agent_messages,
    organize_context,
)
from app.ai.embeddings import EmbeddingConfigurationError, EmbeddingProvider
from app.ai.llm import (
    ChatModelConfigurationError,
    ChatModelError,
    ChatModelProvider,
)
from app.ai.vector_store import (
    SearchResult,
    VectorStore,
    VectorStoreConfigurationError,
)
from app.core.config import get_settings
from app.db.models import AgentTask, AgentTaskStatus, User
from app.repositories.agent_task import AgentTaskRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.agent_task import AgentTaskCreate
from app.services.semantic_search import (
    KnowledgeBaseNotFoundError,
    SemanticSearchDatabaseError,
    SemanticSearchDependencyError,
    SemanticSearchInputError,
    SemanticSearchResult,
    semantic_search,
)

logger = logging.getLogger(__name__)
AGENT_SEARCH_TOP_K = 8
NO_RESULTS_MARKDOWN = (
    "# 资料不足\n\n"
    "当前知识库中未检索到与该任务相关的资料，无法生成有依据的内容。"
)
ProviderLoader = Callable[
    [],
    tuple[EmbeddingProvider, VectorStore, ChatModelProvider],
]


class AgentTaskNotFoundError(Exception):
    pass


class AgentTaskConflictError(Exception):
    pass


class AgentTaskDatabaseError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
        raise AgentTaskNotFoundError


def search_knowledge_base(
    db: Session,
    owner: User,
    *,
    knowledge_base_id: int,
    query: str,
    top_k: int,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
) -> SemanticSearchResult:
    """The fixed Agent workflow's only knowledge-access tool."""
    return semantic_search(
        db,
        owner,
        knowledge_base_id=knowledge_base_id,
        query=query,
        top_k=top_k,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


def _get_owned_task(
    repository: AgentTaskRepository,
    *,
    task_id: int,
    user_id: int,
) -> AgentTask:
    task = repository.get_owned(task_id=task_id, user_id=user_id)
    if task is None:
        raise AgentTaskNotFoundError
    return task


def _citation_snapshots(
    result_content: str,
    source_map: dict[int, SearchResult],
) -> list[dict[str, object]]:
    citations = build_agent_citations(result_content, source_map)
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
        for citation in citations
    ]


def _mark_failed(db: Session, task_id: int, error_message: str) -> AgentTask:
    db.rollback()
    try:
        task = db.get(AgentTask, task_id)
        if task is None:
            raise AgentTaskNotFoundError
        task.status = AgentTaskStatus.FAILED
        task.result_content = None
        task.citations_json = None
        task.error_message = error_message
        task.completed_at = _now()
        db.commit()
        db.refresh(task)
        return task
    except AgentTaskNotFoundError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to mark Agent task as failed")
        raise AgentTaskDatabaseError from exc


def _complete_task(
    db: Session,
    task: AgentTask,
    *,
    result_content: str,
    citations: list[dict[str, object]],
) -> AgentTask:
    try:
        task.status = AgentTaskStatus.COMPLETED
        task.result_content = result_content
        task.citations_json = citations
        task.error_message = None
        task.completed_at = _now()
        db.commit()
        db.refresh(task)
        return task
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while completing Agent task")
        raise AgentTaskDatabaseError from exc


def _execute_task(
    db: Session,
    owner: User,
    task: AgentTask,
    *,
    expected_status: AgentTaskStatus,
    provider_loader: ProviderLoader,
) -> AgentTask:
    repository = AgentTaskRepository(db)
    try:
        claimed = repository.claim_for_execution(
            task_id=task.id,
            user_id=owner.id,
            expected_status=expected_status,
            started_at=_now(),
        )
        if not claimed:
            db.rollback()
            raise AgentTaskConflictError("Agent task is already running")
        db.commit()
        db.refresh(task)
    except AgentTaskConflictError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while starting Agent task")
        raise AgentTaskDatabaseError from exc

    try:
        embedding_provider, vector_store, chat_model = provider_loader()
    except (
        EmbeddingConfigurationError,
        VectorStoreConfigurationError,
        ChatModelConfigurationError,
    ):
        return _mark_failed(db, task.id, "Agent service is not configured")
    except Exception:
        logger.exception("Unexpected error while loading Agent providers")
        return _mark_failed(db, task.id, "Unable to load Agent services")

    try:
        search_result = search_knowledge_base(
            db,
            owner,
            knowledge_base_id=task.knowledge_base_id,
            query=task.task_input,
            top_k=AGENT_SEARCH_TOP_K,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )
    except KnowledgeBaseNotFoundError:
        return _mark_failed(db, task.id, "Knowledge base not found")
    except SemanticSearchInputError:
        return _mark_failed(db, task.id, "Agent task input is invalid")
    except SemanticSearchDependencyError:
        return _mark_failed(db, task.id, "Unable to retrieve knowledge base content")
    except SemanticSearchDatabaseError:
        return _mark_failed(db, task.id, "Unable to retrieve knowledge base content")
    except Exception:
        logger.exception("Unexpected error while retrieving Agent context")
        return _mark_failed(db, task.id, "Unable to retrieve knowledge base content")

    context = organize_context(
        search_result.results,
        max_characters=get_settings().rag_max_context_chars,
    )
    if not context.used_results:
        return _complete_task(
            db,
            task,
            result_content=NO_RESULTS_MARKDOWN,
            citations=[],
        )

    messages = build_agent_messages(
        task_type=task.task_type.value,
        task_input=task.task_input,
        context=context.content,
    )
    settings = get_settings()
    try:
        generated = chat_model.generate(
            messages,
            temperature=settings.rag_temperature,
            max_tokens=settings.rag_max_tokens,
        )
    except ChatModelError:
        return _mark_failed(db, task.id, "Unable to generate Agent result")
    except Exception:
        logger.exception("Unexpected error while generating Agent result")
        return _mark_failed(db, task.id, "Unable to generate Agent result")

    citations = _citation_snapshots(generated.content, context.source_map)
    return _complete_task(
        db,
        task,
        result_content=generated.content,
        citations=citations,
    )


def create_agent_task(
    db: Session,
    owner: User,
    data: AgentTaskCreate,
    *,
    provider_loader: ProviderLoader,
) -> AgentTask:
    repository = AgentTaskRepository(db)
    try:
        _ensure_owned_knowledge_base(
            db,
            knowledge_base_id=data.knowledge_base_id,
            user_id=owner.id,
        )
        task = repository.create(
            user_id=owner.id,
            knowledge_base_id=data.knowledge_base_id,
            task_type=data.task_type,
            task_input=data.task_input,
        )
        db.commit()
        db.refresh(task)
    except AgentTaskNotFoundError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while creating Agent task")
        raise AgentTaskDatabaseError from exc

    return _execute_task(
        db,
        owner,
        task,
        expected_status=AgentTaskStatus.PENDING,
        provider_loader=provider_loader,
    )


def list_agent_tasks(
    db: Session,
    owner: User,
    *,
    page: int,
    page_size: int,
    knowledge_base_id: int | None,
) -> tuple[list[AgentTask], int]:
    repository = AgentTaskRepository(db)
    try:
        if knowledge_base_id is not None:
            _ensure_owned_knowledge_base(
                db,
                knowledge_base_id=knowledge_base_id,
                user_id=owner.id,
            )
        items = repository.list_owned(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = repository.count_owned(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
        )
        return items, total
    except AgentTaskNotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing Agent tasks")
        raise AgentTaskDatabaseError from exc


def get_agent_task(db: Session, owner: User, task_id: int) -> AgentTask:
    try:
        return _get_owned_task(
            AgentTaskRepository(db),
            task_id=task_id,
            user_id=owner.id,
        )
    except AgentTaskNotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading Agent task")
        raise AgentTaskDatabaseError from exc


def retry_agent_task(
    db: Session,
    owner: User,
    task_id: int,
    *,
    provider_loader: ProviderLoader,
) -> AgentTask:
    repository = AgentTaskRepository(db)
    try:
        task = _get_owned_task(
            repository,
            task_id=task_id,
            user_id=owner.id,
        )
        if task.status != AgentTaskStatus.FAILED:
            raise AgentTaskConflictError(
                "Only failed Agent tasks can be retried"
            )
        _ensure_owned_knowledge_base(
            db,
            knowledge_base_id=task.knowledge_base_id,
            user_id=owner.id,
        )
    except (AgentTaskNotFoundError, AgentTaskConflictError):
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while preparing Agent task retry")
        raise AgentTaskDatabaseError from exc

    return _execute_task(
        db,
        owner,
        task,
        expected_status=AgentTaskStatus.FAILED,
        provider_loader=provider_loader,
    )
