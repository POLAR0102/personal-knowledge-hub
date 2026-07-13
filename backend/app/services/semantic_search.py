import logging
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.ai.vector_store import SearchResult, VectorStore, VectorStoreError
from app.core.config import get_settings
from app.db.models import User
from app.repositories.knowledge_base import KnowledgeBaseRepository

logger = logging.getLogger(__name__)
MAX_QUERY_LENGTH = 1000


class KnowledgeBaseNotFoundError(Exception):
    pass


class SemanticSearchInputError(Exception):
    pass


class SemanticSearchDatabaseError(Exception):
    pass


class SemanticSearchDependencyError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SemanticSearchResult:
    query: str
    knowledge_base_id: int
    results: list[SearchResult]


def semantic_search(
    db: Session,
    owner: User,
    *,
    knowledge_base_id: int,
    query: str,
    top_k: int | None,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
) -> SemanticSearchResult:
    normalized_query = query.strip()
    if not normalized_query:
        raise SemanticSearchInputError("Query cannot be empty")
    if len(normalized_query) > MAX_QUERY_LENGTH:
        raise SemanticSearchInputError(
            f"Query cannot exceed {MAX_QUERY_LENGTH} characters"
        )

    resolved_top_k = (
        top_k if top_k is not None else get_settings().semantic_search_top_k
    )
    if not 1 <= resolved_top_k <= 20:
        raise SemanticSearchInputError("top_k must be between 1 and 20")

    try:
        knowledge_base = KnowledgeBaseRepository(db).get_owned(
            knowledge_base_id=knowledge_base_id,
            user_id=owner.id,
        )
    except SQLAlchemyError as exc:
        logger.exception("Database error while validating semantic search scope")
        raise SemanticSearchDatabaseError from exc
    if knowledge_base is None:
        raise KnowledgeBaseNotFoundError

    try:
        query_vector = embedding_provider.embed_query(normalized_query)
        results = vector_store.search(
            query_vector,
            owner.id,
            knowledge_base.id,
            resolved_top_k,
        )
    except EmbeddingError as exc:
        logger.warning(
            "Query embedding failed during semantic search with %s",
            type(exc).__name__,
        )
        raise SemanticSearchDependencyError(
            "Unable to generate query embedding"
        ) from exc
    except VectorStoreError as exc:
        logger.warning(
            "Vector store failed during semantic search with %s",
            type(exc).__name__,
        )
        raise SemanticSearchDependencyError("Unable to search vector store") from exc

    return SemanticSearchResult(
        query=normalized_query,
        knowledge_base_id=knowledge_base.id,
        results=results,
    )
