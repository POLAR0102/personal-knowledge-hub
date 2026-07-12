from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import KnowledgeBase


def register_and_login(
    client: TestClient,
    *,
    username: str,
    email: str,
) -> dict[str, str]:
    password = "123456"
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return {
        "Authorization": f"Bearer {login_response.json()['access_token']}"
    }


def test_knowledge_base_crud(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = register_and_login(
        client,
        username="owner",
        email="owner@example.com",
    )

    create_response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "毕业设计资料", "description": "项目相关文档"},
    )
    assert create_response.status_code == 201
    knowledge_base_id = create_response.json()["id"]
    assert create_response.json()["name"] == "毕业设计资料"

    list_response = client.get("/api/v1/knowledge-bases", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == knowledge_base_id

    get_response = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    )
    assert get_response.status_code == 200

    update_response = client.put(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
        json={"name": "更新后的资料库", "description": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "更新后的资料库"
    assert update_response.json()["description"] is None

    delete_response = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    missing_response = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    )
    assert missing_response.status_code == 404


def test_knowledge_base_list_is_paginated_and_sorted_by_updated_at(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = client_and_session
    headers = register_and_login(
        client,
        username="owner",
        email="owner@example.com",
    )
    for name in ["第一库", "第二库", "第三库"]:
        response = client.post(
            "/api/v1/knowledge-bases",
            headers=headers,
            json={"name": name},
        )
        assert response.status_code == 201

    now = datetime.now(timezone.utc)
    with testing_session() as db:
        knowledge_bases = list(
            db.execute(select(KnowledgeBase).order_by(KnowledgeBase.id)).scalars()
        )
        knowledge_bases[0].updated_at = now - timedelta(days=2)
        knowledge_bases[1].updated_at = now
        knowledge_bases[2].updated_at = now - timedelta(days=1)
        db.commit()

    first_page = client.get(
        "/api/v1/knowledge-bases?page=1&page_size=2",
        headers=headers,
    )
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert first_page.json()["page"] == 1
    assert first_page.json()["page_size"] == 2
    assert [item["name"] for item in first_page.json()["items"]] == [
        "第二库",
        "第三库",
    ]

    second_page = client.get(
        "/api/v1/knowledge-bases?page=2&page_size=2",
        headers=headers,
    )
    assert [item["name"] for item in second_page.json()["items"]] == [
        "第一库"
    ]


def test_other_user_cannot_access_modify_or_delete_knowledge_base(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    user_a_headers = register_and_login(
        client,
        username="user-a",
        email="user-a@example.com",
    )
    user_b_headers = register_and_login(
        client,
        username="user-b",
        email="user-b@example.com",
    )

    create_response = client.post(
        "/api/v1/knowledge-bases",
        headers=user_a_headers,
        json={"name": "用户 A 的知识库"},
    )
    assert create_response.status_code == 201
    knowledge_base_id = create_response.json()["id"]

    view_response = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=user_b_headers,
    )
    assert view_response.status_code == 404

    update_response = client.put(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=user_b_headers,
        json={"name": "恶意修改"},
    )
    assert update_response.status_code == 404

    delete_response = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=user_b_headers,
    )
    assert delete_response.status_code == 404

    owner_response = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=user_a_headers,
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["name"] == "用户 A 的知识库"

    user_b_list = client.get(
        "/api/v1/knowledge-bases",
        headers=user_b_headers,
    )
    assert user_b_list.json()["total"] == 0


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/api/v1/knowledge-bases", {"name": "未登录"}),
        ("get", "/api/v1/knowledge-bases", None),
        ("get", "/api/v1/knowledge-bases/1", None),
        ("put", "/api/v1/knowledge-bases/1", {"name": "未登录"}),
        ("delete", "/api/v1/knowledge-bases/1", None),
    ],
)
def test_knowledge_base_endpoints_require_authentication(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    method: str,
    path: str,
    json_body: dict[str, str] | None,
) -> None:
    client, _ = client_and_session

    response = client.request(method, path, json=json_body)

    assert response.status_code == 401


def test_knowledge_base_validation(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    headers = register_and_login(
        client,
        username="owner",
        email="owner@example.com",
    )

    empty_name = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "   "},
    )
    long_name = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "x" * 101},
    )
    long_description = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "合法名称", "description": "x" * 501},
    )

    assert empty_name.status_code == 422
    assert long_name.status_code == 422
    assert long_description.status_code == 422
