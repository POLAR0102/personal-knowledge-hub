from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskType,
    Note,
    NoteSourceType,
    User,
)
from app.services.note import save_agent_task_as_note


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


def create_knowledge_base(
    client: TestClient,
    headers: dict[str, str],
    name: str,
) -> int:
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_note(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    *,
    title: str,
    content: str = "# Markdown\n\n笔记正文",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/notes",
        headers=headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "title": title,
            "content": content,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_note_crud_and_manual_source(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = register_and_login(
        client,
        username="note-owner",
        email="note-owner@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "笔记知识库")

    created = create_note(
        client,
        headers,
        knowledge_base_id,
        title="FastAPI 笔记",
    )
    note_id = created["id"]
    assert created["source_type"] == "manual"
    assert created["source_agent_task_id"] is None

    detail = client.get(f"/api/v1/notes/{note_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["content"] == "# Markdown\n\n笔记正文"

    updated = client.put(
        f"/api/v1/notes/{note_id}",
        headers=headers,
        json={"title": "更新后的笔记", "content": "更新后的 Markdown"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "更新后的笔记"
    assert updated.json()["content"] == "更新后的 Markdown"
    assert updated.json()["source_type"] == "manual"

    assert client.delete(
        f"/api/v1/notes/{note_id}",
        headers=headers,
    ).status_code == 204
    assert client.get(
        f"/api/v1/notes/{note_id}",
        headers=headers,
    ).status_code == 404


def test_note_list_pagination_filter_and_updated_order(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = client_and_session
    headers = register_and_login(
        client,
        username="note-list",
        email="note-list@example.com",
    )
    first_kb = create_knowledge_base(client, headers, "知识库一")
    second_kb = create_knowledge_base(client, headers, "知识库二")
    first = create_note(client, headers, first_kb, title="第一条")
    second = create_note(client, headers, first_kb, title="第二条")
    create_note(client, headers, second_kb, title="其他知识库")

    now = datetime.now(timezone.utc)
    with session_factory() as db:
        first_note = db.get(Note, first["id"])
        second_note = db.get(Note, second["id"])
        assert first_note is not None and second_note is not None
        first_note.updated_at = now
        second_note.updated_at = now - timedelta(days=1)
        db.commit()

    filtered = client.get(
        f"/api/v1/notes?knowledge_base_id={first_kb}&page=1&page_size=1",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 2
    assert filtered.json()["items"][0]["id"] == first["id"]

    second_page = client.get(
        f"/api/v1/notes?knowledge_base_id={first_kb}&page=2&page_size=1",
        headers=headers,
    )
    assert second_page.json()["items"][0]["id"] == second["id"]

    all_notes = client.get("/api/v1/notes", headers=headers)
    assert all_notes.json()["total"] == 3


def test_note_and_knowledge_base_isolation(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    owner_headers = register_and_login(
        client,
        username="note-user-a",
        email="note-user-a@example.com",
    )
    other_headers = register_and_login(
        client,
        username="note-user-b",
        email="note-user-b@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, owner_headers, "用户 A 知识库")
    note = create_note(
        client,
        owner_headers,
        knowledge_base_id,
        title="用户 A 笔记",
    )

    assert client.get(
        f"/api/v1/notes/{note['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.put(
        f"/api/v1/notes/{note['id']}",
        headers=other_headers,
        json={"title": "越权修改"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/notes/{note['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/notes",
        headers=other_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "title": "越权创建",
            "content": "内容",
        },
    ).status_code == 404
    assert client.get(
        f"/api/v1/notes?knowledge_base_id={knowledge_base_id}",
        headers=other_headers,
    ).status_code == 404


def test_delete_knowledge_base_cascades_notes(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = client_and_session
    email = "note-cascade@example.com"
    headers = register_and_login(
        client,
        username="note-cascade",
        email=email,
    )
    knowledge_base_id = create_knowledge_base(client, headers, "级联删除知识库")
    manual_note = create_note(client, headers, knowledge_base_id, title="将被删除")
    with session_factory() as db:
        owner = db.scalar(select(User).where(User.email == email))
        assert owner is not None
        task = AgentTask(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
            task_type=AgentTaskType.SUMMARY,
            task_input="总结级联删除资料",
            status=AgentTaskStatus.COMPLETED,
            result_content="# Agent 笔记",
            citations_json=[],
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        agent_note = save_agent_task_as_note(db, owner, task.id)
        task_id = task.id
        agent_note_id = agent_note.id

    assert client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    ).status_code == 204
    with session_factory() as db:
        assert db.get(Note, manual_note["id"]) is None
        assert db.get(Note, agent_note_id) is None
        assert db.get(AgentTask, task_id) is None


def test_save_completed_agent_task_as_note_is_idempotent(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = client_and_session
    email = "agent-note@example.com"
    headers = register_and_login(
        client,
        username="agent-note",
        email=email,
    )
    knowledge_base_id = create_knowledge_base(client, headers, "Agent 知识库")
    result_content = "# 学习计划\n\n- 第一天：FastAPI"

    with session_factory() as db:
        owner = db.scalar(select(User).where(User.email == email))
        assert owner is not None
        task = AgentTask(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
            task_type=AgentTaskType.STUDY_PLAN,
            task_input="根据知识库中的 FastAPI 内容生成七天学习计划",
            status=AgentTaskStatus.COMPLETED,
            result_content=result_content,
            citations_json=[],
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        first_note = save_agent_task_as_note(db, owner, task.id)
        first_note_id = first_note.id
        second_note = save_agent_task_as_note(db, owner, task.id)

        assert second_note.id == first_note_id
        assert second_note.source_type == NoteSourceType.AGENT
        assert second_note.source_agent_task_id == task.id
        assert second_note.content == result_content
        notes = list(db.scalars(select(Note)).all())
        assert len(notes) == 1


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "post",
            "/api/v1/notes",
            {"knowledge_base_id": 1, "title": "笔记", "content": "内容"},
        ),
        ("get", "/api/v1/notes", None),
        ("get", "/api/v1/notes/1", None),
        ("put", "/api/v1/notes/1", {"title": "更新"}),
        ("delete", "/api/v1/notes/1", None),
    ],
)
def test_note_endpoints_require_authentication(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    client, _ = client_and_session
    assert client.request(method, path, json=payload).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"knowledge_base_id": 1, "title": "", "content": "内容"},
        {"knowledge_base_id": 1, "title": "x" * 101, "content": "内容"},
        {"knowledge_base_id": 1, "title": "笔记", "content": "   "},
        {"knowledge_base_id": 0, "title": "笔记", "content": "内容"},
    ],
)
def test_note_create_validation_returns_422(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    payload: dict[str, object],
) -> None:
    client, _ = client_and_session
    headers = register_and_login(
        client,
        username=f"validation-{abs(hash(str(payload)))}"[:30],
        email=f"validation-{abs(hash(str(payload)))}@example.com",
    )
    assert client.post(
        "/api/v1/notes",
        headers=headers,
        json=payload,
    ).status_code == 422
