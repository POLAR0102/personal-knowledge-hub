from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.ai.embeddings import EmbeddingProvider
from app.ai.llm import ChatMessage, ChatModelProvider, ChatModelResult
from app.ai.vector_store import (
    CollectionHealth,
    SearchResult,
    VectorRecord,
    VectorStore,
)
from app.api.dependencies import (
    get_chat_model_provider_dependency,
    get_conversation_rag_provider_loader_dependency,
    get_embedding_provider_dependency,
    get_vector_store_dependency,
)
from app.core.config import get_settings
from app.main import app


class DeterministicEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    @property
    def model_name(self) -> str:
        return "e2e-embedding-v1"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        checksum = sum(ord(character) for character in text)
        return [float(checksum % 997) / 997, float(len(text) % 101) / 101]


class InMemoryVectorStore(VectorStore):
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
        matching_records = [
            record
            for record in self.records.values()
            if record.user_id == user_id
            and record.knowledge_base_id == knowledge_base_id
            and (
                embedding_model is None
                or record.embedding_model == embedding_model
            )
        ]
        ranked_records = sorted(
            matching_records,
            key=lambda record: self._distance(query_vector, record.embedding),
        )[:top_k]
        return [
            SearchResult(
                chunk_id=record.chunk_id,
                document_id=record.document_id,
                filename=record.filename,
                content=record.content,
                chunk_index=record.chunk_index,
                page_number=record.page_number,
                section_title=record.section_title,
                distance=self._distance(query_vector, record.embedding),
            )
            for record in ranked_records
        ]

    def count_by_document(self, document_id: int, user_id: int) -> int:
        return sum(
            record.document_id == document_id and record.user_id == user_id
            for record in self.records.values()
        )

    def collection_health(self) -> CollectionHealth:
        return CollectionHealth(healthy=True, record_count=len(self.records))

    def close(self) -> None:
        return None

    @staticmethod
    def _distance(left: list[float], right: list[float]) -> float:
        return sum((left_value - right_value) ** 2 for left_value, right_value in zip(left, right))


class DeterministicChatModel(ChatModelProvider):
    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []

    @property
    def model_name(self) -> str:
        return "e2e-chat-v1"

    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ChatModelResult:
        self.calls.append(messages)
        if "固定工作流内容整理助手" in messages[0].content:
            content = (
                "# 项目知识总结\n\n"
                "## 主题概述\n\n"
                "项目代号是 PKH-2026。[来源 1]\n\n"
                "## 核心知识点\n\n"
                "系统使用 React、FastAPI、ChromaDB 和 RAG。[来源 1]\n\n"
                "## 关键概念\n\n"
                "核心版本计划在 14 天内完成。[来源 1]\n\n"
                "## 引用来源\n\n- [来源 1]"
            )
        else:
            content = "项目代号是 PKH-2026。[来源 1]"
        return ChatModelResult(content=content, model=self.model_name)


@pytest.fixture
def core_e2e_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[
    tuple[
        TestClient,
        DeterministicEmbeddingProvider,
        InMemoryVectorStore,
        DeterministicChatModel,
    ],
    None,
    None,
]:
    client, _ = client_and_session
    embedding_provider = DeterministicEmbeddingProvider()
    vector_store = InMemoryVectorStore()
    chat_model = DeterministicChatModel()

    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(
        "app.services.document_processing.get_vector_store",
        lambda: vector_store,
    )
    app.dependency_overrides[get_embedding_provider_dependency] = (
        lambda: embedding_provider
    )
    app.dependency_overrides[get_vector_store_dependency] = lambda: vector_store
    app.dependency_overrides[get_chat_model_provider_dependency] = lambda: chat_model
    app.dependency_overrides[
        get_conversation_rag_provider_loader_dependency
    ] = lambda: (lambda: (embedding_provider, vector_store, chat_model))

    try:
        yield client, embedding_provider, vector_store, chat_model
    finally:
        app.dependency_overrides.pop(get_embedding_provider_dependency, None)
        app.dependency_overrides.pop(get_vector_store_dependency, None)
        app.dependency_overrides.pop(get_chat_model_provider_dependency, None)
        app.dependency_overrides.pop(
            get_conversation_rag_provider_loader_dependency,
            None,
        )


