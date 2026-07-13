from collections.abc import Iterable, Sequence
from numbers import Real
from pathlib import Path
from typing import Protocol, cast

from app.ai.embeddings.base import (
    EmbeddingConfigurationError,
    EmbeddingInputError,
    EmbeddingProvider,
    EmbeddingRequestError,
    EmbeddingResponseError,
)

BGE_SMALL_ZH_MODEL = "BAAI/bge-small-zh-v1.5"
BGE_SMALL_ZH_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


class _FastEmbedModel(Protocol):
    def passage_embed(
        self,
        texts: Iterable[str],
        *,
        batch_size: int,
    ) -> Iterable[Iterable[float]]: ...

    def query_embed(
        self,
        text: str,
        *,
        batch_size: int,
    ) -> Iterable[Iterable[float]]: ...


class FastEmbedEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        model: str,
        batch_size: int,
        dimension: int | None = None,
        cache_dir: Path | None = None,
        embedding_model: _FastEmbedModel | None = None,
    ) -> None:
        if not model.strip():
            raise EmbeddingConfigurationError("EMBEDDING_MODEL is not configured")
        if batch_size < 1:
            raise EmbeddingConfigurationError("EMBEDDING_BATCH_SIZE must be at least 1")
        if dimension is not None and dimension < 1:
            raise EmbeddingConfigurationError("EMBEDDING_DIMENSION must be at least 1")

        self._model_name = model.strip()
        self._batch_size = batch_size
        self._dimension = dimension
        self._cache_dir = cache_dir
        self._embedding_model = embedding_model or self._load_model()

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._validate_texts(texts)

        try:
            vectors = self._embedding_model.passage_embed(
                texts,
                batch_size=self._batch_size,
            )
            return self._validate_vectors(vectors, expected_count=len(texts))
        except (EmbeddingInputError, EmbeddingResponseError):
            raise
        except Exception as exc:
            raise EmbeddingRequestError("Local embedding generation failed") from exc

    def embed_query(self, text: str) -> list[float]:
        self._validate_texts([text])
        query_text = (
            f"{BGE_SMALL_ZH_QUERY_PREFIX}{text}"
            if self._model_name == BGE_SMALL_ZH_MODEL
            else text
        )

        try:
            vectors = self._embedding_model.query_embed(
                query_text,
                batch_size=self._batch_size,
            )
            return self._validate_vectors(vectors, expected_count=1)[0]
        except (EmbeddingInputError, EmbeddingResponseError):
            raise
        except Exception as exc:
            raise EmbeddingRequestError("Local embedding generation failed") from exc

    def _load_model(self) -> _FastEmbedModel:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise EmbeddingConfigurationError(
                "fastembed is not installed for the local embedding provider"
            ) from exc

        try:
            return cast(
                _FastEmbedModel,
                TextEmbedding(
                    model_name=self._model_name,
                    cache_dir=str(self._cache_dir) if self._cache_dir else None,
                ),
            )
        except Exception as exc:
            raise EmbeddingConfigurationError(
                "Local embedding model could not be loaded"
            ) from exc

    @staticmethod
    def _validate_texts(texts: Sequence[str]) -> None:
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingInputError("Embedding text cannot be empty")

    def _validate_vectors(
        self,
        vectors: Iterable[Iterable[float]],
        *,
        expected_count: int,
    ) -> list[list[float]]:
        raw_vectors = list(vectors)
        if len(raw_vectors) != expected_count:
            raise EmbeddingResponseError(
                "Embedding response count does not match input count"
            )

        parsed_vectors: list[list[float]] = []
        expected_dimension = self._dimension
        for raw_vector in raw_vectors:
            values = list(raw_vector)
            if not values or any(
                isinstance(value, bool) or not isinstance(value, Real)
                for value in values
            ):
                raise EmbeddingResponseError(
                    "Embedding response contains an invalid vector"
                )

            vector = [float(value) for value in values]
            if expected_dimension is None:
                expected_dimension = len(vector)
            elif len(vector) != expected_dimension:
                raise EmbeddingResponseError(
                    "Embedding vectors have inconsistent dimensions"
                )
            parsed_vectors.append(vector)

        self._dimension = expected_dimension
        return parsed_vectors
