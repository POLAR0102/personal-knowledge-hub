from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.llm import (
    ChatMessage,
    ChatModelProvider,
    ChatModelRequestError,
    ChatModelResult,
)
from app.ai.vector_store import SearchResult
from app.api.dependencies import get_conversation_rag_provider_loader_dependency
from app.db.models import AgentTask, AgentTaskStatus, Note
from app.main import app
from app.repositories.agent_task import AgentTaskRepository
from app.services import agent_task as agent_task_service
from app.services.semantic_search import (
    SemanticSearchDependencyError,
    SemanticSearchResult,
)


class SearchStub:
    def __init__(self) -> None:
        self.results = [
            SearchResult(
                chunk_id=11,
                document_id=7,
                filename="FastAPI资料.md",
                content="FastAPI 使用类型提示和依赖注入构建 API。",
                chunk_index=2,
                page_number=None,
                section_title="FastAPI 基础",
                distance=0.12,
            )
        ]
        self.fail = False
        self.calls: list[tuple[int, int, str, int]] = []

    def __call__(
        self,
        _db: object,
        owner: object,
        **kwargs: object,
    ) -> SemanticSearchResult:
        user_id = int(str(getattr(owner, "id")))
        knowledge_base_id = int(str(kwargs["knowledge_base_id"]))
        query = str(kwargs["query"])
        top_k = int(str(kwargs["top_k"]))
        self.calls.append((user_id, knowledge_base_id, query, top_k))
        if self.fail:
            raise SemanticSearchDependencyError("private retrieval failure")
        return SemanticSearchResult(
            query=query,
            knowledge_base_id=knowledge_base_id,
            results=self.results[:top_k],
        )


class FakeChatModel(ChatModelProvider):
    def __init__(self) -> None:
        self.content = (
            "# FastAPI 总结\n\n"
            "FastAPI 支持类型提示和依赖注入。[来源 1]\n\n"
            "## 引用来源\n\n- [来源 1]"
        )
        self.fail = False
        self.calls: list[list[ChatMessage]] = []

    @property
    def model_name(self) -> str:
        return "fake-chat"

    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> ChatModelResult:
        self.calls.append(messages)
        if self.fail:
            raise ChatModelRequestError("private provider failure")
        return ChatModelResult(content=self.content, model=self.model_name)


@pytest.fixture
def agent_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[
    tuple[TestClient, sessionmaker[Session], SearchStub, FakeChatModel],
    None,
    None,
]:
    client, session_factory = client_and_session
    search_stub = SearchStub()
    chat_model = FakeChatModel()
    monkeypatch.setattr(agent_task_service, "semantic_search", search_stub)
    app.dependency_overrides[
        get_conversation_rag_provider_loader_dependency
    ] = lambda: (lambda: (object(), object(), chat_model))
    try:
        yield client, session_factory, search_stub, chat_model
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
        json={"name": "Agent 测试知识库"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_task(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    *,
    task_type: str = "summary",
    task_input: str = "总结知识库中的 FastAPI 内容",
) -> object:
    return client.post(
        "/api/v1/agent/tasks",
        headers=headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "task_type": task_type,
            "task_input": task_input,
        },
    )


