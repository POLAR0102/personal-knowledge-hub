from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider
from app.ai.vector_store import VectorStore
from app.api.dependencies import (
    get_current_user,
    get_embedding_provider_dependency,
    get_vector_store_dependency,
)
from app.core.config import get_settings
from app.db.models import DocumentStatus, User
from app.db.session import get_db
from app.schemas.document import (
    DocumentFavoriteUpdate,
    DocumentList,
    DocumentIndexResult,
    DocumentIndexStatusRead,
    DocumentProcessResult,
    DocumentRead,
    DocumentStats,
)
from app.schemas.document_chunk import DocumentChunkList, DocumentChunkRead
from app.schemas.index_maintenance import DocumentIndexHealthRead
from app.services.document import (
    DocumentDatabaseError,
    DocumentIndexingInProgressError,
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidFilenameError,
    KnowledgeBaseNotFoundError,
    UnsupportedDocumentTypeError,
    DocumentVectorStoreError,
    DocumentTagNotFoundError,
    add_document_tag,
    count_document_chunks,
    count_documents,
    delete_document,
    get_document,
    list_documents,
    list_all_documents,
    remove_document_tag,
    set_document_favorite,
    upload_document,
)
from app.services.document_processing import (
    DocumentAlreadyIndexingError as ProcessingDocumentAlreadyIndexingError,
    DocumentAlreadyProcessingError,
    DocumentNotFoundError as ProcessingDocumentNotFoundError,
    DocumentProcessingDatabaseError,
    DocumentProcessingFailedError,
    list_document_chunks,
    process_document,
)
from app.services.document_indexing import (
    DocumentAlreadyIndexingError,
    DocumentIndexingDatabaseError,
    DocumentIndexingDependencyError,
    DocumentIndexingFailedError,
    DocumentNotFoundError as IndexingDocumentNotFoundError,
    DocumentNotReadyForIndexError,
    get_document_index_status,
    index_document,
)
from app.services.index_maintenance import (
    IndexMaintenanceDatabaseError,
    IndexMaintenanceDependencyError,
    get_document_index_health,
)

router = APIRouter(tags=["documents"])


def document_not_found_error() -> HTTPException:
    return HTTPException(status_code=404, detail="Document not found")


def knowledge_base_not_found_error() -> HTTPException:
    return HTTPException(status_code=404, detail="Knowledge base not found")


def database_error() -> HTTPException:
    return HTTPException(status_code=500, detail="Document operation failed")


def tag_not_found_error() -> HTTPException:
    return HTTPException(status_code=404, detail="Tag not found")


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload(
    knowledge_base_id: int,
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    try:
        document = await upload_document(db, current_user, knowledge_base_id, file)
    except KnowledgeBaseNotFoundError as exc:
        raise knowledge_base_not_found_error() from exc
    except InvalidFilenameError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=400, detail="File is empty") from exc
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too large",
        ) from exc
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type or MIME type",
        ) from exc
    except DocumentStorageError as exc:
        raise HTTPException(status_code=500, detail="Document storage operation failed") from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentRead.model_validate(document)


