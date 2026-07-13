from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.ai.embeddings import EmbeddingProvider, EmbeddingRequestError
from app.ai.vector_store import (
    CollectionHealth,
    SearchResult,
    VectorRecord,
    VectorStore,
    VectorStoreOperationError,
)
from app.api.dependencies import (
    get_embedding_provider_dependency,
    get_vector_store_dependency,
)
from app.main import app


class SearchEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.fail = False

    @property
    def model_name(self) -> str:
        return "test-search-model"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        if self.fail:
            raise EmbeddingRequestError("mock query embedding failure")
        return [1.0, 0.0]


class SearchVectorStore(VectorStore):
    def __init__(self) -> None:
        self.results: list[SearchResult] = []
        self.search_calls: list[tuple[list[float], int, int, int]] = []
        self.fail = False

    def upsert_chunks(self, records: list[VectorRecord]) -> None:
        return None

    def delete_by_document(self, document_id: int, user_id: int) -> None:
        return None

    def delete_by_knowledge_base(
        self,
        knowledge_base_id: int,
        user_id: int,
    ) -> None:
        return None

    def search(
        self,
        query_vector: list[float],
        user_id: int,
        knowledge_base_id: int,
        top_k: int,
    ) -> list[SearchResult]:
        self.search_calls.append((query_vector, user_id, knowledge_base_id, top_k))
        if self.fail:
            raise VectorStoreOperationError("mock vector search failure")
        return self.results[:top_k]

    def count_by_document(self, document_id: int, user_id: int) -> int:
        return 0

    def collection_health(self) -> CollectionHealth:
        return CollectionHealth(healthy=True, record_count=0)

    def close(self) -> None:
        return None


@pytest.fixture
def search_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> Generator[
    tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
    None,
    None,
]:
    client, _ = client_and_session
    provider = SearchEmbeddingProvider()
    vector_store = SearchVectorStore()
    app.dependency_overrides[get_embedding_provider_dependency] = lambda: provider
    app.dependency_overrides[get_vector_store_dependency] = lambda: vector_store
    try:
        yield client, provider, vector_store
    finally:
        app.dependency_overrides.pop(get_embedding_provider_dependency, None)
        app.dependency_overrides.pop(get_vector_store_dependency, None)


def register_and_login(
    client: TestClient,
    *,
    username: str,
    email: str,
) -> dict[str, str]:
    password = "123456"
    assert client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    ).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_knowledge_base(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "语义检索测试"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def sample_results() -> list[SearchResult]:
    return [
        SearchResult(
            chunk_id=8,
            document_id=3,
            filename="项目说明.txt",
            content="核心版本计划在 14 天内完成。",
            chunk_index=1,
            page_number=None,
            section_title="项目计划",
            distance=0.14,
        ),
        SearchResult(
            chunk_id=9,
            document_id=4,
            filename="补充说明.pdf",
            content="项目代号为 PKH-2026。",
            chunk_index=0,
            page_number=2,
            section_title=None,
            distance=0.31,
        ),
    ]


def test_semantic_search_returns_real_chunk_fields_in_order(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, provider, vector_store = search_context
    headers = register_and_login(client, username="searcher", email="searcher@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    vector_store.results = sample_results()

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "query": "  核心版本需要多久？  ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "核心版本需要多久？"
    assert [item["chunk_id"] for item in body["results"]] == [8, 9]
    assert body["results"][0] == {
        "chunk_id": 8,
        "document_id": 3,
        "filename": "项目说明.txt",
        "content": "核心版本计划在 14 天内完成。",
        "chunk_index": 1,
        "page_number": None,
        "section_title": "项目计划",
        "distance": 0.14,
    }
    assert provider.queries == ["核心版本需要多久？"]
    assert vector_store.search_calls == [
        ([1.0, 0.0], 1, knowledge_base_id, 4)
    ]


def test_custom_top_k_is_forwarded(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, _, vector_store = search_context
    headers = register_and_login(client, username="top-k", email="top-k@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    vector_store.results = sample_results()

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "query": "项目", "top_k": 1},
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert vector_store.search_calls[0][3] == 1


@pytest.mark.parametrize(
    "query",
    ["", "   ", "x" * 1001],
)
def test_invalid_query_returns_422(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
    query: str,
) -> None:
    client, _, _ = search_context
    headers = register_and_login(client, username="bad-query", email="bad-query@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "query": query},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("top_k", [0, 21])
def test_invalid_top_k_returns_422(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
    top_k: int,
) -> None:
    client, _, _ = search_context
    headers = register_and_login(client, username="bad-top-k", email="bad-top-k@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "query": "项目", "top_k": top_k},
    )

    assert response.status_code == 422


def test_semantic_search_requires_authentication(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, _, _ = search_context

    response = client.post(
        "/api/v1/rag/search",
        json={"knowledge_base_id": 1, "query": "项目"},
    )

    assert response.status_code == 401


def test_other_user_knowledge_base_returns_404(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, provider, vector_store = search_context
    owner_headers = register_and_login(client, username="scope-a", email="scope-a@example.com")
    other_headers = register_and_login(client, username="scope-b", email="scope-b@example.com")
    knowledge_base_id = create_knowledge_base(client, owner_headers)

    response = client.post(
        "/api/v1/rag/search",
        headers=other_headers,
        json={"knowledge_base_id": knowledge_base_id, "query": "项目"},
    )

    assert response.status_code == 404
    assert provider.queries == []
    assert vector_store.search_calls == []


def test_missing_knowledge_base_returns_404(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, _, _ = search_context
    headers = register_and_login(client, username="missing-kb", email="missing-kb@example.com")

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": 999, "query": "项目"},
    )

    assert response.status_code == 404


def test_no_vector_results_returns_empty_array(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, _, _ = search_context
    headers = register_and_login(client, username="empty", email="empty@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "query": "没有结果"},
    )

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_embedding_failure_returns_503(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, provider, _ = search_context
    headers = register_and_login(client, username="embed-error", email="embed-error@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    provider.fail = True

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "query": "项目"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to generate query embedding"


def test_vector_store_failure_returns_503(
    search_context: tuple[TestClient, SearchEmbeddingProvider, SearchVectorStore],
) -> None:
    client, _, vector_store = search_context
    headers = register_and_login(client, username="store-error", email="store-error@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    vector_store.fail = True

    response = client.post(
        "/api/v1/rag/search",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "query": "项目"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Unable to search vector store"
