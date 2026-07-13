from dataclasses import dataclass

from app.ai.vector_store import SearchResult


@dataclass(frozen=True, slots=True)
class ContextBuildResult:
    content: str
    used_results: list[SearchResult]
    source_map: dict[int, SearchResult]


def build_context(
    results: list[SearchResult],
    *,
    max_characters: int,
) -> ContextBuildResult:
    if max_characters < 1:
        raise ValueError("max_characters must be greater than zero")

    blocks: list[str] = []
    used_results: list[SearchResult] = []
    seen_content: set[str] = set()
    current_length = 0

    for result in results:
        content = result.content.strip()
        if not content or content in seen_content:
            continue

        source_number = len(used_results) + 1
        block = _format_source(source_number, result, content)
        separator_length = 2 if blocks else 0
        if current_length + separator_length + len(block) > max_characters:
            break

        blocks.append(block)
        used_results.append(result)
        seen_content.add(content)
        current_length += separator_length + len(block)

    return ContextBuildResult(
        content="\n\n".join(blocks),
        used_results=used_results,
        source_map={
            source_number: result
            for source_number, result in enumerate(used_results, start=1)
        },
    )


def _format_source(
    source_number: int,
    result: SearchResult,
    content: str,
) -> str:
    page_number = str(result.page_number) if result.page_number is not None else "无"
    section_title = result.section_title or "无"
    return (
        f"[来源 {source_number}]\n"
        f"文件名：{result.filename}\n"
        f"页码：{page_number}\n"
        f"标题：{section_title}\n"
        f"内容：\n{content}"
    )
