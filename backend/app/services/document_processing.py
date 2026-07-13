import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.vector_store import VectorStore, VectorStoreError, get_vector_store
from app.ai.document_processing.base import DocumentProcessingError
from app.ai.document_processing.chunker import Chunker
from app.ai.document_processing.registry import parse_document
from app.core.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentIndexStatus,
    DocumentStatus,
    User,
)
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    pass


class DocumentAlreadyProcessingError(Exception):
    pass


class DocumentAlreadyIndexingError(Exception):
    pass


class DocumentProcessingFailedError(Exception):
    pass


class DocumentProcessingDatabaseError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    document: Document
    chunk_count: int


def _get_owned_document(db: Session, user_id: int, document_id: int) -> Document:
    try:
        document = DocumentRepository(db).get_owned(
            document_id=document_id,
            user_id=user_id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading document for processing")
        raise DocumentProcessingDatabaseError from exc
    if document is None:
        raise DocumentNotFoundError
    return document


def _mark_failed(db: Session, user_id: int, document_id: int, message: str) -> None:
    db.rollback()
    try:
        document = DocumentRepository(db).get_owned(
            document_id=document_id,
            user_id=user_id,
        )
        if document is None:
            raise DocumentNotFoundError
        document.status = DocumentStatus.FAILED
        document.error_message = message[:1000]
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to persist failed document status")
        raise DocumentProcessingDatabaseError from exc


def _validated_file_path(document: Document) -> Path:
    upload_root = get_settings().upload_dir.expanduser().resolve()
    file_path = Path(document.file_path).resolve()
    if not file_path.is_relative_to(upload_root):
        raise DocumentProcessingFailedError("文档文件路径无效")
    if not file_path.is_file():
        raise DocumentProcessingFailedError("文档文件不存在，请重新上传")
    return file_path


def process_document(
    db: Session,
    owner: User,
    document_id: int,
    vector_store: VectorStore | None = None,
) -> ProcessingResult:
    document = _get_owned_document(db, owner.id, document_id)
    if document.status == DocumentStatus.PROCESSING:
        raise DocumentAlreadyProcessingError
    if document.index_status == DocumentIndexStatus.INDEXING:
        raise DocumentAlreadyIndexingError

    try:
        file_path = _validated_file_path(document)
    except DocumentProcessingFailedError as exc:
        _mark_failed(db, owner.id, document_id, str(exc))
        raise

    if document.index_status != DocumentIndexStatus.NOT_INDEXED:
        try:
            (vector_store or get_vector_store()).delete_by_document(
                document.id,
                owner.id,
            )
        except VectorStoreError as exc:
            logger.warning(
                "Unable to invalidate vector index before processing document %s",
                document_id,
            )
            raise DocumentProcessingFailedError(
                "清理旧向量索引失败，请稍后重试"
            ) from exc

    chunk_repository = DocumentChunkRepository(db)
    try:
        chunk_repository.delete_for_document(document_id=document.id)
        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        document.index_status = DocumentIndexStatus.NOT_INDEXED
        document.index_error_message = None
        document.indexed_at = None
        document.embedding_model = None
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to start document processing")
        raise DocumentProcessingDatabaseError from exc

    try:
        parsed_document = parse_document(file_path, document.file_type)
        drafts = Chunker().split(parsed_document)
        if not drafts:
            raise DocumentProcessingFailedError("文档没有可用于切分的有效文本")

        chunk_repository.create_many(
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            drafts=drafts,
        )
        document.status = DocumentStatus.COMPLETED
        document.error_message = None
        db.commit()
        db.refresh(document)
        return ProcessingResult(document=document, chunk_count=len(drafts))
    except DocumentProcessingError as exc:
        logger.warning("Document processing failed for document %s: %s", document_id, exc)
        _mark_failed(db, owner.id, document_id, str(exc))
        raise DocumentProcessingFailedError(str(exc)) from exc
    except DocumentProcessingFailedError as exc:
        logger.warning("Document processing produced no chunks for document %s", document_id)
        _mark_failed(db, owner.id, document_id, str(exc))
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while saving document chunks")
        _mark_failed(db, owner.id, document_id, "保存文本片段失败，请稍后重试")
        raise DocumentProcessingDatabaseError from exc
    except Exception as exc:
        logger.exception("Unexpected error while processing document %s", document_id)
        message = "文档处理失败，请检查文件内容"
        _mark_failed(db, owner.id, document_id, message)
        raise DocumentProcessingFailedError(message) from exc


def list_document_chunks(
    db: Session,
    owner: User,
    document_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[DocumentChunk], int]:
    _get_owned_document(db, owner.id, document_id)
    repository = DocumentChunkRepository(db)
    try:
        items = repository.list_for_document(
            document_id=document_id,
            user_id=owner.id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = repository.count_for_document(
            document_id=document_id,
            user_id=owner.id,
        )
        return items, total
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing document chunks")
        raise DocumentProcessingDatabaseError from exc
