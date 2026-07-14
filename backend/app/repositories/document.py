from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Document,
    DocumentChunk,
    DocumentIndexStatus,
    DocumentStatus,
    Tag,
)


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        original_filename: str,
        stored_filename: str,
        file_type: str,
        mime_type: str,
        file_size: int,
        file_path: str,
    ) -> Document:
        document = Document(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
            file_path=file_path,
            status=DocumentStatus.PENDING,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def list_owned_in_knowledge_base(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        offset: int,
        limit: int,
        status: DocumentStatus | None,
    ) -> list[tuple[Document, int]]:
        statement = (
            select(Document, func.count(DocumentChunk.id))
            .options(selectinload(Document.tags))
            .outerjoin(
                DocumentChunk,
                DocumentChunk.document_id == Document.id,
            )
            .where(
                Document.user_id == user_id,
                Document.knowledge_base_id == knowledge_base_id,
            )
        )
        if status is not None:
            statement = statement.where(Document.status == status)
        statement = (
            statement.group_by(Document.id)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [(document, count) for document, count in self.db.execute(statement).all()]

    def count_owned_in_knowledge_base(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        status: DocumentStatus | None,
    ) -> int:
        statement = select(func.count(Document.id)).where(
            Document.user_id == user_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        if status is not None:
            statement = statement.where(Document.status == status)
        return self.db.execute(statement).scalar_one()

    def count_owned(self, *, user_id: int) -> int:
        statement = select(func.count(Document.id)).where(Document.user_id == user_id)
        return self.db.execute(statement).scalar_one()

    @staticmethod
    def _filtered_owned_ids(
        *,
        user_id: int,
        filename: str | None,
        status: DocumentStatus | None,
        knowledge_base_id: int | None,
        tag_id: int | None,
        is_favorite: bool | None,
    ) -> Select[tuple[int]]:
        statement = select(Document.id).where(Document.user_id == user_id)
        if filename is not None:
            statement = statement.where(
                Document.original_filename.contains(filename, autoescape=True)
            )
        if status is not None:
            statement = statement.where(Document.status == status)
        if knowledge_base_id is not None:
            statement = statement.where(
                Document.knowledge_base_id == knowledge_base_id
            )
        if tag_id is not None:
            statement = statement.where(Document.tags.any(Tag.id == tag_id))
        if is_favorite is not None:
            statement = statement.where(Document.is_favorite == is_favorite)
        return statement

    def list_owned(
        self,
        *,
        user_id: int,
        offset: int,
        limit: int,
        filename: str | None,
        status: DocumentStatus | None,
        knowledge_base_id: int | None,
        tag_id: int | None,
        is_favorite: bool | None,
    ) -> list[tuple[Document, int]]:
        filtered_ids = self._filtered_owned_ids(
            user_id=user_id,
            filename=filename,
            status=status,
            knowledge_base_id=knowledge_base_id,
            tag_id=tag_id,
            is_favorite=is_favorite,
        )
        statement = (
            select(Document, func.count(DocumentChunk.id))
            .options(selectinload(Document.tags))
            .outerjoin(
                DocumentChunk,
                DocumentChunk.document_id == Document.id,
            )
            .where(Document.id.in_(filtered_ids))
            .group_by(Document.id)
            .order_by(Document.created_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [
            (document, chunk_count)
            for document, chunk_count in self.db.execute(statement).all()
        ]

    def count_owned_filtered(
        self,
        *,
        user_id: int,
        filename: str | None,
        status: DocumentStatus | None,
        knowledge_base_id: int | None,
        tag_id: int | None,
        is_favorite: bool | None,
    ) -> int:
        filtered_ids = self._filtered_owned_ids(
            user_id=user_id,
            filename=filename,
            status=status,
            knowledge_base_id=knowledge_base_id,
            tag_id=tag_id,
            is_favorite=is_favorite,
        )
        statement = select(func.count()).select_from(filtered_ids.subquery())
        return self.db.execute(statement).scalar_one()

    def list_owned_by_knowledge_base(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
    ) -> list[Document]:
        statement = select(Document).where(
            Document.user_id == user_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        return list(self.db.execute(statement).scalars().all())

    def get_owned(self, *, document_id: int, user_id: int) -> Document | None:
        statement = (
            select(Document)
            .options(selectinload(Document.tags))
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        return self.db.execute(statement).scalar_one_or_none()

    def set_favorite(self, document: Document, is_favorite: bool) -> None:
        document.is_favorite = is_favorite
        self.db.flush()

    def add_tag(self, document: Document, tag: Tag) -> None:
        if all(existing.id != tag.id for existing in document.tags):
            document.tags.append(tag)
            self.db.flush()

    def remove_tag(self, document: Document, tag: Tag) -> None:
        document.tags[:] = [
            existing for existing in document.tags if existing.id != tag.id
        ]
        self.db.flush()

    def try_start_indexing(self, *, document_id: int, user_id: int) -> bool:
        result = self.db.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
                Document.status == DocumentStatus.COMPLETED,
                Document.index_status != DocumentIndexStatus.INDEXING,
            )
            .values(
                index_status=DocumentIndexStatus.INDEXING,
                index_error_message=None,
            )
            .execution_options(synchronize_session=False)
        )
        self.db.commit()
        return result.rowcount == 1

    def delete(self, document: Document) -> None:
        self.db.delete(document)
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
