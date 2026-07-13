from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.ai.document_processing.chunker import ChunkDraft
from app.db.models import Document, DocumentChunk, KnowledgeBase, User
from app.repositories.document_chunk import DocumentChunkRepository


def create_document(db: Session, tmp_path: Path) -> Document:
    user = User(
        username="chunk-owner",
        email="chunk-owner@example.com",
        password_hash="hashed-password",
    )
    db.add(user)
    db.flush()
    knowledge_base = KnowledgeBase(user_id=user.id, name="Chunk 测试知识库")
    db.add(knowledge_base)
    db.flush()
    file_path = tmp_path / "chunk-source.txt"
    file_path.write_text("source", encoding="utf-8")
    document = Document(
        user_id=user.id,
        knowledge_base_id=knowledge_base.id,
        original_filename="chunk-source.txt",
        stored_filename="chunk-source-random.txt",
        file_type="txt",
        mime_type="text/plain",
        file_size=6,
        file_path=str(file_path),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def draft(index: int, content: str) -> ChunkDraft:
    import hashlib

    return ChunkDraft(
        chunk_index=index,
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        character_count=len(content),
        page_number=1,
        section_title="测试章节",
        start_offset=0,
        end_offset=len(content),
    )


def test_repository_creates_lists_counts_and_deletes_chunks(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
) -> None:
    _, testing_session = client_and_session
    with testing_session() as db:
        document = create_document(db, tmp_path)
        repository = DocumentChunkRepository(db)
        created = repository.create_many(
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            drafts=[draft(0, "第一个 Chunk"), draft(1, "第二个 Chunk")],
        )
        db.commit()

        assert [chunk.chunk_index for chunk in created] == [0, 1]
        assert all(chunk.character_count == len(chunk.content) for chunk in created)
        assert repository.count_for_document(
            document_id=document.id,
            user_id=document.user_id,
        ) == 2
        assert [
            chunk.chunk_index
            for chunk in repository.list_for_document(
                document_id=document.id,
                user_id=document.user_id,
                offset=0,
                limit=20,
            )
        ] == [0, 1]

        repository.delete_for_document(document_id=document.id)
        db.commit()
        assert repository.count_for_document(
            document_id=document.id,
            user_id=document.user_id,
        ) == 0


def test_document_and_chunk_index_must_be_unique(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
) -> None:
    _, testing_session = client_and_session
    with testing_session() as db:
        document = create_document(db, tmp_path)
        repository = DocumentChunkRepository(db)
        repository.create_many(
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            drafts=[draft(0, "原始内容")],
        )
        db.commit()

        with pytest.raises(IntegrityError):
            repository.create_many(
                user_id=document.user_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                drafts=[draft(0, "重复索引")],
            )


def test_deleting_document_cascades_chunks(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    tmp_path: Path,
) -> None:
    _, testing_session = client_and_session
    with testing_session() as db:
        document = create_document(db, tmp_path)
        document_id = document.id
        DocumentChunkRepository(db).create_many(
            user_id=document.user_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            drafts=[draft(0, "将被级联删除")],
        )
        db.commit()

        db.execute(Document.__table__.delete().where(Document.id == document_id))
        db.commit()

        assert db.scalar(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ) is None
