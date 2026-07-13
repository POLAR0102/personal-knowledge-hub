import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.vector_store import VectorStore, VectorStoreError, get_vector_store
from app.core.config import get_settings
from app.db.models import Document, DocumentIndexStatus, DocumentStatus, User
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain", "text/x-markdown"},
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}


class DocumentNotFoundError(Exception):
    pass


class KnowledgeBaseNotFoundError(Exception):
    pass


class UnsupportedDocumentTypeError(Exception):
    pass


class EmptyDocumentError(Exception):
    pass


class DocumentTooLargeError(Exception):
    pass


class InvalidFilenameError(Exception):
    pass


class DocumentStorageError(Exception):
    pass


class DocumentDatabaseError(Exception):
    pass


class DocumentIndexingInProgressError(Exception):
    pass


class DocumentVectorStoreError(Exception):
    pass


def _get_owned_knowledge_base_id(
    db: Session,
    owner: User,
    knowledge_base_id: int,
) -> int:
    try:
        knowledge_base = KnowledgeBaseRepository(db).get_owned(
            knowledge_base_id=knowledge_base_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading a knowledge base for documents")
        raise DocumentDatabaseError from exc

    if knowledge_base is None:
        raise KnowledgeBaseNotFoundError
    return knowledge_base.id


def _validate_upload(upload: UploadFile) -> tuple[str, str, str]:
    raw_filename = upload.filename or ""
    original_filename = raw_filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not original_filename or "\x00" in original_filename or len(original_filename) > 255:
        raise InvalidFilenameError

    extension = Path(original_filename).suffix.lower()
    allowed_mime_types = ALLOWED_MIME_TYPES.get(extension)
    if allowed_mime_types is None:
        raise UnsupportedDocumentTypeError

    mime_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if mime_type not in allowed_mime_types:
        raise UnsupportedDocumentTypeError

    return original_filename, extension, mime_type


def _build_storage_path(
    *,
    user_id: int,
    knowledge_base_id: int,
    extension: str,
) -> tuple[Path, str]:
    upload_root = get_settings().upload_dir.expanduser().resolve()
    upload_directory = (upload_root / str(user_id) / str(knowledge_base_id)).resolve()
    if not upload_directory.is_relative_to(upload_root):
        raise DocumentStorageError

    upload_directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{extension}"
    file_path = (upload_directory / stored_filename).resolve()
    if not file_path.is_relative_to(upload_root):
        raise DocumentStorageError
    return file_path, stored_filename


async def _save_upload(upload: UploadFile, file_path: Path) -> int:
    max_bytes = get_settings().max_upload_size_mb * 1024 * 1024
    temporary_path = file_path.with_name(f"{file_path.name}.part")
    file_size = 0

    try:
        with temporary_path.open("xb") as output:
            while chunk := await upload.read(CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > max_bytes:
                    raise DocumentTooLargeError
                output.write(chunk)
        if file_size == 0:
            raise EmptyDocumentError
        temporary_path.replace(file_path)
    except (DocumentTooLargeError, EmptyDocumentError):
        temporary_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        logger.exception("Unable to save uploaded document")
        raise DocumentStorageError from exc

    return file_size


async def upload_document(
    db: Session,
    owner: User,
    knowledge_base_id: int,
    upload: UploadFile,
) -> Document:
    owned_knowledge_base_id = _get_owned_knowledge_base_id(
        db,
        owner,
        knowledge_base_id,
    )
    original_filename, extension, mime_type = _validate_upload(upload)

    try:
        file_path, stored_filename = _build_storage_path(
            user_id=owner.id,
            knowledge_base_id=owned_knowledge_base_id,
            extension=extension,
        )
    except OSError as exc:
        logger.exception("Unable to prepare document upload directory")
        raise DocumentStorageError from exc

    file_size = await _save_upload(upload, file_path)
    repository = DocumentRepository(db)
    try:
        return repository.create(
            user_id=owner.id,
            knowledge_base_id=owned_knowledge_base_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=extension.lstrip("."),
            mime_type=mime_type,
            file_size=file_size,
            file_path=str(file_path),
        )
    except SQLAlchemyError as exc:
        repository.rollback()
        file_path.unlink(missing_ok=True)
        logger.exception("Database error while creating a document")
        raise DocumentDatabaseError from exc


def list_documents(
    db: Session,
    owner: User,
    knowledge_base_id: int,
    *,
    page: int,
    page_size: int,
    status: DocumentStatus | None,
) -> tuple[list[tuple[Document, int]], int]:
    owned_knowledge_base_id = _get_owned_knowledge_base_id(
        db,
        owner,
        knowledge_base_id,
    )
    repository = DocumentRepository(db)
    try:
        items = repository.list_owned_in_knowledge_base(
            user_id=owner.id,
            knowledge_base_id=owned_knowledge_base_id,
            offset=(page - 1) * page_size,
            limit=page_size,
            status=status,
        )
        total = repository.count_owned_in_knowledge_base(
            user_id=owner.id,
            knowledge_base_id=owned_knowledge_base_id,
            status=status,
        )
        return items, total
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing documents")
        raise DocumentDatabaseError from exc


def get_document(db: Session, owner: User, document_id: int) -> Document:
    repository = DocumentRepository(db)
    try:
        document = repository.get_owned(document_id=document_id, user_id=owner.id)
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading a document")
        raise DocumentDatabaseError from exc

    if document is None:
        raise DocumentNotFoundError
    return document


def count_document_chunks(db: Session, owner: User, document_id: int) -> int:
    get_document(db, owner, document_id)
    try:
        return DocumentChunkRepository(db).count_for_document(
            document_id=document_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while counting document chunks")
        raise DocumentDatabaseError from exc


def count_documents(db: Session, owner: User) -> int:
    try:
        return DocumentRepository(db).count_owned(user_id=owner.id)
    except SQLAlchemyError as exc:
        logger.exception("Database error while counting documents")
        raise DocumentDatabaseError from exc


def delete_document(
    db: Session,
    owner: User,
    document_id: int,
    vector_store: VectorStore | None = None,
) -> None:
    repository = DocumentRepository(db)
    document = get_document(db, owner, document_id)
    if document.index_status == DocumentIndexStatus.INDEXING:
        raise DocumentIndexingInProgressError
    if document.index_status != DocumentIndexStatus.NOT_INDEXED:
        try:
            (vector_store or get_vector_store()).delete_by_document(
                document.id,
                owner.id,
            )
        except VectorStoreError as exc:
            logger.warning(
                "Unable to delete vectors before deleting document %s",
                document_id,
            )
            raise DocumentVectorStoreError from exc

    upload_root = get_settings().upload_dir.expanduser().resolve()
    file_path = Path(document.file_path).resolve()
    if not file_path.is_relative_to(upload_root):
        raise DocumentStorageError

    try:
        file_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.exception("Unable to delete document file")
        raise DocumentStorageError from exc

    try:
        repository.delete(document)
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while deleting a document")
        raise DocumentDatabaseError from exc
