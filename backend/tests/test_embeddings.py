from dataclasses import dataclass

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from app.ai.embeddings.base import (
    EmbeddingConfigurationError,
    EmbeddingInputError,
    EmbeddingRequestError,
    EmbeddingResponseError,
)
from app.ai.embeddings.openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
)


@dataclass
class FakeEmbeddingItem:
    index: int
    embedding: list[float]


@dataclass
class FakeEmbeddingResponse:
    data: list[FakeEmbeddingItem]


class FakeEmbeddingsResource:
    def __init__(
        self,
        outcomes: list[FakeEmbeddingResponse | Exception],
    ) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[list[str], str, int | None]] = []

    def create(
        self,
        *,
        input: list[str],
        model: str,
        dimensions: int | None = None,
    ) -> FakeEmbeddingResponse:
        self.calls.append((input, model, dimensions))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeEmbeddingClient:
    def __init__(self, embeddings: FakeEmbeddingsResource) -> None:
        self.embeddings = embeddings


def make_response(*vectors: list[float]) -> FakeEmbeddingResponse:
    return FakeEmbeddingResponse(
        data=[
            FakeEmbeddingItem(index=index, embedding=vector)
            for index, vector in enumerate(vectors)
        ]
    )


def make_provider(
    resource: FakeEmbeddingsResource,
    *,
    batch_size: int = 32,
    max_retries: int = 0,
) -> OpenAICompatibleEmbeddingProvider:
    return OpenAICompatibleEmbeddingProvider(
        api_key="test-api-key",
        base_url="https://embedding.example/v1",
        model="test-embedding-model",
        batch_size=batch_size,
        timeout_seconds=5,
        max_retries=max_retries,
        client=FakeEmbeddingClient(resource),
    )


def test_embed_single_query() -> None:
    resource = FakeEmbeddingsResource([make_response([0.1, 0.2])])
    provider = make_provider(resource)

    assert provider.embed_query("测试问题") == [0.1, 0.2]
    assert resource.calls == [
        (["测试问题"], "test-embedding-model", None),
    ]


def test_embed_documents_preserves_provider_indexes() -> None:
    response = FakeEmbeddingResponse(
        data=[
            FakeEmbeddingItem(index=1, embedding=[2.0, 2.0]),
            FakeEmbeddingItem(index=0, embedding=[1.0, 1.0]),
        ]
    )
    provider = make_provider(FakeEmbeddingsResource([response]))

    assert provider.embed_documents(["first", "second"]) == [
        [1.0, 1.0],
        [2.0, 2.0],
    ]


def test_embed_documents_splits_batches() -> None:
    resource = FakeEmbeddingsResource(
        [
            make_response([1.0], [2.0]),
            make_response([3.0], [4.0]),
            make_response([5.0]),
        ]
    )
    provider = make_provider(resource, batch_size=2)

    assert provider.embed_documents(["1", "2", "3", "4", "5"]) == [
        [1.0],
        [2.0],
        [3.0],
        [4.0],
        [5.0],
    ]
    assert [call[0] for call in resource.calls] == [
        ["1", "2"],
        ["3", "4"],
        ["5"],
    ]


def test_embed_documents_empty_list_skips_request() -> None:
    resource = FakeEmbeddingsResource([])
    provider = make_provider(resource)

    assert provider.embed_documents([]) == []
    assert resource.calls == []


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_text_is_rejected(text: str) -> None:
    provider = make_provider(FakeEmbeddingsResource([]))

    with pytest.raises(EmbeddingInputError, match="cannot be empty"):
        provider.embed_query(text)


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(EmbeddingConfigurationError, match="AI_API_KEY"):
        OpenAICompatibleEmbeddingProvider(
            api_key=None,
            base_url=None,
            model="model",
            batch_size=1,
            timeout_seconds=5,
            max_retries=0,
        )


def test_response_count_must_match_input_count() -> None:
    provider = make_provider(
        FakeEmbeddingsResource([make_response([1.0, 2.0])])
    )

    with pytest.raises(EmbeddingResponseError, match="count"):
        provider.embed_documents(["one", "two"])


def test_vector_dimensions_must_be_consistent() -> None:
    provider = make_provider(
        FakeEmbeddingsResource([make_response([1.0], [2.0, 3.0])])
    )

    with pytest.raises(EmbeddingResponseError, match="dimensions"):
        provider.embed_documents(["one", "two"])


def test_timeout_is_converted_to_business_error() -> None:
    request = httpx.Request("POST", "https://embedding.example/v1/embeddings")
    provider = make_provider(
        FakeEmbeddingsResource([APITimeoutError(request=request)])
    )

    with pytest.raises(EmbeddingRequestError, match="request failed"):
        provider.embed_query("query")


def test_rate_limit_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "https://embedding.example/v1/embeddings")
    response = httpx.Response(429, request=request)
    resource = FakeEmbeddingsResource(
        [
            RateLimitError("rate limited", response=response, body=None),
            make_response([0.4, 0.5]),
        ]
    )
    provider = make_provider(resource, max_retries=1)
    monkeypatch.setattr(
        "app.ai.embeddings.openai_compatible.time.sleep",
        lambda _seconds: None,
    )

    assert provider.embed_query("query") == [0.4, 0.5]
    assert len(resource.calls) == 2


def test_retry_limit_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "https://embedding.example/v1/embeddings")
    response = httpx.Response(429, request=request)
    resource = FakeEmbeddingsResource(
        [
            RateLimitError("rate limited", response=response, body=None),
            RateLimitError("rate limited", response=response, body=None),
            RateLimitError("rate limited", response=response, body=None),
        ]
    )
    provider = make_provider(resource, max_retries=2)
    monkeypatch.setattr(
        "app.ai.embeddings.openai_compatible.time.sleep",
        lambda _seconds: None,
    )

    with pytest.raises(EmbeddingRequestError, match="request failed"):
        provider.embed_query("query")
    assert len(resource.calls) == 3
