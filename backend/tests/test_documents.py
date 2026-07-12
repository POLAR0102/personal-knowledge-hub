from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Document


@pytest.fixture
def document_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, sessionmaker[Session], Path], None, None]:
    upload_dir = tmp_path / "uploads"
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    monkeypatch.setattr(settings, "max_upload_size_mb", 20)
    client, testing_session = client_and_session
    yield client, testing_session, upload_dir


def register_and_login(
    client: TestClient,
    *,
    username: str = "document-owner",
    email: str = "document-owner@example.com",
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
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def create_knowledge_base(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "文档测试知识库"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload_file(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    *,
    filename: str,
    content: bytes,
    mime_type: str,
):
    return client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"file": (filename, content, mime_type)},
    )


@pytest.mark.parametrize(
    ("filename", "content", "mime_type", "expected_type"),
    [
        ("notes.txt", b"plain text", "text/plain", "txt"),
        ("readme.md", b"# Markdown", "text/markdown", "md"),
        ("paper.pdf", b"%PDF-1.4 test", "application/pdf", "pdf"),
        (
            "report.docx",
            b"PK\x03\x04 test",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        ),
    ],
)
def test_upload_supported_document_types(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
    filename: str,
    content: bytes,
    mime_type: str,
    expected_type: str,
) -> None:
    client, testing_session, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)

    response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename=filename,
        content=content,
        mime_type=mime_type,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == filename
    assert payload["file_type"] == expected_type
    assert payload["file_size"] == len(content)
    assert payload["status"] == "pending"
    assert "stored_filename" not in payload
    assert "file_path" not in payload

    with testing_session() as db:
        document = db.scalar(select(Document).where(Document.id == payload["id"]))
        assert document is not None
        assert Path(document.file_path).is_file()
        assert document.stored_filename != filename


def test_upload_rejects_unsupported_extension_and_mime_type(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)

    unsupported_extension = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="program.exe",
        content=b"not allowed",
        mime_type="application/octet-stream",
    )
    mismatched_mime = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="fake.pdf",
        content=b"not a pdf",
        mime_type="text/plain",
    )

    assert unsupported_extension.status_code == 415
    assert mismatched_mime.status_code == 415


def test_upload_rejects_empty_file(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)

    response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="empty.txt",
        content=b"",
        mime_type="text/plain",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File is empty"


def test_upload_rejects_file_over_configured_limit(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, testing_session, upload_dir = document_context
    monkeypatch.setattr(get_settings(), "max_upload_size_mb", 1)
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)

    response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="large.txt",
        content=b"x" * (1024 * 1024 + 1),
        mime_type="text/plain",
    )

    assert response.status_code == 413
    with testing_session() as db:
        assert db.scalar(select(Document)) is None
    assert not list(upload_dir.rglob("*.part"))


def test_path_traversal_filename_is_sanitized(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, testing_session, upload_dir = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)

    response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="../../escape.txt",
        content=b"safe content",
        mime_type="text/plain",
    )

    assert response.status_code == 201
    assert response.json()["original_filename"] == "escape.txt"
    with testing_session() as db:
        document = db.get(Document, response.json()["id"])
        assert document is not None
        assert Path(document.file_path).resolve().is_relative_to(upload_dir.resolve())
    assert not (upload_dir.parent / "escape.txt").exists()


def test_unauthenticated_user_cannot_upload(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _, _ = document_context

    response = upload_file(
        client,
        {},
        1,
        filename="notes.txt",
        content=b"private",
        mime_type="text/plain",
    )

    assert response.status_code == 401


def test_other_user_cannot_upload_view_or_delete_documents(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _, _ = document_context
    owner_headers = register_and_login(client)
    other_headers = register_and_login(
        client,
        username="other-user",
        email="other@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, owner_headers)
    owner_upload = upload_file(
        client,
        owner_headers,
        knowledge_base_id,
        filename="private.txt",
        content=b"private",
        mime_type="text/plain",
    )
    document_id = owner_upload.json()["id"]

    forbidden_upload = upload_file(
        client,
        other_headers,
        knowledge_base_id,
        filename="intrusion.txt",
        content=b"intrusion",
        mime_type="text/plain",
    )
    forbidden_view = client.get(
        f"/api/v1/documents/{document_id}",
        headers=other_headers,
    )
    forbidden_delete = client.delete(
        f"/api/v1/documents/{document_id}",
        headers=other_headers,
    )

    assert forbidden_upload.status_code == 404
    assert forbidden_view.status_code == 404
    assert forbidden_delete.status_code == 404
    assert client.get(
        f"/api/v1/documents/{document_id}",
        headers=owner_headers,
    ).status_code == 200


def test_document_list_is_paginated_and_supports_status_filter(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    for filename in ("first.txt", "second.txt", "third.txt"):
        assert upload_file(
            client,
            headers,
            knowledge_base_id,
            filename=filename,
            content=filename.encode(),
            mime_type="text/plain",
        ).status_code == 201

    response = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents?page=1&page_size=2&status=pending",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 2
    assert [item["original_filename"] for item in response.json()["items"]] == [
        "third.txt",
        "second.txt",
    ]


def test_document_stats_only_count_current_user_documents(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, _, _ = document_context
    owner_headers = register_and_login(client)
    other_headers = register_and_login(
        client,
        username="other-user",
        email="other@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, owner_headers)
    upload_file(
        client,
        owner_headers,
        knowledge_base_id,
        filename="owned.txt",
        content=b"owned",
        mime_type="text/plain",
    )

    owner_stats = client.get("/api/v1/documents/stats", headers=owner_headers)
    other_stats = client.get("/api/v1/documents/stats", headers=other_headers)

    assert owner_stats.json() == {"total": 1}
    assert other_stats.json() == {"total": 0}


def test_delete_document_removes_database_record_and_file(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, testing_session, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    upload_response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="delete-me.txt",
        content=b"delete me",
        mime_type="text/plain",
    )
    document_id = upload_response.json()["id"]
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        file_path = Path(document.file_path)
        assert file_path.exists()

    response = client.delete(f"/api/v1/documents/{document_id}", headers=headers)

    assert response.status_code == 204
    assert not file_path.exists()
    with testing_session() as db:
        assert db.get(Document, document_id) is None


def test_delete_document_succeeds_when_file_is_already_missing(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, testing_session, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    upload_response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="missing.txt",
        content=b"missing",
        mime_type="text/plain",
    )
    document_id = upload_response.json()["id"]
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        Path(document.file_path).unlink()

    response = client.delete(f"/api/v1/documents/{document_id}", headers=headers)

    assert response.status_code == 204
    with testing_session() as db:
        assert db.get(Document, document_id) is None


def test_deleting_knowledge_base_cascades_document_record(
    document_context: tuple[TestClient, sessionmaker[Session], Path],
) -> None:
    client, testing_session, _ = document_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    upload_response = upload_file(
        client,
        headers,
        knowledge_base_id,
        filename="cascade.txt",
        content=b"cascade",
        mime_type="text/plain",
    )
    document_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
    )

    assert response.status_code == 204
    with testing_session() as db:
        assert db.get(Document, document_id) is None
