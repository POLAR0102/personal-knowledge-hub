import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import KnowledgeBase, User


def test_sqlite_foreign_keys_are_enabled(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    _, testing_session = client_and_session

    with testing_session() as db:
        assert db.scalar(text("PRAGMA foreign_keys")) == 1


def test_knowledge_base_rejects_unknown_user_id(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    _, testing_session = client_and_session

    with testing_session() as db:
        db.add(
            KnowledgeBase(
                user_id=999_999,
                name="无效归属知识库",
            )
        )

        with pytest.raises(IntegrityError):
            db.commit()


def test_deleting_user_cascades_to_knowledge_bases_in_database(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    _, testing_session = client_and_session

    with testing_session() as db:
        user = User(
            username="cascade-user",
            email="cascade@example.com",
            password_hash="hashed-password",
        )
        db.add(user)
        db.flush()
        db.add(
            KnowledgeBase(
                user_id=user.id,
                name="待级联删除知识库",
            )
        )
        db.commit()
        user_id = user.id

        db.execute(User.__table__.delete().where(User.id == user_id))
        db.commit()

        remaining = db.scalar(
            select(func.count())
            .select_from(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id)
        )
        assert remaining == 0
