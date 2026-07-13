from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
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
from app.core.config import get_settings
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentIndexStatus,
    DocumentStatus,
)
from app.main import app


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.fail = False
        self.before_embed: Callable[[], None] | None = None
        self.document_calls: list[list[str]] = []

    @property
    def model_name(self) -> str:
        return "test-embedding-v1"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        if self.before_embed is not None:
            self.before_embed()
        if self.fail:
            raise EmbeddingRequestError("mock embedding failure")
        return [[float(index + 1), 1.0] for index, _text in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        if self.fail:
            raise EmbeddingRequestError("mock embedding failure")
        return [float(len(text)), 1.0]


class FakeVectorStore(VectorStore):
    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}
        self.fail_upsert = False
        self.partially_fail_upsert = False
        self.fail_delete = False

    def upsert_chunks(self, records: list[VectorRecord]) -> None:
        if self.partially_fail_upsert and records:
            self.records[f"chunk:{records[0].chunk_id}"] = records[0]
            raise VectorStoreOperationError("mock partial upsert failure")
        if self.fail_upsert:
            raise VectorStoreOperationError("mock upsert failure")
        for record in records:
            self.records[f"chunk:{record.chunk_id}"] = record

    def delete_by_document(self, document_id: int, user_id: int) -> None:
        if self.fail_delete:
            raise VectorStoreOperationError("mock delete failure")
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
        if self.fail_delete:
            raise VectorStoreOperationError("mock delete failure")
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
def indexing_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[
    tuple[
        TestClient,
        sessionmaker[Session],
        FakeEmbeddingProvider,
        FakeVectorStore,
    ],
    None,
    None,
]:
    client, testing_session = client_and_session
    provider = FakeEmbeddingProvider()
    vector_store = FakeVectorStore()
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(
        "app.services.document.get_vector_store",
        lambda: vector_store,
    )
    monkeypatch.setattr(
        "app.services.document_processing.get_vector_store",
        lambda: vector_store,
    )
    monkeypatch.setattr(
        "app.services.knowledge_base.get_vector_store",
        lambda: vector_store,
    )
    cast_app: FastAPI = app
    cast_app.dependency_overrides[get_embedding_provider_dependency] = lambda: provider
    cast_app.dependency_overrides[get_vector_store_dependency] = lambda: vector_store
    try:
        yield client, testing_session, provider, vector_store
    finally:
        cast_app.dependency_overrides.pop(get_embedding_provider_dependency, None)
        cast_app.dependency_overrides.pop(get_vector_store_dependency, None)


