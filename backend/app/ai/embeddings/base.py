from abc import ABC, abstractmethod


class EmbeddingError(Exception):
    """Base error for embedding operations."""


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when the embedding provider is not configured correctly."""


class EmbeddingInputError(EmbeddingError):
    """Raised when text sent for embedding is invalid."""


class EmbeddingRequestError(EmbeddingError):
    """Raised when the provider request cannot be completed."""


class EmbeddingResponseError(EmbeddingError):
    """Raised when the provider returns an invalid response."""


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured embedding model name."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents while preserving input order."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
