from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.rag import Citation
from app.ai.llm import ChatModelConfigurationError
from app.ai.vector_store import SearchResult
from app.api.dependencies import (
    get_conversation_rag_provider_loader_dependency,
)
from app.db.models import Conversation, Message, MessageRequestStatus
from app.main import app
from app.services import conversation as conversation_service
from app.services.rag_query import RAGQueryDependencyError, RAGQueryResult


class RAGStub:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, int]] = []
        self.fail = False
        self.unexpected_failure = False

    def __call__(self, _db: object, _owner: object, **kwargs: object) -> RAGQueryResult:
        knowledge_base_id = int(str(kwargs["knowledge_base_id"]))
        question = str(kwargs["question"])
        top_k = int(str(kwargs["top_k"]))
        self.calls.append((knowledge_base_id, question, top_k))
        if self.fail:
            raise RAGQueryDependencyError("Unable to generate RAG answer")
        if self.unexpected_failure:
            raise RuntimeError("unexpected private failure")
        search_result = SearchResult(
            chunk_id=8,
            document_id=3,
            filename="项目说明.txt",
            content="项目代号为 PKH-2026。",
            chunk_index=0,
            page_number=None,
            section_title="项目概况",
            distance=0.14,
        )
        return RAGQueryResult(
            answer="项目代号是 PKH-2026。[来源 1]",
            knowledge_base_id=knowledge_base_id,
            citations=[Citation(source_number=1, result=search_result)],
            retrieval_count=1,
            model="fake-chat",
        )


@pytest.fixture
def conversation_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, sessionmaker[Session], RAGStub], None, None]:
    client, session_factory = client_and_session
    rag_stub = RAGStub()
    monkeypatch.setattr(conversation_service, "answer_question", rag_stub)
    app.dependency_overrides[
        get_conversation_rag_provider_loader_dependency
    ] = lambda: (lambda: (object(), object(), object()))
    try:
        yield client, session_factory, rag_stub
    finally:
        app.dependency_overrides.pop(
            get_conversation_rag_provider_loader_dependency,
            None,
        )


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
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_knowledge_base(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "毕业设计资料"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_conversation(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    title: str = "毕业设计问答",
) -> int:
    response = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "title": title},
    )
    assert response.status_code == 201
    return response.json()["id"]


def send_message(
    client: TestClient,
    headers: dict[str, str],
    conversation_id: int,
    *,
    content: str,
    client_request_id: str,
) -> object:
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "content": content,
            "top_k": 4,
            "client_request_id": client_request_id,
        },
    )


