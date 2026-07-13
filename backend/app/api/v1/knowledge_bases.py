from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider
from app.ai.vector_store import VectorStore
from app.api.dependencies import (
    get_current_user,
    get_embedding_provider_dependency,
    get_vector_store_dependency,
)
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.schemas.index_maintenance import (
    KnowledgeBaseReindexItem,
    KnowledgeBaseReindexResponse,
)
from app.services.index_maintenance import (
    IndexMaintenanceDatabaseError,
    KnowledgeBaseNotFoundError as ReindexKnowledgeBaseNotFoundError,
    KnowledgeBaseReindexLimitError,
    reindex_knowledge_base,
)
from app.services.knowledge_base import (
    KnowledgeBaseDatabaseError,
    KnowledgeBaseIndexingInProgressError,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseVectorStoreError,
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base,
    list_knowledge_bases,
    update_knowledge_base,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


def not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge base not found",
    )


def database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Knowledge base operation failed",
    )


@router.post("", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
def create(
    data: KnowledgeBaseCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> KnowledgeBaseRead:
    try:
        knowledge_base = create_knowledge_base(db, current_user, data)
    except KnowledgeBaseDatabaseError as exc:
        raise database_error() from exc
    return KnowledgeBaseRead.model_validate(knowledge_base)


@router.get("", response_model=KnowledgeBaseList)
def list_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> KnowledgeBaseList:
    try:
        items, total = list_knowledge_bases(
            db,
            current_user,
            page=page,
            page_size=page_size,
        )
    except KnowledgeBaseDatabaseError as exc:
        raise database_error() from exc
    return KnowledgeBaseList(
        items=[KnowledgeBaseRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{knowledge_base_id}/reindex",
    response_model=KnowledgeBaseReindexResponse,
)
def reindex(
    knowledge_base_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider_dependency),
    ],
    vector_store: Annotated[VectorStore, Depends(get_vector_store_dependency)],
) -> KnowledgeBaseReindexResponse:
    try:
        result = reindex_knowledge_base(
            db,
            current_user,
            knowledge_base_id,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            document_limit=get_settings().knowledge_base_reindex_limit,
        )
    except ReindexKnowledgeBaseNotFoundError as exc:
        raise not_found_error() from exc
    except KnowledgeBaseReindexLimitError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IndexMaintenanceDatabaseError as exc:
        raise database_error() from exc
    return KnowledgeBaseReindexResponse(
        knowledge_base_id=result.knowledge_base_id,
        total=len(result.items),
        succeeded=result.succeeded,
        failed=result.failed,
        items=[
            KnowledgeBaseReindexItem(
                document_id=item.document_id,
                original_filename=item.original_filename,
                index_status=item.index_status,
                vector_count=item.vector_count,
                error_message=item.error_message,
            )
            for item in result.items
        ],
    )


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseRead)
def get_one(
    knowledge_base_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> KnowledgeBaseRead:
    try:
        knowledge_base = get_knowledge_base(db, current_user, knowledge_base_id)
    except KnowledgeBaseNotFoundError as exc:
        raise not_found_error() from exc
    except KnowledgeBaseDatabaseError as exc:
        raise database_error() from exc
    return KnowledgeBaseRead.model_validate(knowledge_base)


@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseRead)
def update(
    knowledge_base_id: int,
    data: KnowledgeBaseUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> KnowledgeBaseRead:
    try:
        knowledge_base = update_knowledge_base(
            db,
            current_user,
            knowledge_base_id,
            data,
        )
    except KnowledgeBaseNotFoundError as exc:
        raise not_found_error() from exc
    except KnowledgeBaseDatabaseError as exc:
        raise database_error() from exc
    return KnowledgeBaseRead.model_validate(knowledge_base)


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    knowledge_base_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        delete_knowledge_base(db, current_user, knowledge_base_id)
    except KnowledgeBaseNotFoundError as exc:
        raise not_found_error() from exc
    except KnowledgeBaseIndexingInProgressError as exc:
        raise HTTPException(
            status_code=409,
            detail="Knowledge base contains a document that is currently indexing",
        ) from exc
    except KnowledgeBaseVectorStoreError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to delete knowledge base vectors",
        ) from exc
    except KnowledgeBaseDatabaseError as exc:
        raise database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
