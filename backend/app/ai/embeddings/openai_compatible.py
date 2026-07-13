import logging
import time
from collections.abc import Sequence
from typing import Protocol, cast

from openai import (
    APIConnectionError,
    APIStatusError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from app.ai.embeddings.base import (
    EmbeddingConfigurationError,
    EmbeddingInputError,
    EmbeddingProvider,
    EmbeddingRequestError,
    EmbeddingResponseError,
)

logger = logging.getLogger(__name__)


class _EmbeddingItem(Protocol):
    index: int
    embedding: list[float]


class _EmbeddingResponse(Protocol):
    data: list[_EmbeddingItem]


class _EmbeddingsResource(Protocol):
    def create(
        self,
        *,
        input: list[str],
        model: str,
        dimensions: int = ...,
    ) -> _EmbeddingResponse: ...


class _EmbeddingClient(Protocol):
    embeddings: _EmbeddingsResource


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        model: str,
        batch_size: int,
        timeout_seconds: float,
        max_retries: int,
        dimension: int | None = None,
        client: _EmbeddingClient | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise EmbeddingConfigurationError("AI_API_KEY is not configured")
        if not model.strip():
            raise EmbeddingConfigurationError("EMBEDDING_MODEL is not configured")
        if batch_size < 1:
            raise EmbeddingConfigurationError("EMBEDDING_BATCH_SIZE must be at least 1")
        if timeout_seconds <= 0:
            raise EmbeddingConfigurationError(
                "EMBEDDING_TIMEOUT_SECONDS must be greater than 0"
            )
        if max_retries < 0:
            raise EmbeddingConfigurationError(
                "EMBEDDING_MAX_RETRIES cannot be negative"
            )
        if dimension is not None and dimension < 1:
            raise EmbeddingConfigurationError("EMBEDDING_DIMENSION must be at least 1")

        self._model = model.strip()
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._dimension = dimension
        self._client = client or self._create_client(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    @property
    def model_name(self) -> str:
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._validate_texts(texts)

        vectors: list[list[float]] = []
        expected_dimension = self._dimension
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = self._request_batch(batch)
            batch_vectors = self._parse_response(response, len(batch))

            for vector in batch_vectors:
                if expected_dimension is None:
                    expected_dimension = len(vector)
                elif len(vector) != expected_dimension:
                    raise EmbeddingResponseError(
                        "Embedding vectors have inconsistent dimensions"
                    )
            vectors.extend(batch_vectors)

        if len(vectors) != len(texts):
            raise EmbeddingResponseError(
                "Embedding response count does not match input count"
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _create_client(
        self,
        *,
        api_key: str,
        base_url: str | None,
        timeout_seconds: float,
    ) -> _EmbeddingClient:
        options: dict[str, object] = {
            "api_key": api_key,
            "timeout": timeout_seconds,
            "max_retries": 0,
        }
        if base_url and base_url.strip():
            options["base_url"] = base_url.strip()
        return cast(_EmbeddingClient, OpenAI(**options))

    def _request_batch(self, texts: list[str]) -> _EmbeddingResponse:
        for attempt in range(self._max_retries + 1):
            try:
                if self._dimension is None:
                    return self._client.embeddings.create(
                        input=texts,
                        model=self._model,
                    )
                return self._client.embeddings.create(
                    input=texts,
                    model=self._model,
                    dimensions=self._dimension,
                )
            except OpenAIError as exc:
                can_retry = self._is_retryable(exc)
                if not can_retry or attempt >= self._max_retries:
                    raise EmbeddingRequestError(
                        "Embedding provider request failed"
                    ) from exc
                logger.warning(
                    "Embedding request failed with %s; retrying (%s/%s)",
                    type(exc).__name__,
                    attempt + 1,
                    self._max_retries,
                )
                time.sleep(min(2**attempt, 4))

        raise EmbeddingRequestError("Embedding provider request failed")

    @staticmethod
    def _is_retryable(exc: OpenAIError) -> bool:
        if isinstance(exc, (APIConnectionError, RateLimitError)):
            return True
        return isinstance(exc, APIStatusError) and (
            exc.status_code in {408, 409, 429} or exc.status_code >= 500
        )

    @staticmethod
    def _validate_texts(texts: Sequence[str]) -> None:
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingInputError("Embedding text cannot be empty")

    @staticmethod
    def _parse_response(
        response: _EmbeddingResponse,
        expected_count: int,
    ) -> list[list[float]]:
        items = sorted(response.data, key=lambda item: item.index)
        if len(items) != expected_count:
            raise EmbeddingResponseError(
                "Embedding response count does not match input count"
            )
        if [item.index for item in items] != list(range(expected_count)):
            raise EmbeddingResponseError("Embedding response indexes are invalid")

        vectors: list[list[float]] = []
        for item in items:
            if not item.embedding or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in item.embedding
            ):
                raise EmbeddingResponseError("Embedding response contains an invalid vector")
            vectors.append([float(value) for value in item.embedding])
        return vectors
