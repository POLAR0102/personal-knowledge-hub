from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.ai.embeddings import EmbeddingProvider, EmbeddingRequestError
from app.ai.vector_store import (
    CollectionHealth,
    SearchResult,
    VectorRecord,
    VectorStore,
)
from app.api.dependencies import (
    get_embedding_provider_dependency,
    get_vector_store_dependency,
)
from app.core.config import get_settings
from app.main import app


class MaintenanceEmbeddingProvider(EmbeddingProvider):
    @property
    def model_name(self) -> str:
        return "current-model"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if any("FAIL" in text for text in texts):
            raise EmbeddingRequestError("mock embedding failure")
        return [[float(index + 1), 1.0] for index, _text in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 1.0]


class MaintenanceVectorStore(VectorStore):
    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}

    def upsert_chunks(self, records: list[VectorRecord]) -> None:
        for record in records:
            self.records[f"chunk:{record.chunk_id}"] = record

    def delete_by_document(self, document_id: int, user_id: int) -> None:
        self.records = {
            key: record
            for key, record in self.records.items()
            if not (record.document_id == document_id and record.user_id == user_id)
        }

    def delete_by_knowledge_base(
        self,
        knowledge_base_id: int,
        user_id: int,
    ) -> None:
        self.records = {
            key: record
            for key, record in self.records.items()
            if not (
                record.knowledge_base_id == knowledge_base_id
                and record.user_id == user_id
            )
        }

    def search(
        self,
        query_vector: list[float],
        user_id: int,
        knowledge_base_id: int,
        top_k: int,
        embedding_model: str | None = None,
    ) -> list[SearchResult]:
        return []

    def count_by_document(self, document_id: int, user_id: int) -> int:
        return sum(
            record.document_id == document_id and record.user_id == user_id
            for record in self.records.values()
        )

    def collection_health(self) -> CollectionHealth:
        return CollectionHealth(healthy=True, record_count=len(self.records))

    def close(self) -> None:
        return None


