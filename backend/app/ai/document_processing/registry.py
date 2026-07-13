from app.ai.document_processing.base import (
    DocumentParser,
    UnsupportedDocumentTypeError,
)
from app.ai.document_processing.parsers import (
    DocxParser,
    MarkdownParser,
    PdfParser,
    TxtParser,
)

PARSERS: dict[str, DocumentParser] = {
    "txt": TxtParser(),
    "md": MarkdownParser(),
    "pdf": PdfParser(),
    "docx": DocxParser(),
}


def get_parser(file_type: str) -> DocumentParser:
    normalized_type = file_type.lower().lstrip(".")
    try:
        return PARSERS[normalized_type]
    except KeyError as exc:
        raise UnsupportedDocumentTypeError(
            f"暂不支持 {normalized_type or '未知'} 格式"
        ) from exc
