from pathlib import Path

import pymupdf

from app.ai.document_processing.base import (
    DocumentParser,
    DocumentReadError,
    ScannedPdfNotSupportedError,
)
from app.ai.document_processing.parser_result import ParsedDocument, ParsedSection


class PdfParser(DocumentParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            with pymupdf.open(file_path) as pdf:
                sections: list[ParsedSection] = []
                for page in pdf:
                    text = page.get_text("text").strip()
                    if text:
                        sections.append(
                            ParsedSection(
                                content=text,
                                section_index=len(sections),
                                page_number=page.number + 1,
                            )
                        )
                page_count = pdf.page_count
        except (OSError, RuntimeError, ValueError, pymupdf.FileDataError) as exc:
            raise DocumentReadError("无法读取 PDF 文件") from exc

        if not sections:
            raise ScannedPdfNotSupportedError(
                "当前 PDF 可能为扫描版文件，首版暂不支持 OCR"
            )

        return ParsedDocument(
            sections=sections,
            metadata={"format": "pdf", "page_count": page_count},
        )
