from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider
from app.ai.llm import ChatModelProvider
from app.ai.vector_store import VectorStore
from app.api.dependencies import (
    get_chat_model_provider_dependency,
    get_current_user,
    get_embedding_provider_dependency,
    get_vector_store_dependency,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.rag import (
    RAGCitationRead,
    RAGQueryRequest,
    RAGQueryResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultRead,
)
from app.services.rag_query import (
    RAGQueryDatabaseError,
    RAGQueryDependencyError,
    RAGQueryInputError,
    answer_question,
)
from app.services.semantic_search import (
    KnowledgeBaseNotFoundError,
    SemanticSearchDatabaseError,
    SemanticSearchDependencyError,
    SemanticSearchInputError,
    semantic_search,
)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RAGQueryResponse)
def query(
    data: RAGQueryRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider_dependency),
    ],
    vector_store: Annotated[VectorStore, Depends(get_vector_store_dependency)],
    chat_model: Annotated[
        ChatModelProvider,
        Depends(get_chat_model_provider_dependency),
    ],
) -> RAGQueryResponse:
    try:
        result = answer_question(
            db,
            current_user,
            knowledge_base_id=data.knowledge_base_id,
            question=data.question,
            top_k=data.top_k,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            chat_model=chat_model,
        )
    except KnowledgeBaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        ) from exc
    except RAGQueryInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RAGQueryDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except RAGQueryDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG query operation failed",
        ) from exc

    return RAGQueryResponse(
        answer=result.answer,
        knowledge_base_id=result.knowledge_base_id,
        citations=[
            RAGCitationRead(
                source_number=item.source_number,
                chunk_id=item.result.chunk_id,
                document_id=item.result.document_id,
                filename=item.result.filename,
                content=item.result.content,
                chunk_index=item.result.chunk_index,
                page_number=item.result.page_number,
                section_title=item.result.section_title,
                distance=item.result.distance,
            )
            for item in result.citations
        ],
        retrieval_count=result.retrieval_count,
        model=result.model,
    )


@router.post("/search", response_model=SemanticSearchResponse)
def search(
    data: SemanticSearchRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider_dependency),
    ],
    vector_store: Annotated[VectorStore, Depends(get_vector_store_dependency)],
) -> SemanticSearchResponse:
    try:
        result = semantic_search(
            db,
            current_user,
            knowledge_base_id=data.knowledge_base_id,
            query=data.query,
            top_k=data.top_k,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )
    except KnowledgeBaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        ) from exc
    except SemanticSearchInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SemanticSearchDependencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SemanticSearchDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Semantic search operation failed",
        ) from exc

    return SemanticSearchResponse(
        query=result.query,
        knowledge_base_id=result.knowledge_base_id,
        results=[
            SemanticSearchResultRead(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                filename=item.filename,
                content=item.content,
                chunk_index=item.chunk_index,
                page_number=item.page_number,
                section_title=item.section_title,
                distance=item.distance,
            )
            for item in result.results
        ],
    )
