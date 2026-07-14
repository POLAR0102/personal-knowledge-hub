from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Tag


class TagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: int, name: str) -> Tag:
        tag = Tag(user_id=user_id, name=name)
        self.db.add(tag)
        self.db.flush()
        return tag

    def list_owned(
        self,
        *,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[Tag]:
        statement = (
            select(Tag)
            .where(Tag.user_id == user_id)
            .order_by(Tag.name.asc(), Tag.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def count_owned(self, *, user_id: int) -> int:
        statement = select(func.count(Tag.id)).where(Tag.user_id == user_id)
        return self.db.execute(statement).scalar_one()

    def get_owned(self, *, tag_id: int, user_id: int) -> Tag | None:
        statement = select(Tag).where(
            Tag.id == tag_id,
            Tag.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_owned_by_name(self, *, name: str, user_id: int) -> Tag | None:
        statement = select(Tag).where(
            Tag.name == name,
            Tag.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def update_name(self, tag: Tag, name: str) -> None:
        tag.name = name
        self.db.flush()

    def delete(self, tag: Tag) -> None:
        self.db.delete(tag)
