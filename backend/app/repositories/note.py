from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Note, NoteSourceType


class NoteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        knowledge_base_id: int,
        title: str,
        content: str,
        source_type: NoteSourceType,
        source_agent_task_id: int | None = None,
    ) -> Note:
        note = Note(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            title=title,
            content=content,
            source_type=source_type,
            source_agent_task_id=source_agent_task_id,
        )
        self.db.add(note)
        self.db.flush()
        return note

    def list_owned(
        self,
        *,
        user_id: int,
        knowledge_base_id: int | None,
        offset: int,
        limit: int,
    ) -> list[Note]:
        statement = select(Note).where(Note.user_id == user_id)
        if knowledge_base_id is not None:
            statement = statement.where(
                Note.knowledge_base_id == knowledge_base_id
            )
        statement = (
            statement.order_by(Note.updated_at.desc(), Note.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def count_owned(
        self,
        *,
        user_id: int,
        knowledge_base_id: int | None,
    ) -> int:
        statement = select(func.count(Note.id)).where(Note.user_id == user_id)
        if knowledge_base_id is not None:
            statement = statement.where(
                Note.knowledge_base_id == knowledge_base_id
            )
        return self.db.execute(statement).scalar_one()

    def get_owned(self, *, note_id: int, user_id: int) -> Note | None:
        statement = select(Note).where(
            Note.id == note_id,
            Note.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_source_agent_task(
        self,
        *,
        source_agent_task_id: int,
        user_id: int,
    ) -> Note | None:
        statement = select(Note).where(
            Note.source_agent_task_id == source_agent_task_id,
            Note.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def update(self, note: Note, values: dict[str, str | None]) -> Note:
        for field, value in values.items():
            setattr(note, field, value)
        self.db.flush()
        return note

    def delete(self, note: Note) -> None:
        self.db.delete(note)

    def rollback(self) -> None:
        self.db.rollback()
