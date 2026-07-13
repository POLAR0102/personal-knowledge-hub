import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.vector_store import VectorStore, VectorStoreError, get_vector_store
from app.db.models import DocumentIndexStatus, KnowledgeBase, User
from app.repositories.document import DocumentRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate

logger = logging.getLogger(__name__)


class KnowledgeBaseNotFoundError(Exception):
    pass


class KnowledgeBaseDatabaseError(Exception):
    pass


class KnowledgeBaseIndexingInProgressError(Exception):
    pass


class KnowledgeBaseVectorStoreError(Exception):
    pass


def create_knowledge_base(
    db: Session,
    owner: User,
    data: KnowledgeBaseCreate,
) -> KnowledgeBase:
    repository = KnowledgeBaseRepository(db)
    try:
        return repository.create(
            user_id=owner.id,
            name=data.name,
            description=data.description,
        )
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while creating a knowledge base")
        raise KnowledgeBaseDatabaseError from exc


def list_knowledge_bases(
    db: Session,
    owner: User,
    *,
    page: int,
    page_size: int,
) -> tuple[list[KnowledgeBase], int]:
    repository = KnowledgeBaseRepository(db)
    try:
        items = repository.list_owned(
            user_id=owner.id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = repository.count_owned(user_id=owner.id)
        return items, total
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing knowledge bases")
        raise KnowledgeBaseDatabaseError from exc


def get_knowledge_base(
    db: Session,
    owner: User,
    knowledge_base_id: int,
) -> KnowledgeBase:
    repository = KnowledgeBaseRepository(db)
    try:
        knowledge_base = repository.get_owned(
            knowledge_base_id=knowledge_base_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading a knowledge base")
        raise KnowledgeBaseDatabaseError from exc

    if knowledge_base is None:
        raise KnowledgeBaseNotFoundError
    return knowledge_base


def update_knowledge_base(
    db: Session,
    owner: User,
    knowledge_base_id: int,
    data: KnowledgeBaseUpdate,
) -> KnowledgeBase:
    repository = KnowledgeBaseRepository(db)
    knowledge_base = get_knowledge_base(db, owner, knowledge_base_id)
    values = data.model_dump(exclude_unset=True)

    try:
        return repository.update(knowledge_base, values)
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while updating a knowledge base")
        raise KnowledgeBaseDatabaseError from exc


def delete_knowledge_base(
    db: Session,
    owner: User,
    knowledge_base_id: int,
    vector_store: VectorStore | None = None,
) -> None:
    repository = KnowledgeBaseRepository(db)
    knowledge_base = get_knowledge_base(db, owner, knowledge_base_id)

    try:
        documents = DocumentRepository(db).list_owned_by_knowledge_base(
            user_id=owner.id,
            knowledge_base_id=knowledge_base.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading documents for knowledge base deletion")
        raise KnowledgeBaseDatabaseError from exc
    if any(
        document.index_status == DocumentIndexStatus.INDEXING
        for document in documents
    ):
        raise KnowledgeBaseIndexingInProgressError
    if any(
        document.index_status != DocumentIndexStatus.NOT_INDEXED
        for document in documents
    ):
        try:
            (vector_store or get_vector_store()).delete_by_knowledge_base(
                knowledge_base.id,
                owner.id,
            )
        except VectorStoreError as exc:
            logger.warning(
                "Unable to delete vectors before deleting knowledge base %s",
                knowledge_base_id,
            )
            raise KnowledgeBaseVectorStoreError from exc

    try:
        repository.delete(knowledge_base)
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while deleting a knowledge base")
        raise KnowledgeBaseDatabaseError from exc
