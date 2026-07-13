from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
    get_embedding_provider,
)
from app.ai.llm import (
    ChatModelConfigurationError,
    ChatModelProvider,
    get_chat_model_provider,
)
from app.ai.vector_store import (
    VectorStore,
    VectorStoreConfigurationError,
    get_vector_store,
)
from app.core.security import InvalidTokenError, decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_embedding_provider_dependency() -> EmbeddingProvider:
    try:
        return get_embedding_provider()
    except EmbeddingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service is not configured",
        ) from exc


def get_vector_store_dependency() -> VectorStore:
    try:
        return get_vector_store()
    except VectorStoreConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not available",
        ) from exc


def get_chat_model_provider_dependency() -> ChatModelProvider:
    try:
        return get_chat_model_provider()
    except ChatModelConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat model service is not configured",
        ) from exc


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(token)
        user = UserRepository(db).get_by_id(user_id)
    except InvalidTokenError as exc:
        raise credentials_error from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load current user",
        ) from exc

    if user is None or not user.is_active:
        raise credentials_error

    return user
