import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import User
from app.repositories.user import UserRepository


def registration_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456",
        "confirm_password": "123456",
    }
    payload.update(overrides)
    return payload


def test_register_user_success(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, testing_session = client_and_session

    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
    assert response.json()["email"] == "test@example.com"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()

    with testing_session() as db:
        user = db.execute(select(User)).scalar_one()
        assert user.password_hash != "123456"
        assert bcrypt.checkpw(b"123456", user.password_hash.encode("utf-8"))


def test_register_user_with_duplicate_email_returns_409(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session
    client.post("/api/v1/auth/register", json=registration_payload())

    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(username="another-user"),
    )

    assert response.status_code == 409


def test_register_user_with_mismatched_passwords_returns_422(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session

    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(confirm_password="654321"),
    )

    assert response.status_code == 422
    assert "123456" not in response.text
    assert "654321" not in response.text


def test_register_user_with_short_password_returns_422(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session

    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(password="123", confirm_password="123"),
    )

    assert response.status_code == 422
    assert "123" not in response.text


def test_register_user_with_invalid_email_returns_422(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = client_and_session

    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(email="not-an-email"),
    )

    assert response.status_code == 422


def test_register_user_database_error_returns_uniform_500(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = client_and_session

    def raise_database_error(
        _repository: UserRepository,
        _email: str,
    ) -> User | None:
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(UserRepository, "get_by_email", raise_database_error)

    response = client.post("/api/v1/auth/register", json=registration_payload())

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to register user"}
