from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
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
