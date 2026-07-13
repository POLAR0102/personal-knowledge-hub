from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    RAGProviderLoader,
    get_conversation_rag_provider_loader_dependency,
    get_current_user,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.agent_task import AgentTaskCreate, AgentTaskList, AgentTaskRead
from app.schemas.note import NoteRead
from app.services.agent_task import (
    AgentTaskConflictError,
    AgentTaskDatabaseError,
    AgentTaskNotFoundError,
    create_agent_task,
    get_agent_task,
    list_agent_tasks,
    retry_agent_task,
)
from app.services.note import (
    NoteConflictError,
    NoteDatabaseError,
    NoteNotFoundError,
    save_agent_task_as_note,
)

router = APIRouter(prefix="/agent/tasks", tags=["agent"])


def _not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Agent task not found",
    )


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Agent task operation failed",
    )


@router.post("", response_model=AgentTaskRead, status_code=status.HTTP_201_CREATED)
def create(
    data: AgentTaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    provider_loader: Annotated[
        RAGProviderLoader,
        Depends(get_conversation_rag_provider_loader_dependency),
    ],
) -> AgentTaskRead:
    try:
        task = create_agent_task(
            db,
            current_user,
            data,
            provider_loader=provider_loader,
        )
    except AgentTaskNotFoundError as exc:
        raise _not_found_error() from exc
    except AgentTaskConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except AgentTaskDatabaseError as exc:
        raise _database_error() from exc
    return AgentTaskRead.model_validate(task)


@router.get("", response_model=AgentTaskList)
def list_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    knowledge_base_id: Annotated[int | None, Query(gt=0)] = None,
) -> AgentTaskList:
    try:
        items, total = list_agent_tasks(
            db,
            current_user,
            page=page,
            page_size=page_size,
            knowledge_base_id=knowledge_base_id,
        )
    except AgentTaskNotFoundError as exc:
        raise _not_found_error() from exc
    except AgentTaskDatabaseError as exc:
        raise _database_error() from exc
    return AgentTaskList(
        items=[AgentTaskRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=AgentTaskRead)
def get_one(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTaskRead:
    try:
        task = get_agent_task(db, current_user, task_id)
    except AgentTaskNotFoundError as exc:
        raise _not_found_error() from exc
    except AgentTaskDatabaseError as exc:
        raise _database_error() from exc
    return AgentTaskRead.model_validate(task)


@router.post("/{task_id}/retry", response_model=AgentTaskRead)
def retry(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    provider_loader: Annotated[
        RAGProviderLoader,
        Depends(get_conversation_rag_provider_loader_dependency),
    ],
) -> AgentTaskRead:
    try:
        task = retry_agent_task(
            db,
            current_user,
            task_id,
            provider_loader=provider_loader,
        )
    except AgentTaskNotFoundError as exc:
        raise _not_found_error() from exc
    except AgentTaskConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except AgentTaskDatabaseError as exc:
        raise _database_error() from exc
    return AgentTaskRead.model_validate(task)


@router.post(
    "/{task_id}/save-note",
    response_model=NoteRead,
)
def save_note(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> NoteRead:
    try:
        note = save_agent_task_as_note(db, current_user, task_id)
    except NoteNotFoundError as exc:
        raise _not_found_error() from exc
    except NoteConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only completed Agent tasks can be saved as a note",
        ) from exc
    except NoteDatabaseError as exc:
        raise _database_error() from exc
    return NoteRead.model_validate(note)
