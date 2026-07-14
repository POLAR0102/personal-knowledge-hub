from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, Tag, document_tags


@pytest.fixture
def organization_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path / "uploads")
    client, session_factory = client_and_session
    yield client, session_factory


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


def upload_document(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    filename: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"file": (filename, b"document content", "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


def create_tag(
    client: TestClient,
    headers: dict[str, str],
    name: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/tags",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()


def test_tag_crud_and_pagination(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    headers = register_and_login(
        client,
        username="tag-crud",
        email="tag-crud@example.com",
    )
    python_tag = create_tag(client, headers, "  Python  ")
    fastapi_tag = create_tag(client, headers, "FastAPI")

    listing = client.get("/api/v1/tags?page=1&page_size=1", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert listing.json()["items"][0]["name"] == "FastAPI"
    assert client.get(
        f"/api/v1/tags/{python_tag['id']}",
        headers=headers,
    ).json()["name"] == "Python"

    updated = client.put(
        f"/api/v1/tags/{python_tag['id']}",
        headers=headers,
        json={"name": "Python 3.11"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Python 3.11"
    assert client.delete(
        f"/api/v1/tags/{fastapi_tag['id']}",
        headers=headers,
    ).status_code == 204
    assert client.get(
        f"/api/v1/tags/{fastapi_tag['id']}",
        headers=headers,
    ).status_code == 404


def test_duplicate_tag_name_returns_409_but_other_user_can_reuse_name(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    owner_headers = register_and_login(
        client,
        username="tag-owner",
        email="tag-owner@example.com",
    )
    other_headers = register_and_login(
        client,
        username="tag-other",
        email="tag-other@example.com",
    )
    create_tag(client, owner_headers, "RAG")

    duplicate = client.post(
        "/api/v1/tags",
        headers=owner_headers,
        json={"name": "RAG"},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Tag name already exists"
    assert create_tag(client, other_headers, "RAG")["name"] == "RAG"

    second = create_tag(client, owner_headers, "Existing")
    update_duplicate = client.put(
        f"/api/v1/tags/{second['id']}",
        headers=owner_headers,
        json={"name": "RAG"},
    )
    assert update_duplicate.status_code == 409


@pytest.mark.parametrize("name", ["", "x" * 31])
def test_invalid_tag_name_returns_422(
    organization_context: tuple[TestClient, sessionmaker[Session]],
    name: str,
) -> None:
    client, _ = organization_context
    headers = register_and_login(
        client,
        username=f"tag-invalid-{len(name)}",
        email=f"tag-invalid-{len(name)}@example.com",
    )
    response = client.post(
        "/api/v1/tags",
        headers=headers,
        json={"name": name},
    )
    assert response.status_code == 422


def test_tag_endpoints_are_user_isolated(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    owner_headers = register_and_login(
        client,
        username="tag-private-owner",
        email="tag-private-owner@example.com",
    )
    other_headers = register_and_login(
        client,
        username="tag-private-other",
        email="tag-private-other@example.com",
    )
    tag_id = int(str(create_tag(client, owner_headers, "Private")["id"]))

    assert client.get(f"/api/v1/tags/{tag_id}", headers=other_headers).status_code == 404
    assert client.put(
        f"/api/v1/tags/{tag_id}",
        headers=other_headers,
        json={"name": "Intrusion"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/tags/{tag_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.get("/api/v1/tags", headers=other_headers).json()["total"] == 0


def test_upload_and_existing_knowledge_base_list_include_new_fields(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    headers = register_and_login(
        client,
        username="document-compatible",
        email="document-compatible@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "兼容测试")

    uploaded = upload_document(client, headers, knowledge_base_id, "guide.txt")
    listing = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
    )

    assert uploaded["is_favorite"] is False
    assert uploaded["tags"] == []
    assert listing.status_code == 200
    assert listing.json()["items"][0]["is_favorite"] is False
    assert listing.json()["items"][0]["tags"] == []


def test_cross_knowledge_base_document_list_is_paginated_and_isolated(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    owner_headers = register_and_login(
        client,
        username="library-owner",
        email="library-owner@example.com",
    )
    other_headers = register_and_login(
        client,
        username="library-other",
        email="library-other@example.com",
    )
    first_kb = create_knowledge_base(client, owner_headers, "知识库 A")
    second_kb = create_knowledge_base(client, owner_headers, "知识库 B")
    upload_document(client, owner_headers, first_kb, "first.txt")
    upload_document(client, owner_headers, second_kb, "second.txt")

    response = client.get(
        "/api/v1/documents?page=1&page_size=1",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page_size"] == 1
    assert client.get("/api/v1/documents", headers=other_headers).json()["total"] == 0
    assert client.get(
        f"/api/v1/documents?knowledge_base_id={first_kb}",
        headers=other_headers,
    ).status_code == 404


def test_favorite_update_is_idempotent_and_favorites_list_is_real(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    headers = register_and_login(
        client,
        username="favorite-owner",
        email="favorite-owner@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "收藏测试")
    favorite_id = int(str(upload_document(
        client, headers, knowledge_base_id, "favorite.txt"
    )["id"]))
    upload_document(client, headers, knowledge_base_id, "ordinary.txt")

    for _ in range(2):
        response = client.put(
            f"/api/v1/documents/{favorite_id}/favorite",
            headers=headers,
            json={"is_favorite": True},
        )
        assert response.status_code == 200
        assert response.json()["is_favorite"] is True

    favorites = client.get("/api/v1/documents/favorites", headers=headers)
    assert favorites.status_code == 200
    assert favorites.json()["total"] == 1
    assert favorites.json()["items"][0]["id"] == favorite_id

    unset = client.put(
        f"/api/v1/documents/{favorite_id}/favorite",
        headers=headers,
        json={"is_favorite": False},
    )
    assert unset.status_code == 200
    assert client.get(
        "/api/v1/documents/favorites",
        headers=headers,
    ).json()["total"] == 0


def test_document_tag_add_remove_are_idempotent_and_keep_chunk_count(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = organization_context
    headers = register_and_login(
        client,
        username="document-tag",
        email="document-tag@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "标签测试")
    document_id = int(str(upload_document(
        client, headers, knowledge_base_id, "tagged.txt"
    )["id"]))
    tag_id = int(str(create_tag(client, headers, "FastAPI")["id"]))
    with session_factory() as db:
        document = db.get(Document, document_id)
        assert document is not None
        db.add(
            DocumentChunk(
                user_id=document.user_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                chunk_index=0,
                content="chunk",
                content_hash="a" * 64,
                character_count=5,
            )
        )
        db.commit()

    for _ in range(2):
        added = client.post(
            f"/api/v1/documents/{document_id}/tags/{tag_id}",
            headers=headers,
        )
        assert added.status_code == 200
        assert [
            {"id": item["id"], "name": item["name"]}
            for item in added.json()["tags"]
        ] == [{"id": tag_id, "name": "FastAPI"}]
        assert added.json()["chunk_count"] == 1

    for _ in range(2):
        assert client.delete(
            f"/api/v1/documents/{document_id}/tags/{tag_id}",
            headers=headers,
        ).status_code == 204
    detail = client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert detail.json()["tags"] == []


def test_combined_filters_use_and_and_escape_like_wildcards(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    headers = register_and_login(
        client,
        username="filter-owner",
        email="filter-owner@example.com",
    )
    first_kb = create_knowledge_base(client, headers, "筛选 A")
    second_kb = create_knowledge_base(client, headers, "筛选 B")
    target_id = int(str(upload_document(
        client, headers, first_kb, "100%_guide.txt"
    )["id"]))
    upload_document(client, headers, first_kb, "100AAguide.txt")
    upload_document(client, headers, second_kb, "100%_guide.txt")
    tag_id = int(str(create_tag(client, headers, "Target")["id"]))
    assert client.post(
        f"/api/v1/documents/{target_id}/tags/{tag_id}",
        headers=headers,
    ).status_code == 200
    assert client.put(
        f"/api/v1/documents/{target_id}/favorite",
        headers=headers,
        json={"is_favorite": True},
    ).status_code == 200

    response = client.get(
        "/api/v1/documents",
        headers=headers,
        params={
            "filename": "100%_",
            "status": "pending",
            "knowledge_base_id": first_kb,
            "tag_id": tag_id,
            "is_favorite": "true",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == target_id


def test_tag_filter_count_is_not_duplicated_by_multiple_document_tags(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    headers = register_and_login(
        client,
        username="tag-count",
        email="tag-count@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "计数测试")
    document_id = int(str(upload_document(
        client, headers, knowledge_base_id, "multi-tag.txt"
    )["id"]))
    first_tag_id = int(str(create_tag(client, headers, "First")["id"]))
    second_tag_id = int(str(create_tag(client, headers, "Second")["id"]))
    for tag_id in (first_tag_id, second_tag_id):
        assert client.post(
            f"/api/v1/documents/{document_id}/tags/{tag_id}",
            headers=headers,
        ).status_code == 200

    response = client.get(
        f"/api/v1/documents?tag_id={first_tag_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1
    assert len(response.json()["items"][0]["tags"]) == 2


def test_document_and_tag_operations_require_double_ownership(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = organization_context
    owner_headers = register_and_login(
        client,
        username="ownership-owner",
        email="ownership-owner@example.com",
    )
    other_headers = register_and_login(
        client,
        username="ownership-other",
        email="ownership-other@example.com",
    )
    owner_kb = create_knowledge_base(client, owner_headers, "Owner KB")
    other_kb = create_knowledge_base(client, other_headers, "Other KB")
    owner_document_id = int(str(upload_document(
        client, owner_headers, owner_kb, "owner.txt"
    )["id"]))
    other_document_id = int(str(upload_document(
        client, other_headers, other_kb, "other.txt"
    )["id"]))
    owner_tag_id = int(str(create_tag(client, owner_headers, "Owner tag")["id"]))

    assert client.put(
        f"/api/v1/documents/{owner_document_id}/favorite",
        headers=other_headers,
        json={"is_favorite": True},
    ).status_code == 404
    assert client.post(
        f"/api/v1/documents/{owner_document_id}/tags/{owner_tag_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/documents/{other_document_id}/tags/{owner_tag_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/documents?tag_id={owner_tag_id}",
        headers=other_headers,
    ).status_code == 404


def test_deleting_tag_cascades_association_but_keeps_document(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = organization_context
    headers = register_and_login(
        client,
        username="tag-cascade",
        email="tag-cascade@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "级联测试")
    document_id = int(str(upload_document(
        client, headers, knowledge_base_id, "keep.txt"
    )["id"]))
    tag_id = int(str(create_tag(client, headers, "Temporary")["id"]))
    assert client.post(
        f"/api/v1/documents/{document_id}/tags/{tag_id}",
        headers=headers,
    ).status_code == 200

    assert client.delete(f"/api/v1/tags/{tag_id}", headers=headers).status_code == 204

    assert client.get(
        f"/api/v1/documents/{document_id}",
        headers=headers,
    ).json()["tags"] == []
    with session_factory() as db:
        assert db.get(Document, document_id) is not None
        assert db.get(Tag, tag_id) is None
        assert db.scalar(select(func.count()).select_from(document_tags)) == 0


def test_deleting_document_cascades_association_but_keeps_reusable_tag(
    organization_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, session_factory = organization_context
    headers = register_and_login(
        client,
        username="document-tag-cascade",
        email="document-tag-cascade@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, headers, "文档级联测试")
    document_id = int(str(upload_document(
        client, headers, knowledge_base_id, "remove.txt"
    )["id"]))
    tag_id = int(str(create_tag(client, headers, "Reusable")["id"]))
    assert client.post(
        f"/api/v1/documents/{document_id}/tags/{tag_id}",
        headers=headers,
    ).status_code == 200

    assert client.delete(
        f"/api/v1/documents/{document_id}",
        headers=headers,
    ).status_code == 204

    with session_factory() as db:
        assert db.get(Document, document_id) is None
        assert db.get(Tag, tag_id) is not None
        assert db.scalar(select(func.count()).select_from(document_tags)) == 0


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/tags", None),
        ("post", "/api/v1/tags", {"name": "Private"}),
        ("get", "/api/v1/documents", None),
        ("get", "/api/v1/documents/favorites", None),
        ("put", "/api/v1/documents/1/favorite", {"is_favorite": True}),
        ("post", "/api/v1/documents/1/tags/1", None),
        ("delete", "/api/v1/documents/1/tags/1", None),
    ],
)
def test_document_organization_endpoints_require_authentication(
    organization_context: tuple[TestClient, sessionmaker[Session]],
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    client, _ = organization_context
    response = client.request(method, path, json=payload)
    assert response.status_code == 401
