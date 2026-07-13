from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    RAGProviderLoader,
    get_conversation_rag_provider_loader_dependency,
    get_current_user,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationRead,
    MessageCreate,
    MessagePairResponse,
    MessageRead,
)
from app.services.conversation import (
    ConversationConflictError,
    ConversationDatabaseError,
    ConversationNotFoundError,
    ConversationRAGDependencyError,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    send_message,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation not found",
    )


def database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Conversation operation failed",
    )


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create(
    data: ConversationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationRead:
    try:
        conversation = create_conversation(db, current_user, data)
    except ConversationNotFoundError as exc:
        raise not_found_error() from exc
    except ConversationDatabaseError as exc:
        raise database_error() from exc
    return ConversationRead.model_validate(conversation)


@router.get("", response_model=ConversationList)
def list_all(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ConversationList:
    try:
        items, total = list_conversations(
            db,
            current_user,
            page=page,
            page_size=page_size,
        )
    except ConversationDatabaseError as exc:
        raise database_error() from exc
    return ConversationList(
        items=[ConversationRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_one(
    conversation_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationDetail:
    try:
        conversation = get_conversation(db, current_user, conversation_id)
    except ConversationNotFoundError as exc:
        raise not_found_error() from exc
    except ConversationDatabaseError as exc:
        raise database_error() from exc
    return ConversationDetail.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    conversation_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        delete_conversation(db, current_user, conversation_id)
    except ConversationNotFoundError as exc:
        raise not_found_error() from exc
    except ConversationDatabaseError as exc:
        raise database_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessagePairResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: int,
    data: MessageCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    provider_loader: Annotated[
        RAGProviderLoader,
        Depends(get_conversation_rag_provider_loader_dependency),
    ],
) -> MessagePairResponse:
    try:
        result = send_message(
            db,
            current_user,
            conversation_id,
            data,
            provider_loader=provider_loader,
        )
    except ConversationNotFoundError as exc:
        raise not_found_error() from exc
    except ConversationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ConversationRAGDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ConversationDatabaseError as exc:
        raise database_error() from exc
    return MessagePairResponse(
        user_message=MessageRead.model_validate(result.user_message),
        assistant_message=MessageRead.model_validate(result.assistant_message),
    )
