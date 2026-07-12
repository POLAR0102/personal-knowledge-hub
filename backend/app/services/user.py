import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserLogin

logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class UserDatabaseError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(db: Session, user_data: UserCreate) -> User:
    repository = UserRepository(db)
    normalized_email = str(user_data.email).lower()

    try:
        if repository.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError

        return repository.create(
            username=user_data.username,
            email=normalized_email,
            password_hash=hash_password(user_data.password),
        )
    except EmailAlreadyRegisteredError:
        raise
    except IntegrityError as exc:
        repository.rollback()
        raise EmailAlreadyRegisteredError from exc
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while registering a user")
        raise UserDatabaseError from exc


def authenticate_user(db: Session, credentials: UserLogin) -> User:
    repository = UserRepository(db)
    normalized_email = str(credentials.email).lower()

    try:
        user = repository.get_by_email(normalized_email)
    except SQLAlchemyError as exc:
        logger.exception("Database error while authenticating a user")
        raise UserDatabaseError from exc

    if (
        user is None
        or not user.is_active
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise InvalidCredentialsError

    return user
