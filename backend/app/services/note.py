import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import AgentTaskStatus, Note, NoteSourceType, User
from app.repositories.agent_task import AgentTaskRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.repositories.note import NoteRepository
from app.schemas.note import NoteCreate, NoteUpdate

logger = logging.getLogger(__name__)


class NoteNotFoundError(Exception):
    pass


class NoteConflictError(Exception):
    pass


class NoteDatabaseError(Exception):
    pass


def _ensure_owned_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: int,
    user_id: int,
) -> None:
    knowledge_base = KnowledgeBaseRepository(db).get_owned(
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
    )
    if knowledge_base is None:
        raise NoteNotFoundError


def _get_owned_note(
    repository: NoteRepository,
    *,
    note_id: int,
    user_id: int,
) -> Note:
    note = repository.get_owned(note_id=note_id, user_id=user_id)
    if note is None:
        raise NoteNotFoundError
    return note


def create_note(db: Session, owner: User, data: NoteCreate) -> Note:
    repository = NoteRepository(db)
    try:
        _ensure_owned_knowledge_base(
            db,
            knowledge_base_id=data.knowledge_base_id,
            user_id=owner.id,
        )
        note = repository.create(
            user_id=owner.id,
            knowledge_base_id=data.knowledge_base_id,
            title=data.title,
            content=data.content,
            source_type=NoteSourceType.MANUAL,
        )
        db.commit()
        db.refresh(note)
        return note
    except NoteNotFoundError:
        repository.rollback()
        raise
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while creating a note")
        raise NoteDatabaseError from exc


def list_notes(
    db: Session,
    owner: User,
    *,
    page: int,
    page_size: int,
    knowledge_base_id: int | None,
) -> tuple[list[Note], int]:
    repository = NoteRepository(db)
    try:
        if knowledge_base_id is not None:
            _ensure_owned_knowledge_base(
                db,
                knowledge_base_id=knowledge_base_id,
                user_id=owner.id,
            )
        items = repository.list_owned(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total = repository.count_owned(
            user_id=owner.id,
            knowledge_base_id=knowledge_base_id,
        )
        return items, total
    except NoteNotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while listing notes")
        raise NoteDatabaseError from exc


def get_note(db: Session, owner: User, note_id: int) -> Note:
    repository = NoteRepository(db)
    try:
        return _get_owned_note(repository, note_id=note_id, user_id=owner.id)
    except NoteNotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Database error while loading a note")
        raise NoteDatabaseError from exc


def update_note(
    db: Session,
    owner: User,
    note_id: int,
    data: NoteUpdate,
) -> Note:
    repository = NoteRepository(db)
    try:
        note = _get_owned_note(repository, note_id=note_id, user_id=owner.id)
        repository.update(note, data.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(note)
        return note
    except NoteNotFoundError:
        repository.rollback()
        raise
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while updating a note")
        raise NoteDatabaseError from exc


def delete_note(db: Session, owner: User, note_id: int) -> None:
    repository = NoteRepository(db)
    try:
        note = _get_owned_note(repository, note_id=note_id, user_id=owner.id)
        repository.delete(note)
        db.commit()
    except NoteNotFoundError:
        repository.rollback()
        raise
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while deleting a note")
        raise NoteDatabaseError from exc


def save_agent_task_as_note(
    db: Session,
    owner: User,
    task_id: int,
) -> Note:
    repository = NoteRepository(db)
    try:
        task = AgentTaskRepository(db).get_owned(task_id=task_id, user_id=owner.id)
        if task is None:
            raise NoteNotFoundError

        existing = repository.get_by_source_agent_task(
            source_agent_task_id=task.id,
            user_id=owner.id,
        )
        if existing is not None:
            return existing

        if (
            task.status != AgentTaskStatus.COMPLETED
            or task.result_content is None
            or not task.result_content.strip()
        ):
            raise NoteConflictError("Agent task is not completed")

        note = repository.create(
            user_id=owner.id,
            knowledge_base_id=task.knowledge_base_id,
            title=task.task_input.strip()[:100],
            content=task.result_content,
            source_type=NoteSourceType.AGENT,
            source_agent_task_id=task.id,
        )
        db.commit()
        db.refresh(note)
        return note
    except (NoteNotFoundError, NoteConflictError):
        repository.rollback()
        raise
    except IntegrityError:
        repository.rollback()
        existing = repository.get_by_source_agent_task(
            source_agent_task_id=task_id,
            user_id=owner.id,
        )
        if existing is not None:
            return existing
        logger.exception("Unable to resolve concurrent Agent note save")
        raise NoteDatabaseError
    except SQLAlchemyError as exc:
        repository.rollback()
        logger.exception("Database error while saving an Agent task as a note")
        raise NoteDatabaseError from exc
