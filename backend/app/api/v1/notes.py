from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.note import NoteCreate, NoteList, NoteRead, NoteUpdate
from app.services.note import (
    NoteDatabaseError,
    NoteNotFoundError,
    create_note,
    delete_note,
    get_note,
    list_notes,
    update_note,
)

router = APIRouter(prefix="/notes", tags=["notes"])


def not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Note not found",
    )


def database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Note operation failed",
    )


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create(
    data: NoteCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteRead:
    try:
        note = create_note(db, current_user, data)
    except NoteNotFoundError as exc:
        raise not_found_error() from exc
    except NoteDatabaseError as exc:
        raise database_error() from exc
    return NoteRead.model_validate(note)


@router.get("", response_model=NoteList)
def list_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    knowledge_base_id: Annotated[int | None, Query(gt=0)] = None,
) -> NoteList:
    try:
        items, total = list_notes(
            db,
            current_user,
            page=page,
            page_size=page_size,
            knowledge_base_id=knowledge_base_id,
        )
    except NoteNotFoundError as exc:
        raise not_found_error() from exc
    except NoteDatabaseError as exc:
        raise database_error() from exc
    return NoteList(
        items=[NoteRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{note_id}", response_model=NoteRead)
def get_one(
    note_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteRead:
    try:
        note = get_note(db, current_user, note_id)
    except NoteNotFoundError as exc:
        raise not_found_error() from exc
    except NoteDatabaseError as exc:
        raise database_error() from exc
    return NoteRead.model_validate(note)


@router.put("/{note_id}", response_model=NoteRead)
def update(
    note_id: int,
    data: NoteUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteRead:
    try:
        note = update_note(db, current_user, note_id, data)
    except NoteNotFoundError as exc:
        raise not_found_error() from exc
    except NoteDatabaseError as exc:
        raise database_error() from exc
    return NoteRead.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    note_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        delete_note(db, current_user, note_id)
    except NoteNotFoundError as exc:
        raise not_found_error() from exc
    except NoteDatabaseError as exc:
        raise database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
