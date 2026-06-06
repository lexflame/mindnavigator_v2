"""DatabaseCoreMixin for storage database operations."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from ._shared import *  # noqa: F401,F403

class DatabaseCoreMixin:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=SQLITE_BUSY_TIMEOUT_MS / 1000,
        )
        self._conn.row_factory = sqlite3.Row
        self._closed = False
        self._transaction_counter = 0
        self._init_db()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Runs a write operation in a nestable SQLite savepoint."""
        self._transaction_counter += 1
        savepoint = f"mn_transaction_{self._transaction_counter}"
        self._conn.execute(f"SAVEPOINT {savepoint};")
        try:
            yield
        except Exception:
            self._conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint};")
            self._conn.execute(f"RELEASE SAVEPOINT {savepoint};")
            raise
        else:
            self._conn.execute(f"RELEASE SAVEPOINT {savepoint};")

    def reindex(self) -> None:
        """Переиндексирует таблицы базы данных."""
        with self._conn:
            self._conn.execute("REINDEX;")

    def backup_to(self, destination_path: Path) -> Path:
        """Создает консистентную копию базы данных в указанный файл."""
        destination_path = Path(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.resolve() == self.path.resolve():
            return destination_path
        tmp_target = destination_path.with_suffix(f"{destination_path.suffix}.tmp")
        if tmp_target.exists():
            tmp_target.unlink()
        with self._conn:
            self._conn.execute("PRAGMA wal_checkpoint(FULL);")
        target_conn = sqlite3.connect(tmp_target)
        try:
            self._conn.backup(target_conn)
            target_conn.commit()
        finally:
            target_conn.close()
        tmp_target.replace(destination_path)
        return destination_path

    def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self._closed:
            return
        self._conn.close()
        self._closed = True

__all__ = ["DatabaseCoreMixin"]
