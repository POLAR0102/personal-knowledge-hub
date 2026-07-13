from pathlib import Path

from app.ai.document_processing.cleaners import clean_parsed_document, clean_text
from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection
from app.ai.document_processing.registry import parse_document


def test_clean_text_normalizes_windows_and_legacy_newlines() -> None:
    assert clean_text("第一行\r\n第二行\r第三行") == "第一行\n第二行\n第三行"


def test_clean_text_limits_consecutive_blank_lines() -> None:
    assert clean_text("第一段\n\n\n\n\n第二段") == "第一段\n\n\n第二段"


def test_clean_text_collapses_spaces_in_normal_paragraphs() -> None:
    assert clean_text("  hello     world\t test  ") == "hello world test"


def test_clean_text_preserves_chinese_punctuation_and_numbers() -> None:
    text = "项目编号：PKH-2026，计划 14 天完成。"
    assert clean_text(text) == text


def test_clean_text_preserves_urls() -> None:
    text = "文档地址：https://example.com/docs?q=rag&lang=zh"
    assert clean_text(text) == text


def test_clean_text_preserves_markdown_headings() -> None:
    assert clean_text("# 标题\n\n正文") == "# 标题\n\n正文"


def test_clean_text_preserves_code_block_indentation_and_line_breaks() -> None:
    text = "```python\nif True:\n    print('hello')\n\n\n    print('world')\n```"
    assert clean_text(text) == text


def test_clean_text_removes_invisible_control_characters() -> None:
    assert clean_text("正常\x00文本\u200b保留\n下一行") == "正常文本保留\n下一行"


def test_clean_parsed_document_drops_empty_sections_and_reindexes() -> None:
    document = ParsedDocument(
        sections=[
            ParsedSection(content="   ", section_index=0, page_number=1),
            ParsedSection(
                content="  有效内容  ",
                section_index=1,
                page_number=2,
                section_title="  标题  ",
            ),
        ],
        metadata={"source": "test"},
    )

    cleaned = clean_parsed_document(document)

    assert len(cleaned.sections) == 1
    assert cleaned.sections[0].section_index == 0
    assert cleaned.sections[0].page_number == 2
    assert cleaned.sections[0].section_title == "标题"
    assert cleaned.metadata == {"source": "test"}


def test_clean_text_is_idempotent() -> None:
    text = "  标题  \r\n\r\n正文    内容\x00\n"
    once = clean_text(text)
    assert clean_text(once) == once


def test_parse_document_applies_cleaning_after_parsing(tmp_path: Path) -> None:
    file_path = tmp_path / "clean.txt"
    file_path.write_bytes("第一行\r\n\r\n\r\n\r\n第二行".encode())

    result = parse_document(file_path, "txt")

    assert result.sections[0].content == "第一行\n\n\n第二行"
