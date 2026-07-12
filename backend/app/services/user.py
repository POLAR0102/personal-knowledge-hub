import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class UserDatabaseError(Exception):
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