def test_core_api_journey_from_registration_to_agent_note(
    core_e2e_context: tuple[
        TestClient,
        DeterministicEmbeddingProvider,
        InMemoryVectorStore,
        DeterministicChatModel,
    ],
) -> None:
    client, embedding_provider, vector_store, chat_model = core_e2e_context
    password = "123456"

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "username": "e2e-user",
            "email": "e2e@example.com",
            "password": password,
            "confirm_password": password,
        },
    )
    assert registered.status_code == 201

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "e2e@example.com", "password": password},
    )
    assert logged_in.status_code == 200
    headers = {
        "Authorization": f"Bearer {logged_in.json()['access_token']}"
    }

    created_knowledge_base = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "E2E 毕业设计资料"},
    )
    assert created_knowledge_base.status_code == 201
    knowledge_base_id = created_knowledge_base.json()["id"]

    source_text = (
        "智能个人知识库系统的项目代号为 PKH-2026。\n\n"
        "项目核心技术包括 React、FastAPI、ChromaDB 和 RAG。\n\n"
        "核心版本计划在 14 天内完成。\n\n"
        "项目负责人为测试用户张三。"
    )
    uploaded = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={
            "file": (
                "e2e-project.txt",
                source_text.encode("utf-8"),
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    assert uploaded.json()["status"] == "pending"

    processed = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )
    assert processed.status_code == 200
    assert processed.json()["status"] == "completed"
    assert processed.json()["chunk_count"] >= 1

    indexed = client.post(
        f"/api/v1/documents/{document_id}/index",
        headers=headers,
    )
    assert indexed.status_code == 200
    assert indexed.json()["index_status"] == "indexed"
    assert indexed.json()["vector_count"] == processed.json()["chunk_count"]
    assert vector_store.count_by_document(document_id, registered.json()["id"]) == (
        processed.json()["chunk_count"]
    )

    answered = client.post(
        "/api/v1/rag/query",
        headers=headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "question": "项目代号是什么？",
            "top_k": 4,
        },
    )
    assert answered.status_code == 200
    answer_body = answered.json()
    assert answer_body["answer"] == "项目代号是 PKH-2026。[来源 1]"
    assert answer_body["retrieval_count"] >= 1
    assert answer_body["model"] == chat_model.model_name
    assert len(answer_body["citations"]) == 1
    assert answer_body["citations"][0]["document_id"] == document_id
    assert answer_body["citations"][0]["filename"] == "e2e-project.txt"
    assert "PKH-2026" in answer_body["citations"][0]["content"]

    created_task = client.post(
        "/api/v1/agent/tasks",
        headers=headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "task_type": "summary",
            "task_input": "总结知识库中的项目关键信息",
        },
    )
    assert created_task.status_code == 201
    task_body = created_task.json()
    assert task_body["status"] == "completed"
    assert "# 项目知识总结" in task_body["result_content"]
    assert task_body["citations"][0]["document_id"] == document_id

    saved_note = client.post(
        f"/api/v1/agent/tasks/{task_body['id']}/save-note",
        headers=headers,
    )
    assert saved_note.status_code == 200
    note_body = saved_note.json()
    assert note_body["source_type"] == "agent"
    assert note_body["source_agent_task_id"] == task_body["id"]
    assert note_body["content"] == task_body["result_content"]

    loaded_note = client.get(
        f"/api/v1/notes/{note_body['id']}",
        headers=headers,
    )
    assert loaded_note.status_code == 200
    assert loaded_note.json() == note_body
    assert len(embedding_provider.document_calls) == 1
    assert embedding_provider.query_calls == [
        "项目代号是什么？",
        "总结知识库中的项目关键信息",
    ]
    assert len(chat_model.calls) == 2
