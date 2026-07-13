from pathlib import Path

from app.ai.document_processing.base import DocumentParser, EmptyDocumentError
from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection
from app.ai.document_processing.parsers.txt_parser import read_utf8_text


class MarkdownParser(DocumentParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        text = read_utf8_text(file_path)
        sections: list[ParsedSection] = []
        current_lines: list[str] = []
        current_title: str | None = None
        in_code_block = False

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

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code_block = not in_code_block

            is_heading = (
                not in_code_block
                and stripped.startswith("#")
                and stripped.lstrip("#").startswith(" ")
            )
            if is_heading:
                append_section()
                current_lines = [line]
                current_title = stripped.lstrip("#").strip() or None
            else:
                current_lines.append(line)

        append_section()
        if not sections:
            raise EmptyDocumentError("文档没有可提取的文本内容")

        return ParsedDocument(
            sections=sections,
            metadata={"format": "markdown", "encoding": "utf-8"},
        )
