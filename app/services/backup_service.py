from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import shutil
import sqlite3

from flask import current_app


class BackupServiceError(Exception):
    pass


@dataclass(frozen=True)
class BackupResult:
    path: Path
    size_bytes: int
    created_at: datetime
    operation_label: str


def create_database_backup(operation_label: str) -> BackupResult:
    source = _sqlite_database_path()
    if source is None:
        raise BackupServiceError("A base de dados configurada nao e um ficheiro SQLite.")
    if not source.exists():
        raise BackupServiceError(f"A base de dados real nao existe: {source}")

    created_at = datetime.now(UTC)
    safe_label = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in operation_label.strip().lower()
    ).strip("_") or "backup"
    target_dir = Path(current_app.instance_path) / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"escala_{created_at:%Y%m%d_%H%M%S}_{safe_label}.db"

    shutil.copy2(source, target)
    size_bytes = target.stat().st_size
    if size_bytes <= 0:
        target.unlink(missing_ok=True)
        raise BackupServiceError("O backup foi criado vazio e foi rejeitado.")
    _validate_sqlite(target)
    return BackupResult(
        path=target,
        size_bytes=size_bytes,
        created_at=created_at,
        operation_label=safe_label,
    )


def _sqlite_database_path() -> Path | None:
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    prefix = "sqlite:///"
    if not uri.startswith(prefix) or uri == "sqlite:///:memory:":
        return None
    return Path(uri.removeprefix(prefix)).resolve()


def _validate_sqlite(path: Path) -> None:
    try:
        with sqlite3.connect(path) as connection:
            result = connection.execute("pragma integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise BackupServiceError(f"Backup SQLite invalido: {exc}") from exc
    if not result or result[0] != "ok":
        raise BackupServiceError("Backup SQLite falhou integrity_check.")
