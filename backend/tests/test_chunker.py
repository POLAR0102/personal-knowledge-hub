from app.ai.document_processing.chunker import Chunker
from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection


def parsed_document(
    content: str,
    *,
    page_number: int | None = None,
    section_title: str | None = None,
) -> ParsedDocument:
    return ParsedDocument(
        sections=[
            ParsedSection(
                content=content,
                section_index=0,
                page_number=page_number,
                section_title=section_title,
            )
        ]
    )


def test_short_text_creates_one_chunk() -> None:
    chunks = Chunker().split(parsed_document("一段简短文本"))
    assert len(chunks) == 1
    assert chunks[0].content == "一段简短文本"
    assert chunks[0].chunk_index == 0


def test_long_text_creates_multiple_chunks() -> None:
    chunks = Chunker(chunk_size=80, chunk_overlap=10, minimum_chunk_size=20).split(
        parsed_document("这是一个较长段落。" * 30)
    )
    assert len(chunks) > 1
    assert all(chunk.character_count <= 80 for chunk in chunks)


def test_chunker_prefers_chinese_sentence_boundaries() -> None:
    chunks = Chunker(chunk_size=14, chunk_overlap=0, minimum_chunk_size=4).split(
        parsed_document("第一句话。第二句话。第三句话。第四句话。")
    )
    assert len(chunks) > 1
    assert all(chunk.content.endswith("。") for chunk in chunks)


def test_chunker_prefers_english_sentence_boundaries() -> None:
    chunks = Chunker(chunk_size=25, chunk_overlap=0, minimum_chunk_size=5).split(
        parsed_document("First sentence. Second sentence. Third sentence.")
    )
    assert len(chunks) > 1
    assert chunks[0].content.endswith(".")


def test_chunker_preserves_markdown_section_title() -> None:
    chunks = Chunker().split(
        parsed_document("# 技术栈\nFastAPI 与 React", section_title="技术栈")
    )
    assert chunks[0].section_title == "技术栈"


def test_chunker_preserves_pdf_page_number() -> None:
    chunks = Chunker().split(parsed_document("PDF 页面内容", page_number=3))
    assert chunks[0].page_number == 3


def test_chunk_overlap_is_applied() -> None:
    content = "abcdefghijklmnopqrstuvwxyz" * 5
    chunks = Chunker(chunk_size=50, chunk_overlap=10, minimum_chunk_size=10).split(
        parsed_document(content)
    )
    assert chunks[0].content[-10:] == chunks[1].content[:10]


def test_chunker_does_not_create_blank_chunks() -> None:
    document = ParsedDocument(
        sections=[
            ParsedSection(content="   ", section_index=0),
            ParsedSection(content="有效内容", section_index=1),
        ]
    )
    chunks = Chunker().split(document)
    assert [chunk.content for chunk in chunks] == ["有效内容"]


def test_oversized_sentence_falls_back_to_character_split() -> None:
    chunks = Chunker(chunk_size=40, chunk_overlap=5, minimum_chunk_size=10).split(
        parsed_document("A" * 130)
    )
    assert len(chunks) > 1
    assert all(chunk.character_count <= 40 for chunk in chunks)


def test_small_final_chunk_is_merged_by_adjusting_split_position() -> None:
    chunks = Chunker(chunk_size=50, chunk_overlap=0, minimum_chunk_size=20).split(
        parsed_document("x" * 105)
    )
    assert all(chunk.character_count >= 20 for chunk in chunks)
    assert "".join(chunk.content for chunk in chunks) == "x" * 105


def test_content_hash_is_stable() -> None:
    document = parsed_document("稳定的内容哈希")
    first = Chunker().split(document)[0]
    second = Chunker().split(document)[0]
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64


def test_invalid_chunker_settings_are_rejected() -> None:
    for settings in (
        {"chunk_size": 0},
        {"chunk_size": 10, "chunk_overlap": 10},
        {"chunk_size": 10, "minimum_chunk_size": 11},
    ):
        try:
            Chunker(**settings)
        except ValueError:
            continue
        raise AssertionError("invalid settings must raise ValueError")