def test_create_list_and_get_conversation(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, _ = conversation_context
    headers = register_and_login(client, username="history", email="history@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    first_id = create_conversation(client, headers, knowledge_base_id, "第一个会话")
    second_id = create_conversation(client, headers, knowledge_base_id, "第二个会话")

    listing = client.get(
        "/api/v1/conversations?page=1&page_size=1",
        headers=headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert listing.json()["page"] == 1
    assert listing.json()["page_size"] == 1
    assert listing.json()["items"][0]["id"] == second_id

    detail = client.get(f"/api/v1/conversations/{first_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["title"] == "第一个会话"
    assert detail.json()["knowledge_base_id"] == knowledge_base_id
    assert detail.json()["messages"] == []


def test_message_saves_answer_citation_snapshot_and_order(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, session_factory, rag_stub = conversation_context
    headers = register_and_login(client, username="message", email="message@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    request_id = str(uuid4())

    response = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=request_id,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_message"]["sequence_number"] == 1
    assert body["user_message"]["request_status"] == "completed"
    assert body["user_message"]["client_request_id"] == request_id
    assert body["user_message"]["citations"] is None
    assert body["assistant_message"]["sequence_number"] == 2
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["model"] == "fake-chat"
    assert body["assistant_message"]["citations"][0] == {
        "source_number": 1,
        "chunk_id": 8,
        "document_id": 3,
        "filename": "项目说明.txt",
        "content": "项目代号为 PKH-2026。",
        "chunk_index": 0,
        "page_number": None,
        "section_title": "项目概况",
        "distance": 0.14,
    }
    assert rag_stub.calls == [(knowledge_base_id, "项目代号是什么？", 4)]

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert [item["sequence_number"] for item in detail.json()["messages"]] == [1, 2]
    with session_factory() as db:
        assistant = db.scalar(
            select(Message).where(Message.sequence_number == 2)
        )
        assert assistant is not None
        assert assistant.citations_json == body["assistant_message"]["citations"]


def test_two_questions_keep_stable_sequence(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, _ = conversation_context
    headers = register_and_login(client, username="sequence", email="sequence@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)

    for content in ("项目代号是什么？", "项目使用什么技术？"):
        assert send_message(
            client,
            headers,
            conversation_id,
            content=content,
            client_request_id=str(uuid4()),
        ).status_code == 201

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    messages = detail.json()["messages"]
    assert [item["sequence_number"] for item in messages] == [1, 2, 3, 4]
    assert [item["role"] for item in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_completed_request_is_idempotent(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, rag_stub = conversation_context
    headers = register_and_login(client, username="duplicate", email="duplicate@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    request_id = str(uuid4())

    first = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=request_id,
    )
    second = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=request_id,
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["user_message"]["id"] == second.json()["user_message"]["id"]
    assert first.json()["assistant_message"]["id"] == second.json()["assistant_message"]["id"]
    assert len(rag_stub.calls) == 1
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert len(detail.json()["messages"]) == 2


def test_reusing_request_id_for_different_content_returns_409(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, _ = conversation_context
    headers = register_and_login(client, username="conflict", email="conflict@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    request_id = str(uuid4())
    assert send_message(
        client,
        headers,
        conversation_id,
        content="问题一",
        client_request_id=request_id,
    ).status_code == 201

    response = send_message(
        client,
        headers,
        conversation_id,
        content="问题二",
        client_request_id=request_id,
    )
    assert response.status_code == 409


def test_rag_failure_keeps_user_message_and_same_request_can_retry(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, rag_stub = conversation_context
    headers = register_and_login(client, username="retry", email="retry@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    request_id = str(uuid4())
    rag_stub.fail = True

    failed = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=request_id,
    )
    assert failed.status_code == 502
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert len(detail.json()["messages"]) == 1
    failed_user = detail.json()["messages"][0]
    assert failed_user["role"] == "user"
    assert failed_user["request_status"] == "failed"

    blocked = send_message(
        client,
        headers,
        conversation_id,
        content="另一个问题",
        client_request_id=str(uuid4()),
    )
    assert blocked.status_code == 409

    rag_stub.fail = False
    retried = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=request_id,
    )
    assert retried.status_code == 201
    assert retried.json()["user_message"]["id"] == failed_user["id"]
    assert retried.json()["user_message"]["request_status"] == "completed"
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert len(detail.json()["messages"]) == 2


def test_provider_configuration_failure_still_saves_retriable_user_message(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, _ = conversation_context
    headers = register_and_login(client, username="config", email="config@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    request_id = str(uuid4())

    def failing_loader() -> tuple[object, object, object]:
        raise ChatModelConfigurationError("private configuration detail")

    app.dependency_overrides[
        get_conversation_rag_provider_loader_dependency
    ] = lambda: failing_loader
    response = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=request_id,
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "RAG service is not configured"
    assert "private configuration detail" not in response.text
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert len(detail.json()["messages"]) == 1
    assert detail.json()["messages"][0]["request_status"] == "failed"
    assert detail.json()["messages"][0]["client_request_id"] == request_id


def test_unexpected_rag_failure_marks_user_message_failed_without_stack_details(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, rag_stub = conversation_context
    headers = register_and_login(client, username="unexpected", email="unexpected@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    rag_stub.unexpected_failure = True

    response = send_message(
        client,
        headers,
        conversation_id,
        content="项目代号是什么？",
        client_request_id=str(uuid4()),
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to generate conversation response"
    assert "unexpected private failure" not in response.text
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    assert len(detail.json()["messages"]) == 1
    assert detail.json()["messages"][0]["request_status"] == "failed"


def test_processing_duplicate_returns_409(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, session_factory, rag_stub = conversation_context
    headers = register_and_login(client, username="processing", email="processing@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    request_id = str(uuid4())
    rag_stub.fail = True
    assert send_message(
        client,
        headers,
        conversation_id,
        content="问题",
        client_request_id=request_id,
    ).status_code == 502
    with session_factory() as db:
        message = db.scalar(select(Message).where(Message.client_request_id == request_id))
        assert message is not None
        message.request_status = MessageRequestStatus.PROCESSING
        db.commit()

    response = send_message(
        client,
        headers,
        conversation_id,
        content="问题",
        client_request_id=request_id,
    )
    assert response.status_code == 409


def test_message_without_client_request_id_is_supported(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, _ = conversation_context
    headers = register_and_login(client, username="no-id", email="no-id@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "项目代号是什么？", "top_k": 4},
    )

    assert response.status_code == 201
    generated_request_id = response.json()["user_message"]["client_request_id"]
    assert generated_request_id is not None
    assert str(UUID(generated_request_id)) == generated_request_id


def test_failed_message_without_client_request_id_can_retry_by_same_content(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, rag_stub = conversation_context
    headers = register_and_login(client, username="no-id-retry", email="no-id-retry@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    payload = {"content": "项目代号是什么？", "top_k": 4}
    rag_stub.fail = True

    failed = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json=payload,
    )
    assert failed.status_code == 502
    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers)
    failed_user_id = detail.json()["messages"][0]["id"]

    rag_stub.fail = False
    retried = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json=payload,
    )
    assert retried.status_code == 201
    assert retried.json()["user_message"]["id"] == failed_user_id


def test_user_and_knowledge_base_isolation_returns_404(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, _, rag_stub = conversation_context
    owner_headers = register_and_login(client, username="owner", email="owner@example.com")
    other_headers = register_and_login(client, username="other", email="other@example.com")
    knowledge_base_id = create_knowledge_base(client, owner_headers)
    conversation_id = create_conversation(client, owner_headers, knowledge_base_id)

    assert client.post(
        "/api/v1/conversations",
        headers=other_headers,
        json={"knowledge_base_id": knowledge_base_id, "title": "越权"},
    ).status_code == 404
    assert client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/conversations/{conversation_id}",
        headers=other_headers,
    ).status_code == 404
    assert send_message(
        client,
        other_headers,
        conversation_id,
        content="越权问题",
        client_request_id=str(uuid4()),
    ).status_code == 404
    assert rag_stub.calls == []


def test_delete_conversation_cascades_messages(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, session_factory, _ = conversation_context
    headers = register_and_login(client, username="delete", email="delete@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    assert send_message(
        client,
        headers,
        conversation_id,
        content="问题",
        client_request_id=str(uuid4()),
    ).status_code == 201

    assert client.delete(
        f"/api/v1/conversations/{conversation_id}",
        headers=headers,
    ).status_code == 204
    with session_factory() as db:
        assert db.get(Conversation, conversation_id) is None
        count = db.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id
            )
        )
        assert count == 0


def test_delete_knowledge_base_cascades_conversation_and_messages(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
) -> None:
    client, session_factory, _ = conversation_context
    headers = register_and_login(client, username="cascade", email="cascade@example.com")
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    assert send_message(
        client,
        headers,
        conversation_id,
        content="问题",
        client_request_id=str(uuid4()),
    ).status_code == 201

    assert client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    ).status_code == 204
    with session_factory() as db:
        assert db.get(Conversation, conversation_id) is None
        count = db.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation_id
            )
        )
        assert count == 0


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/api/v1/conversations", {"knowledge_base_id": 1, "title": "会话"}),
        ("get", "/api/v1/conversations", None),
        ("get", "/api/v1/conversations/1", None),
        ("delete", "/api/v1/conversations/1", None),
        (
            "post",
            "/api/v1/conversations/1/messages",
            {"content": "问题", "client_request_id": str(uuid4())},
        ),
    ],
)
def test_conversation_endpoints_require_authentication(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    client, _, _ = conversation_context
    response = client.request(method, path, json=payload)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"content": ""},
        {"content": "x" * 1001},
        {"content": "问题", "top_k": 0},
        {"content": "问题", "top_k": 11},
        {"content": "问题", "client_request_id": "not-a-uuid"},
    ],
)
def test_invalid_message_input_returns_422(
    conversation_context: tuple[TestClient, sessionmaker[Session], RAGStub],
    payload: dict[str, object],
) -> None:
    client, _, _ = conversation_context
    headers = register_and_login(
        client,
        username=f"invalid-{uuid4().hex[:8]}",
        email=f"invalid-{uuid4().hex[:8]}@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)
    conversation_id = create_conversation(client, headers, knowledge_base_id)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422
