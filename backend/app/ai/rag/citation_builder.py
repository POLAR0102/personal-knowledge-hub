import logging
import re
from dataclasses import dataclass

from app.ai.vector_store import SearchResult

logger = logging.getLogger(__name__)
SOURCE_PATTERN = re.compile(r"\[来源\s*(\d+)\]")


@dataclass(frozen=True, slots=True)
class Citation:
    source_number: int
    result: SearchResult


def build_citations(
    answer: str,
    source_map: dict[int, SearchResult],
) -> list[Citation]:
    citations: list[Citation] = []
    seen_source_numbers: set[int] = set()

    for match in SOURCE_PATTERN.finditer(answer):
        source_number = int(match.group(1))
        if source_number in seen_source_numbers:
            continue
        seen_source_numbers.add(source_number)

        result = source_map.get(source_number)
        if result is None:
            logger.warning(
                "Chat model returned unknown RAG source number %s",
                source_number,
            )
            continue
        citations.append(Citation(source_number=source_number, result=result))

    return citations