@pytest.mark.parametrize(
    ("task_type", "expected_structure"),
    [
        ("summary", "核心知识点"),
        ("study_plan", "每日任务"),
        ("topic_note", "注意事项"),
    ],
)
def test_three_task_types_complete_with_fixed_prompt(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
    task_type: str,
    expected_structure: str,
) -> None:
    client, _, search_stub, chat_model = agent_context
    headers = register_and_login(
        client,
        username=f"agent-{task_type}",
        email=f"agent-{task_type}@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)

    response = create_task(
        client,
        headers,
        knowledge_base_id,
        task_type=task_type,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["result_content"] == chat_model.content
    assert body["error_message"] is None
    assert body["started_at"] is not None
    assert body["completed_at"] is not None
    assert search_stub.calls[-1][1:] == (
        knowledge_base_id,
        "总结知识库中的 FastAPI 内容",
        8,
    )
    system_prompt = chat_model.calls[-1][0].content
    assert expected_structure in system_prompt
    assert "只输出最终 Markdown" in system_prompt
    assert "不得输出思考过程" in system_prompt


def test_no_search_results_completes_without_calling_chat_model(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, _, search_stub, chat_model = agent_context
    search_stub.results = []
    headers = register_and_login(
        client,
        username="agent-empty",
        email="agent-empty@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)

    response = create_task(client, headers, knowledge_base_id)

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert "资料不足" in response.json()["result_content"]
    assert response.json()["citations"] == []
    assert chat_model.calls == []


def test_chat_failure_marks_task_failed_without_private_details(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, session_factory, _, chat_model = agent_context
    chat_model.fail = True
    headers = register_and_login(
        client,
        username="agent-failure",
        email="agent-failure@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)

    response = create_task(client, headers, knowledge_base_id)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["result_content"] is None
    assert body["citations"] == []
    assert body["error_message"] == "Unable to generate Agent result"
    assert "private provider failure" not in response.text
    with session_factory() as db:
        task = db.get(AgentTask, body["id"])
        assert task is not None
        assert task.status == AgentTaskStatus.FAILED


def test_retrieval_failure_marks_task_failed_without_private_details(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, _, search_stub, chat_model = agent_context
    search_stub.fail = True
    headers = register_and_login(
        client,
        username="agent-search-failure",
        email="agent-search-failure@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)

    response = create_task(client, headers, knowledge_base_id)

    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["error_message"] == (
        "Unable to retrieve knowledge base content"
    )
    assert "private retrieval failure" not in response.text
    assert chat_model.calls == []


def test_failed_task_can_retry_without_creating_duplicate_task(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, session_factory, _, chat_model = agent_context
    chat_model.fail = True
    headers = register_and_login(
        client,
        username="agent-retry",
        email="agent-retry@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)
    failed = create_task(client, headers, knowledge_base_id)
    task_id = failed.json()["id"]

    chat_model.fail = False
    retried = client.post(
        f"/api/v1/agent/tasks/{task_id}/retry",
        headers=headers,
    )

    assert retried.status_code == 200
    assert retried.json()["id"] == task_id
    assert retried.json()["status"] == "completed"
    assert retried.json()["error_message"] is None
    with session_factory() as db:
        assert db.scalar(select(func.count(AgentTask.id))) == 1


def test_non_failed_task_cannot_retry(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, session_factory, _, _ = agent_context
    headers = register_and_login(
        client,
        username="agent-running",
        email="agent-running@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)
    task_id = create_task(client, headers, knowledge_base_id).json()["id"]
    with session_factory() as db:
        task = db.get(AgentTask, task_id)
        assert task is not None
        task.status = AgentTaskStatus.RUNNING
        db.commit()

    response = client.post(
        f"/api/v1/agent/tasks/{task_id}/retry",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only failed Agent tasks can be retried"


def test_agent_task_execution_claim_only_succeeds_once(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, session_factory, _, chat_model = agent_context
    chat_model.fail = True
    headers = register_and_login(
        client,
        username="agent-claim",
        email="agent-claim@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)
    task_id = create_task(client, headers, knowledge_base_id).json()["id"]

    with session_factory() as first_db:
        task = first_db.get(AgentTask, task_id)
        assert task is not None
        first_claim = AgentTaskRepository(first_db).claim_for_execution(
            task_id=task_id,
            user_id=task.user_id,
            expected_status=AgentTaskStatus.FAILED,
            started_at=datetime.now(timezone.utc),
        )
        first_db.commit()

    with session_factory() as second_db:
        task = second_db.get(AgentTask, task_id)
        assert task is not None
        second_claim = AgentTaskRepository(second_db).claim_for_execution(
            task_id=task_id,
            user_id=task.user_id,
            expected_status=AgentTaskStatus.FAILED,
            started_at=datetime.now(timezone.utc),
        )
        second_db.rollback()

    assert first_claim is True
    assert second_claim is False
    with session_factory() as db:
        claimed_task = db.get(AgentTask, task_id)
        assert claimed_task is not None
        assert claimed_task.status == AgentTaskStatus.RUNNING
        assert claimed_task.error_message is None
        assert claimed_task.result_content is None
        assert claimed_task.citations_json is None
        assert claimed_task.started_at is not None
        assert claimed_task.completed_at is None


def test_citation_snapshot_comes_from_real_search_result(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, _, search_stub, _ = agent_context
    headers = register_and_login(
        client,
        username="agent-citation",
        email="agent-citation@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)

    body = create_task(client, headers, knowledge_base_id).json()

    source = search_stub.results[0]
    assert body["citations"] == [
        {
            "source_number": 1,
            "chunk_id": source.chunk_id,
            "document_id": source.document_id,
            "filename": source.filename,
            "content": source.content,
            "chunk_index": source.chunk_index,
            "page_number": source.page_number,
            "section_title": source.section_title,
            "distance": source.distance,
        }
    ]


def test_list_get_and_user_knowledge_base_isolation(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, _, _, chat_model = agent_context
    owner_headers = register_and_login(
        client,
        username="agent-owner",
        email="agent-owner@example.com",
    )
    other_headers = register_and_login(
        client,
        username="agent-other",
        email="agent-other@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, owner_headers)
    task_id = create_task(client, owner_headers, knowledge_base_id).json()["id"]

    listing = client.get(
        f"/api/v1/agent/tasks?knowledge_base_id={knowledge_base_id}",
        headers=owner_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == task_id
    assert client.get(
        f"/api/v1/agent/tasks/{task_id}",
        headers=other_headers,
    ).status_code == 404
    assert create_task(
        client,
        other_headers,
        knowledge_base_id,
    ).status_code == 404
    assert client.get(
        f"/api/v1/agent/tasks?knowledge_base_id={knowledge_base_id}",
        headers=other_headers,
    ).status_code == 404
    assert len(chat_model.calls) == 1


def test_completed_task_save_note_is_idempotent(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, session_factory, _, _ = agent_context
    headers = register_and_login(
        client,
        username="agent-note",
        email="agent-note@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)
    task_id = create_task(client, headers, knowledge_base_id).json()["id"]

    first = client.post(
        f"/api/v1/agent/tasks/{task_id}/save-note",
        headers=headers,
    )
    second = client.post(
        f"/api/v1/agent/tasks/{task_id}/save-note",
        headers=headers,
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["source_type"] == "agent"
    assert first.json()["source_agent_task_id"] == task_id
    with session_factory() as db:
        assert db.scalar(select(func.count(Note.id))) == 1


def test_failed_task_cannot_be_saved_as_note(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
) -> None:
    client, _, _, chat_model = agent_context
    chat_model.fail = True
    headers = register_and_login(
        client,
        username="agent-note-failed",
        email="agent-note-failed@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers)
    task_id = create_task(client, headers, knowledge_base_id).json()["id"]

    response = client.post(
        f"/api/v1/agent/tasks/{task_id}/save-note",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only completed Agent tasks can be saved as a note"
    )


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "post",
            "/api/v1/agent/tasks",
            {
                "knowledge_base_id": 1,
                "task_type": "summary",
                "task_input": "总结 FastAPI",
            },
        ),
        ("get", "/api/v1/agent/tasks", None),
        ("get", "/api/v1/agent/tasks/1", None),
        ("post", "/api/v1/agent/tasks/1/retry", None),
        ("post", "/api/v1/agent/tasks/1/save-note", None),
    ],
)
def test_agent_endpoints_require_authentication(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    client, _ = client_and_session
    response = client.request(method, path, json=payload)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"knowledge_base_id": 1, "task_type": "unknown", "task_input": "任务"},
        {"knowledge_base_id": 1, "task_type": "summary", "task_input": ""},
        {
            "knowledge_base_id": 1,
            "task_type": "summary",
            "task_input": "x" * 1001,
        },
    ],
)
def test_invalid_task_input_returns_422(
    agent_context: tuple[
        TestClient,
        sessionmaker[Session],
        SearchStub,
        FakeChatModel,
    ],
    payload: dict[str, object],
) -> None:
    client, _, _, _ = agent_context
    headers = register_and_login(
        client,
        username=f"agent-invalid-{len(str(payload))}",
        email=f"agent-invalid-{len(str(payload))}@example.com",
    )
    response = client.post("/api/v1/agent/tasks", headers=headers, json=payload)
    assert response.status_code == 422