@router.get(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentList,
)
def list_all(
    knowledge_base_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
) -> DocumentList:
    try:
        items, total = list_documents(
            db,
            current_user,
            knowledge_base_id,
            page=page,
            page_size=page_size,
            status=document_status,
        )
    except KnowledgeBaseNotFoundError as exc:
        raise knowledge_base_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentList(
        items=[
            DocumentRead.model_validate(document).model_copy(
                update={"chunk_count": chunk_count}
            )
            for document, chunk_count in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents", response_model=DocumentList)
def list_across_knowledge_bases(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    filename: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    knowledge_base_id: Annotated[int | None, Query(gt=0)] = None,
    tag_id: Annotated[int | None, Query(gt=0)] = None,
    is_favorite: bool | None = None,
) -> DocumentList:
    try:
        items, total = list_all_documents(
            db,
            current_user,
            page=page,
            page_size=page_size,
            filename=filename,
            status=document_status,
            knowledge_base_id=knowledge_base_id,
            tag_id=tag_id,
            is_favorite=is_favorite,
        )
    except KnowledgeBaseNotFoundError as exc:
        raise knowledge_base_not_found_error() from exc
    except DocumentTagNotFoundError as exc:
        raise tag_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentList(
        items=[
            DocumentRead.model_validate(document).model_copy(
                update={"chunk_count": chunk_count}
            )
            for document, chunk_count in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/favorites", response_model=DocumentList)
def list_favorites(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    filename: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    knowledge_base_id: Annotated[int | None, Query(gt=0)] = None,
    tag_id: Annotated[int | None, Query(gt=0)] = None,
) -> DocumentList:
    try:
        items, total = list_all_documents(
            db,
            current_user,
            page=page,
            page_size=page_size,
            filename=filename,
            status=document_status,
            knowledge_base_id=knowledge_base_id,
            tag_id=tag_id,
            is_favorite=True,
        )
    except KnowledgeBaseNotFoundError as exc:
        raise knowledge_base_not_found_error() from exc
    except DocumentTagNotFoundError as exc:
        raise tag_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentList(
        items=[
            DocumentRead.model_validate(document).model_copy(
                update={"chunk_count": chunk_count}
            )
            for document, chunk_count in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/stats", response_model=DocumentStats)
def stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentStats:
    try:
        total = count_documents(db, current_user)
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentStats(total=total)


@router.put("/documents/{document_id}/favorite", response_model=DocumentRead)
def set_favorite(
    document_id: int,
    data: DocumentFavoriteUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    try:
        document = set_document_favorite(
            db,
            current_user,
            document_id,
            is_favorite=data.is_favorite,
        )
        chunk_count = count_document_chunks(db, current_user, document.id)
    except DocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentRead.model_validate(document).model_copy(
        update={"chunk_count": chunk_count}
    )


@router.post("/documents/{document_id}/tags/{tag_id}", response_model=DocumentRead)
def add_tag(
    document_id: int,
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    try:
        document = add_document_tag(
            db,
            current_user,
            document_id,
            tag_id,
        )
        chunk_count = count_document_chunks(db, current_user, document.id)
    except DocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentTagNotFoundError as exc:
        raise tag_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentRead.model_validate(document).model_copy(
        update={"chunk_count": chunk_count}
    )


@router.delete(
    "/documents/{document_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_tag(
    document_id: int,
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        remove_document_tag(db, current_user, document_id, tag_id)
    except DocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentTagNotFoundError as exc:
        raise tag_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documents/{document_id}/process",
    response_model=DocumentProcessResult,
)
def process(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentProcessResult:
    try:
        result = process_document(db, current_user, document_id)
    except ProcessingDocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentAlreadyProcessingError as exc:
        raise HTTPException(status_code=409, detail="Document is already processing") from exc
    except ProcessingDocumentAlreadyIndexingError as exc:
        raise HTTPException(status_code=409, detail="Document is currently indexing") from exc
    except DocumentProcessingFailedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DocumentProcessingDatabaseError as exc:
        raise database_error() from exc
    return DocumentProcessResult(
        document_id=result.document.id,
        status=result.document.status,
        chunk_count=result.chunk_count,
        updated_at=result.document.updated_at,
    )


@router.post(
    "/documents/{document_id}/index",
    response_model=DocumentIndexResult,
)
def index(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider_dependency),
    ],
    vector_store: Annotated[VectorStore, Depends(get_vector_store_dependency)],
) -> DocumentIndexResult:
    try:
        result = index_document(
            db,
            current_user,
            document_id,
            embedding_provider,
            vector_store,
        )
    except IndexingDocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentAlreadyIndexingError as exc:
        raise HTTPException(status_code=409, detail="Document is already indexing") from exc
    except DocumentNotReadyForIndexError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DocumentIndexingFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DocumentIndexingDatabaseError as exc:
        raise database_error() from exc
    return DocumentIndexResult(
        document_id=result.document.id,
        index_status=result.document.index_status,
        chunk_count=result.chunk_count,
        vector_count=result.vector_count,
        embedding_model=result.document.embedding_model or "",
        indexed_at=result.document.indexed_at,
    )


@router.get(
    "/documents/{document_id}/index-status",
    response_model=DocumentIndexStatusRead,
)
def index_status(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store_dependency)],
) -> DocumentIndexStatusRead:
    try:
        result = get_document_index_status(
            db,
            current_user,
            document_id,
            vector_store,
        )
    except IndexingDocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentIndexingDependencyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Vector store is not available",
        ) from exc
    except DocumentIndexingDatabaseError as exc:
        raise database_error() from exc
    return DocumentIndexStatusRead(
        document_id=result.document.id,
        processing_status=result.document.status,
        index_status=result.document.index_status,
        chunk_count=result.chunk_count,
        vector_count=result.vector_count,
        embedding_model=result.document.embedding_model,
        indexed_at=result.document.indexed_at,
        index_error_message=result.document.index_error_message,
    )


@router.get(
    "/documents/{document_id}/index-health",
    response_model=DocumentIndexHealthRead,
)
def index_health(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store_dependency)],
) -> DocumentIndexHealthRead:
    try:
        result = get_document_index_health(
            db,
            current_user,
            document_id,
            vector_store,
            get_settings().embedding_model,
        )
    except IndexingDocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except IndexMaintenanceDependencyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Vector store is not available",
        ) from exc
    except IndexMaintenanceDatabaseError as exc:
        raise database_error() from exc
    return DocumentIndexHealthRead(
        document_id=result.document.id,
        index_status=result.document.index_status,
        health_status=result.health_status,
        chunk_count=result.chunk_count,
        vector_count=result.vector_count,
        embedding_model=result.document.embedding_model,
        current_embedding_model=result.current_embedding_model,
        indexed_at=result.document.indexed_at,
        index_error_message=result.document.index_error_message,
    )


@router.get(
    "/documents/{document_id}/chunks",
    response_model=DocumentChunkList,
)
def list_chunks(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentChunkList:
    try:
        items, total = list_document_chunks(
            db,
            current_user,
            document_id,
            page=page,
            page_size=page_size,
        )
    except ProcessingDocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentProcessingDatabaseError as exc:
        raise database_error() from exc
    return DocumentChunkList(
        items=[DocumentChunkRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_one(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    try:
        document = get_document(db, current_user, document_id)
        chunk_count = count_document_chunks(db, current_user, document.id)
    except DocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentRead.model_validate(document).model_copy(
        update={"chunk_count": chunk_count}
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        delete_document(db, current_user, document_id)
    except DocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentStorageError as exc:
        raise HTTPException(status_code=500, detail="Document storage operation failed") from exc
    except DocumentIndexingInProgressError as exc:
        raise HTTPException(status_code=409, detail="Document is currently indexing") from exc
    except DocumentVectorStoreError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to delete document vectors",
        ) from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
