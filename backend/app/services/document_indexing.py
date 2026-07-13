import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.ai.vector_store import VectorRecord, VectorStore, VectorStoreError
from app.db.models import (
    Document,
    DocumentIndexStatus,
    DocumentStatus,
    User,
)
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    pass


class DocumentNotReadyForIndexError(Exception):
    pass


class DocumentAlreadyIndexingError(Exception):
    pass


class DocumentIndexingFailedError(Exception):
    pass


class DocumentIndexingDatabaseError(Exception):
    pass


class DocumentIndexingDependencyError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class _ChunkSnapshot:
    id: int
    chunk_index: int
    content: str
    content_hash: str
    page_number: int | None
    section_title: str | None


@dataclass(frozen=True, slots=True)
class IndexingResult:
    document: Document
    chunk_count: int
    vector_count: int


@dataclass(frozen=True, slots=True)
class IndexStatusResult:
    document: Document
    chunk_count: int
    vector_count: int


def _get_owned_document(db: Session, user_id: int, document_id: int) -> Document:
    try:
        document = DocumentRepository(db).get_owned(
            document_id=document_id,
            user_id=user_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading document for indexing")
        raise DocumentIndexingDatabaseError from exc
    if document is None:
        raise DocumentNotFoundError
    return document


def _get_chunk_snapshots(
    db: Session,
    user_id: int,
    document_id: int,
) -> list[_ChunkSnapshot]:
    try:
        chunks = DocumentChunkRepository(db).list_all_for_document(
            document_id=document_id,
            user_id=user_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading chunks for indexing")
        raise DocumentIndexingDatabaseError from exc
    return [
        _ChunkSnapshot(
            id=chunk.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
        )
        for chunk in chunks
    ]


def _mark_index_failed(
    db: Session,
    user_id: int,
    document_id: int,
    message: str,
) -> None:
    db.rollback()
    try:
        document = DocumentRepository(db).get_owned(
            document_id=document_id,
            user_id=user_id,
        )
        if document is None:
            raise DocumentNotFoundError
        document.index_status = DocumentIndexStatus.FAILED
        document.index_error_message = message[:1000]
        document.indexed_at = None
        document.embedding_model = None
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to persist failed document index status")
        raise DocumentIndexingDatabaseError from exc


def _cleanup_partial_vectors(
    vector_store: VectorStore,
    document_id: int,
    user_id: int,
) -> None:
    try:
        vector_store.delete_by_document(document_id, user_id)
    except VectorStoreError as exc:
        logger.error(
            "Unable to clean partial vectors for document %s after %s",
            document_id,
            type(exc).__name__,
        )


def index_document(
    db: Session,
    owner: User,
    document_id: int,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
) -> IndexingResult:
    document = _get_owned_document(db, owner.id, document_id)
    if document.status != DocumentStatus.COMPLETED:
        raise DocumentNotReadyForIndexError(
            "Document must be processed before indexing"
        )
    if document.index_status == DocumentIndexStatus.INDEXING:
        raise DocumentAlreadyIndexingError

    chunks = _get_chunk_snapshots(db, owner.id, document_id)
    if not chunks:
        raise DocumentNotReadyForIndexError("Document has no chunks to index")
    knowledge_base_id = document.knowledge_base_id
    original_filename = document.original_filename

    try:
        claimed = DocumentRepository(db).try_start_indexing(
            document_id=document_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to start document indexing")
        raise DocumentIndexingDatabaseError from exc
    if not claimed:
        current = _get_owned_document(db, owner.id, document_id)
        if current.index_status == DocumentIndexStatus.INDEXING:
            raise DocumentAlreadyIndexingError
        raise DocumentNotReadyForIndexError(
            "Document must be processed before indexing"
        )

    try:
        vector_store.delete_by_document(document_id, owner.id)
        embeddings = embedding_provider.embed_documents(
            [chunk.content for chunk in chunks]
        )
        if len(embeddings) != len(chunks):
            raise DocumentIndexingFailedError(
                "Embedding count does not match document chunk count"
            )

        vector_store.upsert_chunks(
            [
                VectorRecord(
                    chunk_id=chunk.id,
                    user_id=owner.id,
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    filename=original_filename,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    embedding_model=embedding_provider.model_name,
                    embedding=embedding,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]
        )
        vector_count = vector_store.count_by_document(document_id, owner.id)
        if vector_count != len(chunks):
            raise DocumentIndexingFailedError(
                "Vector count does not match document chunk count"
            )

        indexed_document = _get_owned_document(db, owner.id, document_id)
        indexed_document.index_status = DocumentIndexStatus.INDEXED
        indexed_document.index_error_message = None
        indexed_document.indexed_at = datetime.now(timezone.utc)
        indexed_document.embedding_model = embedding_provider.model_name
        db.commit()
        db.refresh(indexed_document)
        return IndexingResult(
            document=indexed_document,
            chunk_count=len(chunks),
            vector_count=vector_count,
        )
    except EmbeddingError as exc:
        message = "生成文档向量失败，请检查 Embedding 服务配置后重试"
        logger.warning(
            "Embedding failed while indexing document %s with %s",
            document_id,
            type(exc).__name__,
        )
    except VectorStoreError as exc:
        message = "保存文档向量失败，请稍后重试"
        logger.warning(
            "Vector store failed while indexing document %s with %s",
            document_id,
            type(exc).__name__,
        )
    except DocumentIndexingFailedError as exc:
        message = str(exc)
        logger.warning("Document %s index validation failed", document_id)
    except SQLAlchemyError as exc:
        message = "保存索引状态失败，请稍后重试"
        logger.exception("Database error while completing document indexing")
        _cleanup_partial_vectors(vector_store, document_id, owner.id)
        _mark_index_failed(db, owner.id, document_id, message)
        raise DocumentIndexingDatabaseError from exc
    except Exception as exc:
        message = "文档索引失败，请稍后重试"
        logger.exception("Unexpected error while indexing document %s", document_id)
        _cleanup_partial_vectors(vector_store, document_id, owner.id)
        _mark_index_failed(db, owner.id, document_id, message)
        raise DocumentIndexingFailedError(message) from exc

    _cleanup_partial_vectors(vector_store, document_id, owner.id)
    _mark_index_failed(db, owner.id, document_id, message)
    raise DocumentIndexingFailedError(message)


def get_document_index_status(
    db: Session,
    owner: User,
    document_id: int,
    vector_store: VectorStore,
) -> IndexStatusResult:
    document = _get_owned_document(db, owner.id, document_id)
    try:
        chunk_count = DocumentChunkRepository(db).count_for_document(
            document_id=document_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while counting chunks for index status")
        raise DocumentIndexingDatabaseError from exc
    try:
        vector_count = vector_store.count_by_document(document_id, owner.id)
    except VectorStoreError as exc:
        logger.warning(
            "Vector store failed while loading index status for document %s",
            document_id,
        )
        raise DocumentIndexingDependencyError from exc
    return IndexStatusResult(
        document=document,
        chunk_count=chunk_count,
        vector_count=vector_count,
    )
