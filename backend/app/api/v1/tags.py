from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.tag import TagCreate, TagList, TagRead, TagUpdate
from app.services.tag import (
    TagConflictError,
    TagDatabaseError,
    TagNotFoundError,
    create_tag,
    delete_tag,
    get_tag,
    list_tags,
    update_tag,
)

router = APIRouter(prefix="/tags", tags=["tags"])


def _not_found_error() -> HTTPException:
    return HTTPException(status_code=404, detail="Tag not found")


def _database_error() -> HTTPException:
    return HTTPException(status_code=500, detail="Tag operation failed")


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create(
    data: TagCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TagRead:
    try:
        tag = create_tag(db, current_user, data)
    except TagConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TagDatabaseError as exc:
        raise _database_error() from exc
    return TagRead.model_validate(tag)


@router.get("", response_model=TagList)
def list_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TagList:
    try:
        items, total = list_tags(
            db,
            current_user,
            page=page,
            page_size=page_size,
        )
    except TagDatabaseError as exc:
        raise _database_error() from exc
    return TagList(
        items=[TagRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{tag_id}", response_model=TagRead)
def get_one(
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TagRead:
    try:
        tag = get_tag(db, current_user, tag_id)
    except TagNotFoundError as exc:
        raise _not_found_error() from exc
    except TagDatabaseError as exc:
        raise _database_error() from exc
    return TagRead.model_validate(tag)


@router.put("/{tag_id}", response_model=TagRead)
def update(
    tag_id: int,
    data: TagUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TagRead:
    try:
        tag = update_tag(db, current_user, tag_id, data)
    except TagNotFoundError as exc:
        raise _not_found_error() from exc
    except TagConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TagDatabaseError as exc:
        raise _database_error() from exc
    return TagRead.model_validate(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        delete_tag(db, current_user, tag_id)
    except TagNotFoundError as exc:
        raise _not_found_error() from exc
    except TagDatabaseError as exc:
        raise _database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