def register_and_login(
    client: TestClient,
    *,
    username: str,
    email: str,
) -> dict[str, str]:
    password = "123456"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 201
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
        json={"name": "索引测试知识库"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload_document(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
) -> int:
    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={
            "file": (
                "index-test.txt",
                "项目代号 PKH-2026。\n\n核心版本计划在 14 天内完成。".encode(),
                "text/plain",
            )
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def prepare_document(
    client: TestClient,
    headers: dict[str, str],
    *,
    process: bool = True,
) -> tuple[int, int]:
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload_document(client, headers, knowledge_base_id)
    if process:
        response = client.post(
            f"/api/v1/documents/{document_id}/process",
            headers=headers,
        )
        assert response.status_code == 200
    return knowledge_base_id, document_id


def test_completed_document_can_be_indexed(
    indexing_context: tuple[
        TestClient,
        sessionmaker[Session],
        FakeEmbeddingProvider,
        FakeVectorStore,
    ],
) -> None:
    client, testing_session, provider, vector_store = indexing_context
    headers = register_and_login(
        client,
        username="index-owner",
        email="index-owner@example.com",
    )
    _, document_id = prepare_document(client, headers)

    def assert_indexing_state() -> None:
        with testing_session() as db:
            document = db.get(Document, document_id)
            assert document is not None
            assert document.index_status == DocumentIndexStatus.INDEXING

    provider.before_embed = assert_indexing_state
    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 200
    assert response.json()["index_status"] == "indexed"
    assert response.json()["vector_count"] == response.json()["chunk_count"]
    assert response.json()["embedding_model"] == "test-embedding-v1"
    assert vector_store.count_by_document(document_id, 1) == response.json()["chunk_count"]
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        assert document.index_status == DocumentIndexStatus.INDEXED
        assert document.indexed_at is not None


def test_pending_document_cannot_be_indexed(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, _ = indexing_context
    headers = register_and_login(client, username="pending", email="pending@example.com")
    _, document_id = prepare_document(client, headers, process=False)

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "Document must be processed before indexing"


def test_completed_document_without_chunks_cannot_be_indexed(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, _, _ = indexing_context
    headers = register_and_login(client, username="no-chunks", email="no-chunks@example.com")
    _, document_id = prepare_document(client, headers, process=False)
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        document.status = DocumentStatus.COMPLETED
        db.commit()

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "Document has no chunks to index"


def test_repeated_indexing_does_not_duplicate_vectors(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, vector_store = indexing_context
    headers = register_and_login(client, username="repeat", email="repeat@example.com")
    _, document_id = prepare_document(client, headers)

    first = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    second = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert first.status_code == second.status_code == 200
    assert vector_store.count_by_document(document_id, 1) == first.json()["chunk_count"]


def test_reindex_replaces_old_vector_content(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, _, vector_store = indexing_context
    headers = register_and_login(client, username="replace", email="replace@example.com")
    _, document_id = prepare_document(client, headers)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200

    with testing_session() as db:
        chunk = db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).scalars().first()
        assert chunk is not None
        chunk.content = "替换后的文本片段"
        chunk.character_count = len(chunk.content)
        chunk.content_hash = "1" * 64
        db.commit()
        chunk_id = chunk.id

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 200
    assert vector_store.records[f"chunk:{chunk_id}"].content == "替换后的文本片段"


def test_embedding_failure_marks_index_failed(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, provider, vector_store = indexing_context
    headers = register_and_login(client, username="embed-fail", email="embed-fail@example.com")
    _, document_id = prepare_document(client, headers)
    provider.fail = True

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 502
    assert vector_store.count_by_document(document_id, 1) == 0
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        assert document.index_status == DocumentIndexStatus.FAILED
        assert document.index_error_message == response.json()["detail"]


def test_vector_upsert_failure_marks_index_failed(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, _, vector_store = indexing_context
    headers = register_and_login(client, username="store-fail", email="store-fail@example.com")
    _, document_id = prepare_document(client, headers)
    vector_store.fail_upsert = True

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 502
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        assert document.index_status == DocumentIndexStatus.FAILED


def test_partial_failure_can_be_retried(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, vector_store = indexing_context
    headers = register_and_login(client, username="partial", email="partial@example.com")
    _, document_id = prepare_document(client, headers)
    vector_store.partially_fail_upsert = True

    failed = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    assert failed.status_code == 502
    assert vector_store.count_by_document(document_id, 1) == 0

    vector_store.partially_fail_upsert = False
    retried = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    assert retried.status_code == 200
    assert vector_store.count_by_document(document_id, 1) == retried.json()["chunk_count"]


def test_other_user_cannot_index_document(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, _ = indexing_context
    owner_headers = register_and_login(client, username="owner-a", email="owner-a@example.com")
    other_headers = register_and_login(client, username="owner-b", email="owner-b@example.com")
    _, document_id = prepare_document(client, owner_headers)

    response = client.post(
        f"/api/v1/documents/{document_id}/index",
        headers=other_headers,
    )

    assert response.status_code == 404


def test_index_status_returns_database_and_vector_counts(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, _ = indexing_context
    headers = register_and_login(client, username="status", email="status@example.com")
    _, document_id = prepare_document(client, headers)
    indexed = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    assert indexed.status_code == 200

    response = client.get(
        f"/api/v1/documents/{document_id}/index-status",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["processing_status"] == "completed"
    assert response.json()["index_status"] == "indexed"
    assert response.json()["chunk_count"] == response.json()["vector_count"]
    assert response.json()["embedding_model"] == "test-embedding-v1"


def test_delete_document_removes_vectors(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, vector_store = indexing_context
    headers = register_and_login(client, username="delete-doc", email="delete-doc@example.com")
    _, document_id = prepare_document(client, headers)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200

    response = client.delete(f"/api/v1/documents/{document_id}", headers=headers)

    assert response.status_code == 204
    assert vector_store.count_by_document(document_id, 1) == 0


def test_document_delete_is_rejected_when_vector_cleanup_fails(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, _, vector_store = indexing_context
    headers = register_and_login(client, username="delete-fail", email="delete-fail@example.com")
    _, document_id = prepare_document(client, headers)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200
    vector_store.fail_delete = True

    response = client.delete(f"/api/v1/documents/{document_id}", headers=headers)

    assert response.status_code == 503
    with testing_session() as db:
        assert db.get(Document, document_id) is not None


def test_delete_knowledge_base_removes_vectors(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, _, _, vector_store = indexing_context
    headers = register_and_login(client, username="delete-kb", email="delete-kb@example.com")
    knowledge_base_id, document_id = prepare_document(client, headers)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200

    response = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert vector_store.records == {}


def test_knowledge_base_delete_is_rejected_when_vector_cleanup_fails(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, _, vector_store = indexing_context
    headers = register_and_login(client, username="delete-kb-fail", email="delete-kb-fail@example.com")
    knowledge_base_id, document_id = prepare_document(client, headers)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200
    vector_store.fail_delete = True

    response = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    )

    assert response.status_code == 503
    with testing_session() as db:
        assert db.get(Document, document_id) is not None


def test_reprocessing_invalidates_existing_index(
    indexing_context: tuple[TestClient, sessionmaker[Session], FakeEmbeddingProvider, FakeVectorStore],
) -> None:
    client, testing_session, _, vector_store = indexing_context
    headers = register_and_login(client, username="reprocess", email="reprocess@example.com")
    _, document_id = prepare_document(client, headers)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200

    response = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)

    assert response.status_code == 200
    assert vector_store.count_by_document(document_id, 1) == 0
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        assert document.status == DocumentStatus.COMPLETED
        assert document.index_status == DocumentIndexStatus.NOT_INDEXED
        assert document.embedding_model is None
        assert document.indexed_at is None
