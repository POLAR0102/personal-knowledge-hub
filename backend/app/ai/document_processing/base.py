from abc import ABC, abstractmethod
from pathlib import Path

from app.ai.document_processing.parser_result import ParsedDocument


class DocumentProcessingError(Exception):
    """Base exception for errors safe to translate into a short user message."""


class UnsupportedDocumentTypeError(DocumentProcessingError):
    pass


class DocumentReadError(DocumentProcessingError):
    pass


class EmptyDocumentError(DocumentProcessingError):
    pass


class ScannedPdfNotSupportedError(DocumentProcessingError):
    pass


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        raise NotImplementedError
