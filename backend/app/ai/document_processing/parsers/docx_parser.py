from collections.abc import Iterator
from pathlib import Path

from docx import Document as open_docx
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ai.document_processing.base import (
    DocumentParser,
    DocumentReadError,
    EmptyDocumentError,
)
from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection


def iter_blocks(document: DocxDocument) -> Iterator[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


class DocxParser(DocumentParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            document = open_docx(file_path)
        except (OSError, ValueError, PackageNotFoundError) as exc:
            raise DocumentReadError("无法读取 DOCX 文件") from exc

        sections: list[ParsedSection] = []
        current_title: str | None = None
        current_lines: list[str] = []

        def append_section() -> None:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append(
                    ParsedSection(
                        content=content,
                        section_index=len(sections),
                        section_title=current_title,
                    )
                )

        for block in iter_blocks(document):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if not text:
                    continue
                style_name = block.style.name if block.style is not None else ""
                if style_name.startswith("Heading"):
                    append_section()
                    current_lines = [text]
                    current_title = text
                else:
                    current_lines.append(text)
            else:
                table_lines = [
                    " | ".join(cell.text.strip() for cell in row.cells)
                    for row in block.rows
                ]
                current_lines.extend(line for line in table_lines if line.strip(" |"))

        append_section()
        if not sections:
            raise EmptyDocumentError("文档没有可提取的文本内容")

        return ParsedDocument(
            sections=sections,
            metadata={"format": "docx"},
        )
