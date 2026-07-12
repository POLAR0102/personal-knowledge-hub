from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import DocumentStatus, User
from app.db.session import get_db
from app.schemas.document import DocumentList, DocumentRead, DocumentStats
from app.services.document import (
    DocumentDatabaseError,
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidFilenameError,
    KnowledgeBaseNotFoundError,
    UnsupportedDocumentTypeError,
    count_documents,
    delete_document,
    get_document,
    list_documents,
    upload_document,
)

router = APIRouter(tags=["documents"])


def document_not_found_error() -> HTTPException:
    return HTTPException(status_code=404, detail="Document not found")


def knowledge_base_not_found_error() -> HTTPException:
    return HTTPException(status_code=404, detail="Knowledge base not found")


def database_error() -> HTTPException:
    return HTTPException(status_code=500, detail="Document operation failed")


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
        items=[DocumentRead.model_validate(item) for item in items],
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


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_one(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    try:
        document = get_document(db, current_user, document_id)
    except DocumentNotFoundError as exc:
        raise document_not_found_error() from exc
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return DocumentRead.model_validate(document)


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
    except DocumentDatabaseError as exc:
        raise database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
