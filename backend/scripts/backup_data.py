import argparse
import json
import shutil
import sqlite3
import sys
from collections.abc import Iterable
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings


def create_backup(
    settings: Settings,
    output_root: Path,
    *,
    created_at: datetime | None = None,
) -> Path:
    database_path = _sqlite_database_path(settings.database_url)
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {database_path}")

    sources = {
        "uploads": settings.upload_dir.expanduser().resolve(),
        "chroma": settings.chroma_persist_dir.expanduser().resolve(),
    }
    resolved_output_root = output_root.expanduser().resolve()
    _ensure_output_is_separate(resolved_output_root, sources.values())

    current_time = created_at or datetime.now(timezone.utc)
    backup_name = current_time.strftime("%Y%m%dT%H%M%S%fZ")
    backup_directory = resolved_output_root / backup_name
    working_directory = resolved_output_root / f".{backup_name}.incomplete"
    if backup_directory.exists():
        raise FileExistsError(f"Backup already exists: {backup_directory}")
    working_directory.mkdir(parents=True, exist_ok=False)

    try:
        database_target = working_directory / "database.sqlite3"
        _backup_sqlite(database_path, database_target)

        components: dict[str, str | None] = {"database": database_target.name}
        for name, source in sources.items():
            if source.is_dir():
                destination = working_directory / name
                shutil.copytree(source, destination)
                components[name] = destination.name
            else:
                components[name] = None

        manifest = {
            "version": 1,
            "created_at": current_time.astimezone(timezone.utc).isoformat(),
            "database_backend": "sqlite",
            "components": components,
        }
        (working_directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        working_directory.rename(backup_directory)
    except Exception:
        shutil.rmtree(working_directory, ignore_errors=True)
        raise
    return backup_directory


def _sqlite_database_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError(
            "This backup script supports SQLite only; use the database vendor's "
            "native backup tool for other databases"
        )
    if not url.database or url.database == ":memory:" or url.database.startswith("file:"):
        raise ValueError("A file-based SQLite DATABASE_URL is required")
    return Path(url.database).expanduser().resolve()


def _backup_sqlite(source: Path, destination: Path) -> None:
    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)


def _ensure_output_is_separate(
    output_root: Path,
    source_directories: Iterable[Path],
) -> None:
    for source in source_directories:
        if output_root.is_relative_to(source):
            raise ValueError("Backup output cannot be inside uploads or Chroma data")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back up SQLite, uploaded files, and persistent ChromaDB data."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./backups"),
        help="Directory that will contain timestamped backup folders.",
    )
    args = parser.parse_args()

    try:
        backup_directory = create_backup(get_settings(), args.output_dir)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        return 1

    manifest = json.loads(
        (backup_directory / "manifest.json").read_text(encoding="utf-8")
    )
    missing_components = [
        name
        for name, path in manifest["components"].items()
        if path is None
    ]
    if missing_components:
        print(
            "Backup warning: source directories were absent for "
            + ", ".join(missing_components),
            file=sys.stderr,
        )
    print(f"Backup created: {backup_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
