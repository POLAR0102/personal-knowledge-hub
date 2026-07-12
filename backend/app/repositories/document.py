from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus


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
    ) -> list[Document]:
        statement = select(Document).where(
            Document.user_id == user_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        if status is not None:
            statement = statement.where(Document.status == status)
        statement = (
            statement.order_by(Document.created_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

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

    def get_owned(self, *, document_id: int, user_id: int) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def delete(self, document: Document) -> None:
        self.db.delete(document)
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
