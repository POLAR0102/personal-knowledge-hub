from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import User
from app.schemas.user import UserRead


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as database_session:
        yield database_session


def test_user_model_persists_defaults(session: Session) -> None:
    user = User(
        username="alice",
        email="alice@example.com",
        password_hash="hashed-password",
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


def test_user_email_must_be_unique(session: Session) -> None:
    session.add(
        User(
            username="alice",
            email="same@example.com",
            password_hash="hashed-password",
        )
    )
    session.commit()

    session.add(
        User(
            username="bob",
            email="same@example.com",
            password_hash="another-hash",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_user_username_length_is_enforced(session: Session) -> None:
    session.add(
        User(
            username="x",
            email="short-name@example.com",
            password_hash="hashed-password",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_user_read_schema_excludes_password_hash(session: Session) -> None:
    user = User(
        username="alice",
        email="alice@example.com",
        password_hash="must-not-be-returned",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    payload = UserRead.model_validate(user).model_dump()

    assert "password_hash" not in payload
    assert "password" not in payload
