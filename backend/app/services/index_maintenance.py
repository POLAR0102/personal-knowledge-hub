import logging
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider
from app.ai.vector_store import VectorStore, VectorStoreError
from app.db.models import Document, DocumentIndexStatus, DocumentStatus, User
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.index_maintenance import IndexHealthStatus
from app.services.document_indexing import (
    DocumentAlreadyIndexingError,
    DocumentIndexingDatabaseError,
    DocumentIndexingFailedError,
    DocumentNotFoundError,
    DocumentNotReadyForIndexError,
    index_document,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseNotFoundError(Exception):
    pass


class IndexMaintenanceDatabaseError(Exception):
    pass


class IndexMaintenanceDependencyError(Exception):
    pass


class KnowledgeBaseReindexLimitError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class DocumentIndexHealth:
    document: Document
    health_status: IndexHealthStatus
    chunk_count: int
    vector_count: int
    current_embedding_model: str


@dataclass(frozen=True, slots=True)
class KnowledgeBaseReindexItemResult:
    document_id: int
    original_filename: str
    index_status: DocumentIndexStatus
    vector_count: int
    error_message: str | None


@dataclass(frozen=True, slots=True)
class KnowledgeBaseReindexResult:
    knowledge_base_id: int
    items: list[KnowledgeBaseReindexItemResult]

    @property
    def succeeded(self) -> int:
        return sum(item.index_status == DocumentIndexStatus.INDEXED for item in self.items)

    @property
    def failed(self) -> int:
        return len(self.items) - self.succeeded


def _get_owned_document(db: Session, owner: User, document_id: int) -> Document:
    try:
        document = DocumentRepository(db).get_owned(
            document_id=document_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading document index health")
        raise IndexMaintenanceDatabaseError from exc
    if document is None:
        raise DocumentNotFoundError
    return document


def get_document_index_health(
    db: Session,
    owner: User,
    document_id: int,
    vector_store: VectorStore,
    current_embedding_model: str,
) -> DocumentIndexHealth:
    document = _get_owned_document(db, owner, document_id)
    try:
        chunk_count = DocumentChunkRepository(db).count_for_document(
            document_id=document.id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while counting chunks for index health")
        raise IndexMaintenanceDatabaseError from exc
    try:
        vector_count = vector_store.count_by_document(document.id, owner.id)
    except VectorStoreError as exc:
        logger.warning("Vector store failed while checking document index health")
        raise IndexMaintenanceDependencyError from exc

    if document.index_status == DocumentIndexStatus.FAILED:
        health_status = IndexHealthStatus.FAILED
    elif document.index_status == DocumentIndexStatus.INDEXED:
        if document.embedding_model != current_embedding_model:
            health_status = IndexHealthStatus.MODEL_MISMATCH
        elif vector_count < chunk_count:
            health_status = IndexHealthStatus.MISSING_VECTORS
        elif vector_count > chunk_count:
            health_status = IndexHealthStatus.EXTRA_VECTORS
        else:
            health_status = IndexHealthStatus.HEALTHY
    elif vector_count > chunk_count:
        health_status = IndexHealthStatus.EXTRA_VECTORS
    elif 0 < vector_count < chunk_count:
        health_status = IndexHealthStatus.MISSING_VECTORS
    else:
        health_status = IndexHealthStatus.NOT_INDEXED

    return DocumentIndexHealth(
        document=document,
        health_status=health_status,
        chunk_count=chunk_count,
        vector_count=vector_count,
        current_embedding_model=current_embedding_model,
    )


def reindex_knowledge_base(
    db: Session,
    owner: User,
    knowledge_base_id: int,
    *,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    document_limit: int,
) -> KnowledgeBaseReindexResult:
    try:
        knowledge_base = KnowledgeBaseRepository(db).get_owned(
            knowledge_base_id=knowledge_base_id,
            user_id=owner.id,
        )
        documents = DocumentRepository(db).list_owned_by_knowledge_base(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading knowledge base for reindex")
        raise IndexMaintenanceDatabaseError from exc
    if knowledge_base is None:
        raise KnowledgeBaseNotFoundError

    indexable_documents = [
        (document.id, document.original_filename)
        for document in documents
        if document.status == DocumentStatus.COMPLETED
    ]
    if document_limit < 1 or len(indexable_documents) > document_limit:
        raise KnowledgeBaseReindexLimitError(
            f"Knowledge base reindex is limited to {document_limit} documents"
        )

    items: list[KnowledgeBaseReindexItemResult] = []
    for document_id, original_filename in indexable_documents:
        try:
            indexed = index_document(
                db,
                owner,
                document_id,
                embedding_provider,
                vector_store,
            )
            items.append(
                KnowledgeBaseReindexItemResult(
                    document_id=document_id,
                    original_filename=original_filename,
                    index_status=DocumentIndexStatus.INDEXED,
                    vector_count=indexed.vector_count,
                    error_message=None,
                )
            )
        except (
            DocumentAlreadyIndexingError,
            DocumentIndexingFailedError,
            DocumentNotReadyForIndexError,
        ) as exc:
            items.append(
                KnowledgeBaseReindexItemResult(
                    document_id=document_id,
                    original_filename=original_filename,
                    index_status=DocumentIndexStatus.FAILED,
                    vector_count=0,
                    error_message=str(exc) or "Document indexing failed",
                )
            )
        except DocumentIndexingDatabaseError:
            items.append(
                KnowledgeBaseReindexItemResult(
                    document_id=document_id,
                    original_filename=original_filename,
                    index_status=DocumentIndexStatus.FAILED,
                    vector_count=0,
                    error_message="Document indexing database operation failed",
                )
            )

    return KnowledgeBaseReindexResult(
        knowledge_base_id=knowledge_base.id,
        items=items,
    )
