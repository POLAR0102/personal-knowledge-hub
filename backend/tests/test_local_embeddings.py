from collections.abc import Iterable
from pathlib import Path

import pytest

from app.ai.embeddings import EmbeddingProvider
from app.ai.embeddings.base import (
    EmbeddingInputError,
    EmbeddingRequestError,
    EmbeddingResponseError,
)
from app.ai.embeddings.factory import create_embedding_provider
from app.ai.embeddings.fastembed_local import FastEmbedEmbeddingProvider
from app.core.config import Settings


class FakeFastEmbedModel:
    def __init__(
        self,
        *,
        document_vectors: list[list[float]] | None = None,
        query_vectors: list[list[float]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.document_vectors = document_vectors or []
        self.query_vectors = query_vectors or []
        self.error = error
        self.passage_calls: list[tuple[list[str], int]] = []
        self.query_calls: list[tuple[str, int]] = []

    def passage_embed(
        self,
        texts: Iterable[str],
        *,
        batch_size: int,
    ) -> Iterable[Iterable[float]]:
        self.passage_calls.append((list(texts), batch_size))
        if self.error is not None:
            raise self.error
        return iter(self.document_vectors)

    def query_embed(
        self,
        text: str,
        *,
        batch_size: int,
    ) -> Iterable[Iterable[float]]:
        self.query_calls.append((text, batch_size))
        if self.error is not None:
            raise self.error
        return iter(self.query_vectors)


def make_provider(
    model: FakeFastEmbedModel,
    *,
    dimension: int | None = None,
) -> FastEmbedEmbeddingProvider:
    return FastEmbedEmbeddingProvider(
        model="BAAI/bge-small-zh-v1.5",
        batch_size=8,
        dimension=dimension,
        embedding_model=model,
    )


def test_local_provider_uses_passage_and_query_embedding() -> None:
    model = FakeFastEmbedModel(
        document_vectors=[[0.1, 0.2], [0.3, 0.4]],
        query_vectors=[[0.5, 0.6]],
    )
    provider = make_provider(model)

    assert provider.embed_documents(["中文资料", "English notes"]) == [
        [0.1, 0.2],
        [0.3, 0.4],
    ]
    assert provider.embed_query("项目是什么？") == [0.5, 0.6]
    assert provider.model_name == "BAAI/bge-small-zh-v1.5"
    assert model.passage_calls == [(["中文资料", "English notes"], 8)]
    assert model.query_calls == [
        ("为这个句子生成表示以用于检索相关文章：项目是什么？", 8)
    ]


def test_local_provider_empty_document_list_skips_model() -> None:
    model = FakeFastEmbedModel()
    provider = make_provider(model)

    assert provider.embed_documents([]) == []
    assert model.passage_calls == []


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_local_provider_rejects_empty_text(text: str) -> None:
    provider = make_provider(FakeFastEmbedModel())

    with pytest.raises(EmbeddingInputError, match="cannot be empty"):
        provider.embed_query(text)


def test_local_provider_checks_vector_count() -> None:
    provider = make_provider(
        FakeFastEmbedModel(document_vectors=[[0.1, 0.2]])
    )

    with pytest.raises(EmbeddingResponseError, match="count"):
        provider.embed_documents(["one", "two"])


def test_local_provider_checks_configured_dimension() -> None:
    provider = make_provider(
        FakeFastEmbedModel(query_vectors=[[0.1, 0.2]]),
        dimension=3,
    )

    with pytest.raises(EmbeddingResponseError, match="dimensions"):
        provider.embed_query("query")


def test_local_provider_converts_model_error() -> None:
    provider = make_provider(FakeFastEmbedModel(error=RuntimeError("inference failed")))

    with pytest.raises(EmbeddingRequestError, match="generation failed"):
        provider.embed_query("query")


def test_factory_selects_local_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class StubProvider(EmbeddingProvider):
        @property
        def model_name(self) -> str:
            return "stub"

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0] for _text in texts]

        def embed_query(self, text: str) -> list[float]:
            return [1.0]

    def create_stub(
        *,
        model: str,
        batch_size: int,
        dimension: int | None,
        cache_dir: Path,
    ) -> EmbeddingProvider:
        captured.update(
            model=model,
            batch_size=batch_size,
            dimension=dimension,
            cache_dir=cache_dir,
        )
        return StubProvider()

    monkeypatch.setattr(
        "app.ai.embeddings.factory.FastEmbedEmbeddingProvider",
        create_stub,
    )
    settings = Settings(
        _env_file=None,
        embedding_provider="local",
        embedding_model="BAAI/bge-small-zh-v1.5",
        embedding_dimension=512,
        embedding_batch_size=16,
    )

    provider = create_embedding_provider(settings)

    assert provider.model_name == "stub"
    assert captured == {
        "model": "BAAI/bge-small-zh-v1.5",
        "batch_size": 16,
        "dimension": 512,
        "cache_dir": Path("model_cache"),
    }
