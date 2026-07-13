from abc import ABC, abstractmethod
from dataclasses import dataclass


class VectorStoreError(Exception):
    """Base error for vector store operations."""


class VectorStoreConfigurationError(VectorStoreError):
    """Raised when the vector store configuration is invalid."""


class VectorStoreInputError(VectorStoreError):
    """Raised when a vector store input is invalid."""


class VectorStoreOperationError(VectorStoreError):
    """Raised when the vector store cannot complete an operation."""


@dataclass(frozen=True, slots=True)
class VectorRecord:
    chunk_id: int
    user_id: int
    knowledge_base_id: int
    document_id: int
    chunk_index: int
    filename: str
    content: str
    content_hash: str
    embedding: list[float]
    page_number: int | None = None
    section_title: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk_id: int
    document_id: int
    filename: str
    content: str
    chunk_index: int
    page_number: int | None
    section_title: str | None
    distance: float


@dataclass(frozen=True, slots=True)
class CollectionHealth:
    healthy: bool
    record_count: int


class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(self, records: list[VectorRecord]) -> None:
        """Insert or replace chunk vectors by stable chunk ID."""

    @abstractmethod
    def delete_by_document(self, document_id: int, user_id: int) -> None:
        """Delete vectors belonging to one user's document."""

    @abstractmethod
    def delete_by_knowledge_base(
        self,
        knowledge_base_id: int,
        user_id: int,
    ) -> None:
        """Delete vectors belonging to one user's knowledge base."""

    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        user_id: int,
        knowledge_base_id: int,
        top_k: int,
    ) -> list[SearchResult]:
        """Search within one user and one knowledge base."""

    @abstractmethod
    def count_by_document(self, document_id: int, user_id: int) -> int:
        """Count vectors belonging to one user's document."""

    @abstractmethod
    def collection_health(self) -> CollectionHealth:
        """Check whether the collection is reachable."""

    @abstractmethod
    def close(self) -> None:
        """Release vector store resources."""
