from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        name: str,
        description: str | None,
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            user_id=user_id,
            name=name,
            description=description,
        )
        self.db.add(knowledge_base)
        self.db.commit()
        self.db.refresh(knowledge_base)
        return knowledge_base

    def list_owned(
        self,
        *,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[KnowledgeBase]:
        statement = (
            select(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id)
            .order_by(KnowledgeBase.updated_at.desc(), KnowledgeBase.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def count_owned(self, *, user_id: int) -> int:
        statement = select(func.count(KnowledgeBase.id)).where(
            KnowledgeBase.user_id == user_id
        )
        return self.db.execute(statement).scalar_one()

    def get_owned(
        self,
        *,
        knowledge_base_id: int,
        user_id: int,
    ) -> KnowledgeBase | None:
        statement = select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def update(
        self,
        knowledge_base: KnowledgeBase,
        values: dict[str, str | None],
    ) -> KnowledgeBase:
        for field, value in values.items():
            setattr(knowledge_base, field, value)
        self.db.commit()
        self.db.refresh(knowledge_base)
        return knowledge_base

    def delete(self, knowledge_base: KnowledgeBase) -> None:
        self.db.delete(knowledge_base)
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
