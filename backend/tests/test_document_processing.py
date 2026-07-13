from collections.abc import Callable, Generator
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from docx import Document as create_docx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentStatus


@pytest.fixture
def processing_context(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path / "uploads")
    yield client_and_session


def register_and_login(
    client: TestClient,
    *,
    username: str = "processor",
    email: str = "processor@example.com",
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
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_knowledge_base(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "处理测试知识库"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: int,
    *,
    filename: str,
    content: bytes,
    mime_type: str,
) -> int:
    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"file": (filename, content, mime_type)},
    )
    assert response.status_code == 201
    return response.json()["id"]


def pdf_bytes(*pages: str) -> bytes:
    with pymupdf.open() as pdf:
        for text in pages:
            page = pdf.new_page()
            if text:
                page.insert_text((72, 72), text)
        return pdf.tobytes()


def docx_bytes() -> bytes:
    document = create_docx()
    document.add_heading("DOCX 标题", level=1)
    document.add_paragraph("DOCX 正文内容")
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def txt_content() -> bytes:
    return "智能知识库 TXT 文档。\n\n用于完整处理测试。".encode()


def markdown_content() -> bytes:
    return "# Markdown 标题\n\nMarkdown 正文内容。".encode()


def pdf_content() -> bytes:
    return pdf_bytes("PDF first page", "PDF second page")


@pytest.mark.parametrize(
    ("filename", "mime_type", "content_factory"),
    [
        ("complete.txt", "text/plain", txt_content),
        ("complete.md", "text/markdown", markdown_content),
        ("complete.pdf", "application/pdf", pdf_content),
        (
            "complete.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_bytes,
        ),
    ],
)
def test_complete_processing_for_supported_formats(
    processing_context: tuple[TestClient, sessionmaker[Session]],
    filename: str,
    mime_type: str,
    content_factory: Callable[[], bytes],
) -> None:
    client, _ = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename=filename,
        content=content_factory(),
        mime_type=mime_type,
    )

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["chunk_count"] >= 1
    detail = client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert detail.json()["status"] == "completed"
    assert detail.json()["chunk_count"] == response.json()["chunk_count"]

    chunks = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=headers,
    ).json()["items"]
    assert [chunk["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
    if filename.endswith(".pdf"):
        assert [chunk["page_number"] for chunk in chunks] == [1, 2]


def test_processing_missing_document_returns_404(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = processing_context
    headers = register_and_login(client)
    response = client.post("/api/v1/documents/999999/process", headers=headers)
    assert response.status_code == 404


def test_missing_file_sets_failed_status_and_short_error(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename="missing.txt",
        content=b"content",
        mime_type="text/plain",
    )
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        Path(document.file_path).unlink()

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )

    assert response.status_code == 422
    assert "不存在" in response.json()["detail"]
    detail = client.get(f"/api/v1/documents/{document_id}", headers=headers).json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "文档文件不存在，请重新上传"


def test_empty_file_during_processing_sets_failed_status(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename="empty-later.txt",
        content=b"temporary",
        mime_type="text/plain",
    )
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        Path(document.file_path).write_bytes(b"")

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )

    assert response.status_code == 422
    assert "没有可提取" in response.json()["detail"]
    assert client.get(
        f"/api/v1/documents/{document_id}", headers=headers
    ).json()["status"] == "failed"


def test_scanned_pdf_sets_failed_status_with_ocr_message(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename="scanned.pdf",
        content=pdf_bytes(""),
        mime_type="application/pdf",
    )

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )

    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]
    detail = client.get(f"/api/v1/documents/{document_id}", headers=headers).json()
    assert detail["status"] == "failed"
    assert "OCR" in detail["error_message"]


def test_processing_requires_authentication(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = processing_context
    assert client.post("/api/v1/documents/1/process").status_code == 401
    assert client.get("/api/v1/documents/1/chunks").status_code == 401


def test_other_user_cannot_process_or_read_chunks(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = processing_context
    owner_headers = register_and_login(client)
    other_headers = register_and_login(
        client,
        username="other-processor",
        email="other-processor@example.com",
    )
    knowledge_base_id = create_knowledge_base(client, owner_headers)
    document_id = upload(
        client,
        owner_headers,
        knowledge_base_id,
        filename="private.txt",
        content=b"private content",
        mime_type="text/plain",
    )
    assert client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=owner_headers,
    ).status_code == 200

    assert client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=other_headers,
    ).status_code == 404


def test_reprocessing_replaces_old_chunks_without_duplicates(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename="repeat.txt",
        content=b"old unique content",
        mime_type="text/plain",
    )
    first = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )
    assert first.status_code == 200
    with testing_session() as db:
        old_chunks = list(
            db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            ).scalars()
        )
        old_hashes = {chunk.content_hash for chunk in old_chunks}
        document = db.get(Document, document_id)
        assert document is not None
        Path(document.file_path).write_text("new unique content", encoding="utf-8")

    second = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )

    assert second.status_code == 200
    with testing_session() as db:
        new_chunks = list(
            db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            ).scalars()
        )
        assert len(new_chunks) == second.json()["chunk_count"]
        assert old_hashes.isdisjoint({chunk.content_hash for chunk in new_chunks})
        assert "new unique content" in new_chunks[0].content
        assert all("old unique content" not in chunk.content for chunk in new_chunks)


def test_processing_state_rejects_duplicate_request(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename="processing.txt",
        content=b"processing",
        mime_type="text/plain",
    )
    with testing_session() as db:
        document = db.get(Document, document_id)
        assert document is not None
        document.status = DocumentStatus.PROCESSING
        db.commit()

    response = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )
    assert response.status_code == 409


def test_stage_b_acceptance_document_can_be_verified_and_reprocessed(
    processing_context: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = processing_context
    headers = register_and_login(client)
    knowledge_base_id = create_knowledge_base(client, headers)
    content = """智能个人知识库系统的项目代号为 PKH-2026。

项目核心技术包括 React、FastAPI、ChromaDB 和 RAG。

核心版本计划在 14 天内完成。

项目负责人为测试用户张三。"""
    document_id = upload(
        client,
        headers,
        knowledge_base_id,
        filename="test-rag.txt",
        content=content.encode(),
        mime_type="text/plain",
    )

    first_process = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )
    first_chunks = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        headers=headers,
    ).json()

    assert first_process.json()["status"] == "completed"
    assert first_chunks["total"] >= 1
    assert any("PKH-2026" in chunk["content"] for chunk in first_chunks["items"])
    with testing_session() as db:
        chunks = list(
            db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            ).scalars()
        )
        assert all(chunk.document_id == document_id for chunk in chunks)
        assert all(chunk.knowledge_base_id == knowledge_base_id for chunk in chunks)
        assert len({chunk.user_id for chunk in chunks}) == 1

    second_process = client.post(
        f"/api/v1/documents/{document_id}/process",
        headers=headers,
    )
    assert second_process.json()["chunk_count"] == first_chunks["total"]

    assert client.delete(
        f"/api/v1/documents/{document_id}", headers=headers
    ).status_code == 204
    with testing_session() as db:
        assert db.scalar(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ) is None
