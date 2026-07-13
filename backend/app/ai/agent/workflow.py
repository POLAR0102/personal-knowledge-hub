from app.ai.rag import Citation, ContextBuildResult, build_citations, build_context
from app.ai.vector_store import SearchResult


def organize_context(
    results: list[SearchResult],
    *,
    max_characters: int,
) -> ContextBuildResult:
    return build_context(results, max_characters=max_characters)


def build_agent_citations(
    result_content: str,
    source_map: dict[int, SearchResult],
) -> list[Citation]:
    return build_citations(result_content, source_map)
