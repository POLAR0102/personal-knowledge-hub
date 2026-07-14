import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import configure_logging
from app.core.security import verify_password
from app.db.base import Base
from app.db.models import Document, KnowledgeBase, User
from scripts.backup_data import create_backup
from scripts.seed_demo import (
    DEFAULT_PASSWORD,
    DEMO_DOCUMENT_CONTENT,
    resolve_demo_password,
    seed_demo_data,
)


def test_logging_writes_rotating_file(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "app.log"
    settings = Settings(
        _env_file=None,
        log_level="WARNING",
        log_file=log_file,
        log_max_bytes=1024,
        log_backup_count=2,
    )

    try:
        configure_logging(settings)
        logging.getLogger("tests.operations").warning("operational warning")
        for handler in logging.getLogger().handlers:
            handler.flush()

        assert "operational warning" in log_file.read_text(encoding="utf-8")
    finally:
        configure_logging(Settings(_env_file=None))


def test_logging_rejects_invalid_rotation_limits() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_max_bytes=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_backup_count=0)


def test_backup_copies_database_uploads_and_chroma(tmp_path: Path) -> None:
    database_path = tmp_path / "app.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sample VALUES ('backed-up')")

    upload_dir = tmp_path / "uploads"
    chroma_dir = tmp_path / "chroma"
    upload_dir.mkdir()
    chroma_dir.mkdir()
    (upload_dir / "document.txt").write_text("document", encoding="utf-8")
    (chroma_dir / "chroma.sqlite3").write_bytes(b"vector-data")
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{database_path.as_posix()}",
        upload_dir=upload_dir,
        chroma_persist_dir=chroma_dir,
    )

    backup_directory = create_backup(
        settings,
        tmp_path / "backups",
        created_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    with sqlite3.connect(backup_directory / "database.sqlite3") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone() == (
            "backed-up",
        )
    assert (backup_directory / "uploads" / "document.txt").read_text(
        encoding="utf-8"
    ) == "document"
    assert (backup_directory / "chroma" / "chroma.sqlite3").read_bytes() == (
        b"vector-data"
    )
    manifest_text = (backup_directory / "manifest.json").read_text(
        encoding="utf-8"
    )
    manifest = json.loads(manifest_text)
    assert manifest["components"] == {
        "database": "database.sqlite3",
        "uploads": "uploads",
        "chroma": "chroma",
    }
    assert "database_url" not in manifest_text.lower()
    assert "api_key" not in manifest_text.lower()


def test_backup_rejects_non_sqlite_database(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://example.invalid/app",
    )

    with pytest.raises(ValueError, match="supports SQLite only"):
        create_backup(settings, tmp_path / "backups")


def test_backup_removes_incomplete_directory_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "app.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE sample (value TEXT NOT NULL)")
    upload_dir = tmp_path / "uploads"
    chroma_dir = tmp_path / "chroma"
    upload_dir.mkdir()
    chroma_dir.mkdir()
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{database_path.as_posix()}",
        upload_dir=upload_dir,
        chroma_persist_dir=chroma_dir,
    )
    backup_root = tmp_path / "backups"
    created_at = datetime(2026, 7, 14, tzinfo=timezone.utc)

    def fail_backup(_source: Path, _destination: Path) -> None:
        raise OSError("simulated backup failure")

    monkeypatch.setattr("scripts.backup_data._backup_sqlite", fail_backup)
    with pytest.raises(OSError, match="simulated backup failure"):
        create_backup(settings, backup_root, created_at=created_at)

    assert not (backup_root / "20260714T000000000000Z").exists()
    assert not (backup_root / ".20260714T000000000000Z.incomplete").exists()


def test_demo_seed_is_idempotent(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'seed.db').as_posix()}")
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, upload_dir=tmp_path / "uploads")

    with Session(engine) as db:
        first = seed_demo_data(
            db,
            settings,
            email="demo@example.com",
            username="演示用户",
            password=DEFAULT_PASSWORD,
        )
        second = seed_demo_data(
            db,
            settings,
            email="demo@example.com",
            username="不会覆盖已有用户",
            password="DifferentPassword123!",
        )

        assert first.created_user is True
        assert first.created_knowledge_base is True
        assert first.created_document is True
        assert second.created_user is False
        assert second.created_knowledge_base is False
        assert second.created_document is False
        assert (first.user_id, first.knowledge_base_id, first.document_id) == (
            second.user_id,
            second.knowledge_base_id,
            second.document_id,
        )
        assert db.scalar(select(func.count(User.id))) == 1
        assert db.scalar(select(func.count(KnowledgeBase.id))) == 1
        assert db.scalar(select(func.count(Document.id))) == 1
        user = db.get(User, first.user_id)
        document = db.get(Document, first.document_id)
        assert user is not None
        assert document is not None
        assert verify_password(DEFAULT_PASSWORD, user.password_hash)
        assert Path(document.file_path).read_text(encoding="utf-8") == (
            DEMO_DOCUMENT_CONTENT
        )


def test_production_demo_seed_requires_explicit_password() -> None:
    with pytest.raises(ValueError, match="--password is required"):
        resolve_demo_password("production", None)

    assert resolve_demo_password("production", "ExplicitPassword123!") == (
        "ExplicitPassword123!"
    )
    with pytest.raises(ValueError, match="at least 6 characters"):
        resolve_demo_password("production", "")
