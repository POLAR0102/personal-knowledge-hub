import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Tag, User
from app.repositories.tag import TagRepository
from app.schemas.tag import TagCreate, TagUpdate

logger = logging.getLogger(__name__)


class TagNotFoundError(Exception):
    pass


class TagConflictError(Exception):
    pass


class TagDatabaseError(Exception):
    pass


def _get_owned_tag(
    repository: TagRepository,
    *,
    tag_id: int,
    user_id: int,
) -> Tag:
    tag = repository.get_owned(tag_id=tag_id, user_id=user_id)
    if tag is None:
        raise TagNotFoundError
    return tag


def create_tag(db: Session, owner: User, data: TagCreate) -> Tag:
    repository = TagRepository(db)
    try:
        if repository.get_owned_by_name(name=data.name, user_id=owner.id) is not None:
            raise TagConflictError("Tag name already exists")
        tag = repository.create(user_id=owner.id, name=data.name)
        db.commit()
        db.refresh(tag)
        return tag
    except TagConflictError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise TagConflictError("Tag name already exists") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while creating a tag")
        raise TagDatabaseError from exc


def list_tags(
    db: Session,
    owner: User,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Tag], int]:
    repository = TagRepository(db)
    try:
        items = repository.list_owned(
            user_id=owner.id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return items, repository.count_owned(user_id=owner.id)
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing tags")
        raise TagDatabaseError from exc


def get_tag(db: Session, owner: User, tag_id: int) -> Tag:
    try:
        return _get_owned_tag(
            TagRepository(db),
            tag_id=tag_id,
            user_id=owner.id,
        )
    except TagNotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading a tag")
        raise TagDatabaseError from exc


def update_tag(
    db: Session,
    owner: User,
    tag_id: int,
    data: TagUpdate,
) -> Tag:
    repository = TagRepository(db)
    try:
        tag = _get_owned_tag(repository, tag_id=tag_id, user_id=owner.id)
        existing = repository.get_owned_by_name(name=data.name, user_id=owner.id)
        if existing is not None and existing.id != tag.id:
            raise TagConflictError("Tag name already exists")
        repository.update_name(tag, data.name)
        db.commit()
        db.refresh(tag)
        return tag
    except (TagNotFoundError, TagConflictError):
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise TagConflictError("Tag name already exists") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while updating a tag")
        raise TagDatabaseError from exc


def delete_tag(db: Session, owner: User, tag_id: int) -> None:
    repository = TagRepository(db)
    try:
        tag = _get_owned_tag(repository, tag_id=tag_id, user_id=owner.id)
        repository.delete(tag)
        db.commit()
    except TagNotFoundError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while deleting a tag")
        raise TagDatabaseError from exc
