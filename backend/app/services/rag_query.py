import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider
from app.ai.llm import ChatModelError, ChatModelProvider
from app.ai.prompts import build_rag_messages
from app.ai.rag import Citation, build_citations, build_context
from app.ai.vector_store import VectorStore
from app.core.config import get_settings
from app.db.models import User
from app.services.semantic_search import (
    KnowledgeBaseNotFoundError,
    SemanticSearchDatabaseError,
    SemanticSearchDependencyError,
    SemanticSearchInputError,
    semantic_search,
)

logger = logging.getLogger(__name__)
MAX_QUESTION_LENGTH = 1000
NO_ANSWER_MESSAGE = "根据当前知识库内容，无法确定该问题的答案。"


class RAGQueryInputError(Exception):
    pass


class RAGQueryDependencyError(Exception):
    pass


class RAGQueryDatabaseError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class RAGQueryResult:
    answer: str
    knowledge_base_id: int
    citations: list[Citation]
    retrieval_count: int
    model: str


def answer_question(
    db: Session,
    owner: User,
    *,
    knowledge_base_id: int,
    question: str,
    top_k: int,
    embedding_provider: EmbeddingProvider,
    vector_store: VectorStore,
    chat_model: ChatModelProvider,
) -> RAGQueryResult:
    normalized_question = question.strip()
    if not normalized_question:
        raise RAGQueryInputError("Question cannot be empty")
    if len(normalized_question) > MAX_QUESTION_LENGTH:
        raise RAGQueryInputError(
            f"Question cannot exceed {MAX_QUESTION_LENGTH} characters"
        )
    if not 1 <= top_k <= 10:
        raise RAGQueryInputError("top_k must be between 1 and 10")

    try:
        search_result = semantic_search(
            db,
            owner,
            knowledge_base_id=knowledge_base_id,
            query=normalized_question,
            top_k=top_k,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )
    except KnowledgeBaseNotFoundError:
        raise
    except SemanticSearchInputError as exc:
        raise RAGQueryInputError(str(exc)) from exc
    except SemanticSearchDependencyError as exc:
        raise RAGQueryDependencyError(str(exc)) from exc
    except SemanticSearchDatabaseError as exc:
        raise RAGQueryDatabaseError from exc

    settings = get_settings()
    context = build_context(
        search_result.results,
        max_characters=settings.rag_max_context_chars,
    )
    if not context.used_results:
        return RAGQueryResult(
            answer=NO_ANSWER_MESSAGE,
            knowledge_base_id=search_result.knowledge_base_id,
            citations=[],
            retrieval_count=0,
            model=chat_model.model_name,
        )

    messages = build_rag_messages(
        question=normalized_question,
        context=context.content,
    )
    try:
        generated = chat_model.generate(
            messages,
            temperature=settings.rag_temperature,
            max_tokens=settings.rag_max_tokens,
        )
    except ChatModelError as exc:
        logger.warning(
            "Chat model failed during RAG query with %s",
            type(exc).__name__,
        )
        raise RAGQueryDependencyError("Unable to generate RAG answer") from exc

    return RAGQueryResult(
        answer=generated.content,
        knowledge_base_id=search_result.knowledge_base_id,
        citations=build_citations(generated.content, context.source_map),
        retrieval_count=len(context.used_results),
        model=generated.model,
    )
