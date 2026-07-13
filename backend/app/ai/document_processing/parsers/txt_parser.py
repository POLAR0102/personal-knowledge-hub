from pathlib import Path

from app.ai.document_processing.base import (
    DocumentParser,
    DocumentReadError,
    EmptyDocumentError,
)
from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection


def read_utf8_text(file_path: Path) -> str:
    try:
        raw_content = file_path.read_bytes()
    except OSError as exc:
        raise DocumentReadError("无法读取文档文件") from exc

    try:
        return raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentReadError("文本文件不是有效的 UTF-8 编码") from exc


class TxtParser(DocumentParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        content = read_utf8_text(file_path).strip()
        if not content:
            raise EmptyDocumentError("文档没有可提取的文本内容")

        return ParsedDocument(
            sections=[ParsedSection(content=content, section_index=0)],
            metadata={"format": "txt", "encoding": "utf-8"},
        )
