from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.document_processing.chunker import ChunkDraft
from app.db.models import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        document_id: int,
        drafts: Sequence[ChunkDraft],
    ) -> list[DocumentChunk]:
        chunks = [
            DocumentChunk(
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                chunk_index=draft.chunk_index,
                content=draft.content,
                content_hash=draft.content_hash,
                character_count=draft.character_count,
                page_number=draft.page_number,
                section_title=draft.section_title,
                start_offset=draft.start_offset,
                end_offset=draft.end_offset,
            )
            for draft in drafts
        ]
        self.db.add_all(chunks)
        self.db.flush()
        return chunks

    def delete_for_document(self, *, document_id: int) -> None:
        self.db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

    def list_for_document(
        self,
        *,
        document_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == user_id,
            )
            .order_by(DocumentChunk.chunk_index)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def count_for_document(self, *, document_id: int, user_id: int) -> int:
        statement = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one()