@pytest.fixture
def maintenance_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[
    tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
    None,
    None,
]:
    client, _ = client_and_session
    provider = MaintenanceEmbeddingProvider()
    vector_store = MaintenanceVectorStore()
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "embedding_model", "current-model")
    monkeypatch.setattr(settings, "knowledge_base_reindex_limit", 50)
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
        json={"name": "索引维护测试"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload_document(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    *,
    filename: str,
    content: str,
    process: bool = True,
) -> int:
    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"file": (filename, content.encode(), "text/plain")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    if process:
        processed = client.post(
            f"/api/v1/documents/{document_id}/process",
            headers=headers,
        )
        assert processed.status_code == 200
    return document_id


def index_document(client: TestClient, headers: dict[str, str], document_id: int) -> None:
    response = client.post(
        f"/api/v1/documents/{document_id}/index",
        headers=headers,
    )
    assert response.status_code == 200


def test_index_health_is_healthy_when_counts_and_model_match(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, _ = maintenance_context
    headers = register_and_login(client, username="healthy", email="healthy@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(
        client,
        headers,
        knowledge_base_id,
        filename="healthy.txt",
        content="健康索引内容",
    )
    index_document(client, headers, document_id)

    response = client.get(
        f"/api/v1/documents/{document_id}/index-health",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["health_status"] == "healthy"
    assert response.json()["chunk_count"] == response.json()["vector_count"]


def test_index_health_detects_missing_vectors(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, vector_store = maintenance_context
    headers = register_and_login(client, username="missing", email="missing@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(
        client, headers, knowledge_base_id, filename="missing.txt", content="缺少向量"
    )
    index_document(client, headers, document_id)
    vector_store.delete_by_document(document_id, 1)

    response = client.get(
        f"/api/v1/documents/{document_id}/index-health",
        headers=headers,
    )

    assert response.json()["health_status"] == "missing_vectors"


def test_index_health_detects_extra_vectors(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, vector_store = maintenance_context
    headers = register_and_login(client, username="extra", email="extra@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(
        client, headers, knowledge_base_id, filename="extra.txt", content="多余向量"
    )
    index_document(client, headers, document_id)
    vector_store.records["chunk:9999"] = VectorRecord(
        chunk_id=9999,
        user_id=1,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        chunk_index=9999,
        filename="extra.txt",
        content="orphan vector",
        content_hash="f" * 64,
        embedding_model="current-model",
        embedding=[1.0, 1.0],
    )

    response = client.get(
        f"/api/v1/documents/{document_id}/index-health",
        headers=headers,
    )

    assert response.json()["health_status"] == "extra_vectors"


def test_index_health_detects_model_mismatch(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = maintenance_context
    headers = register_and_login(client, username="model", email="model@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(
        client, headers, knowledge_base_id, filename="model.txt", content="模型变化"
    )
    index_document(client, headers, document_id)
    monkeypatch.setattr(get_settings(), "embedding_model", "new-model")

    response = client.get(
        f"/api/v1/documents/{document_id}/index-health",
        headers=headers,
    )

    assert response.json()["health_status"] == "model_mismatch"
    assert response.json()["embedding_model"] == "current-model"
    assert response.json()["current_embedding_model"] == "new-model"


def test_index_health_reports_not_indexed(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, _ = maintenance_context
    headers = register_and_login(client, username="not-indexed", email="not-indexed@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(
        client, headers, knowledge_base_id, filename="new.txt", content="尚未索引"
    )

    response = client.get(
        f"/api/v1/documents/{document_id}/index-health",
        headers=headers,
    )

    assert response.json()["health_status"] == "not_indexed"


def test_index_health_reports_failed_status(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, _ = maintenance_context
    headers = register_and_login(client, username="failed", email="failed@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(
        client, headers, knowledge_base_id, filename="failed.txt", content="FAIL"
    )
    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    assert response.status_code == 502

    health = client.get(
        f"/api/v1/documents/{document_id}/index-health",
        headers=headers,
    )

    assert health.json()["health_status"] == "failed"


def test_batch_reindex_indexes_only_completed_documents(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, vector_store = maintenance_context
    headers = register_and_login(client, username="batch", email="batch@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    first_id = upload_document(
        client, headers, knowledge_base_id, filename="one.txt", content="第一个文档"
    )
    second_id = upload_document(
        client, headers, knowledge_base_id, filename="two.txt", content="第二个文档"
    )
    upload_document(
        client,
        headers,
        knowledge_base_id,
        filename="pending.txt",
        content="待处理文档",
        process=False,
    )

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/reindex",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["succeeded"] == 2
    assert response.json()["failed"] == 0
    assert vector_store.count_by_document(first_id, 1) > 0
    assert vector_store.count_by_document(second_id, 1) > 0


def test_batch_reindex_reports_partial_failure(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, _ = maintenance_context
    headers = register_and_login(client, username="partial", email="partial-batch@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    upload_document(
        client, headers, knowledge_base_id, filename="ok.txt", content="正常内容"
    )
    upload_document(
        client, headers, knowledge_base_id, filename="fail.txt", content="FAIL"
    )

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/reindex",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["succeeded"] == 1
    assert response.json()["failed"] == 1
    failed_item = next(
        item for item in response.json()["items"] if item["index_status"] == "failed"
    )
    assert failed_item["error_message"]


def test_batch_reindex_other_user_returns_404(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, _ = maintenance_context
    owner_headers = register_and_login(client, username="batch-a", email="batch-a@example.com")
    other_headers = register_and_login(client, username="batch-b", email="batch-b@example.com")
    knowledge_base_id = create_knowledge_base(client, owner_headers)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/reindex",
        headers=other_headers,
    )

    assert response.status_code == 404


def test_batch_reindex_empty_knowledge_base_returns_empty_result(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
) -> None:
    client, _, _ = maintenance_context
    headers = register_and_login(client, username="empty-batch", email="empty-batch@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/reindex",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "knowledge_base_id": knowledge_base_id,
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "items": [],
    }


def test_batch_reindex_enforces_document_limit(
    maintenance_context: tuple[TestClient, MaintenanceEmbeddingProvider, MaintenanceVectorStore],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, vector_store = maintenance_context
    headers = register_and_login(client, username="limit", email="limit@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    upload_document(client, headers, knowledge_base_id, filename="one.txt", content="一")
    upload_document(client, headers, knowledge_base_id, filename="two.txt", content="二")
    monkeypatch.setattr(get_settings(), "knowledge_base_reindex_limit", 1)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/reindex",
        headers=headers,
    )

    assert response.status_code == 422
    assert "limited to 1 documents" in response.json()["detail"]
    assert vector_store.records == {}
