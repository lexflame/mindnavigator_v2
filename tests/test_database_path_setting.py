from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from mindnavigator import storage
from mindnavigator.storage import Database


def _new_temp_dir(prefix: str) -> Path:
    base_dir = Path.cwd() / ".pytest_tmp_data"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class _FakeConnection:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def execute(self, sql: str):
        self.commands.append(sql)
        return self


def test_configured_database_path_overrides_default(monkeypatch) -> None:
    root_dir = _new_temp_dir("cfg_path")
    app_home = root_dir / "app_home"
    monkeypatch.setattr(storage, "_app_base_dir", lambda: app_home)

    assert storage.get_configured_db_path() is None
    assert storage.get_configured_db_paths() == []
    assert storage.default_db_path() == app_home / "lib" / "db" / "mindnavigator.db"

    configured_path = root_dir / "custom" / "mindnavigator.custom.db"
    saved_path = storage.set_configured_db_path(configured_path)

    assert saved_path == configured_path
    assert storage.get_configured_db_path() == configured_path
    assert storage.get_configured_db_paths() == [configured_path]
    assert storage.default_db_path() == configured_path

    storage.set_configured_db_path(None)
    assert storage.get_configured_db_path() is None
    assert storage.get_configured_db_paths() == [configured_path]
    assert storage.default_db_path() == app_home / "lib" / "db" / "mindnavigator.db"


def test_database_paths_list_supports_add_and_remove(monkeypatch) -> None:
    root_dir = _new_temp_dir("cfg_db_list")
    app_home = root_dir / "app_home"
    monkeypatch.setattr(storage, "_app_base_dir", lambda: app_home)

    first = root_dir / "db" / "first.db"
    second = root_dir / "db" / "second.db"

    assert storage.add_configured_db_path(first) == [first]
    assert storage.add_configured_db_path(second) == [first, second]
    assert storage.get_configured_db_paths() == [first, second]

    storage.set_configured_db_path(second)
    remaining, active = storage.remove_configured_db_path(second)

    assert remaining == [first]
    assert active == first
    assert storage.get_configured_db_path() == first


def test_database_backup_to_copies_current_data() -> None:
    root_dir = _new_temp_dir("backup_copy")
    source_db_path = root_dir / "source.db"
    source_db = Database(path=source_db_path)
    try:
        source_db.create_project(
            area="Work",
            title="Backup Probe",
            updated=date(2026, 2, 25),
            priority="Medium",
        )
        target_db_path = root_dir / "nested" / "copied.db"
        source_db.backup_to(target_db_path)
    finally:
        source_db.close()

    copied_db = Database(path=target_db_path)
    try:
        titles = {project.title for project in copied_db.fetch_projects()}
        assert "Backup Probe" in titles
    finally:
        copied_db.close()


def test_reset_database_uses_configured_path(monkeypatch) -> None:
    root_dir = _new_temp_dir("reset_db")
    app_home = root_dir / "app_home"
    monkeypatch.setattr(storage, "_app_base_dir", lambda: app_home)
    configured_path = root_dir / "switch_target" / "mindnavigator.db"
    storage.set_configured_db_path(configured_path)

    db = storage.reset_database()
    try:
        assert db.path == configured_path
    finally:
        db.close()
        storage.get_database.cache_clear()
        storage.set_configured_db_path(None)


def test_unc_database_path_uses_rollback_journal_mode() -> None:
    fake_connection = _FakeConnection()
    unc_path = Path(r"\\gtx\YandexDisk\.mindnavigator\mindnavigator.db")

    assert storage.is_network_database_path(unc_path) is True
    storage._configure_connection_pragmas(fake_connection, unc_path)

    assert fake_connection.commands[0] == "PRAGMA journal_mode=DELETE;"
    assert fake_connection.commands[1] == f"PRAGMA busy_timeout={storage.SQLITE_BUSY_TIMEOUT_MS};"
    assert fake_connection.commands[2] == "PRAGMA synchronous=NORMAL;"
    assert fake_connection.commands[3] == "PRAGMA foreign_keys=ON;"


def test_local_database_path_keeps_wal_journal_mode() -> None:
    fake_connection = _FakeConnection()
    local_path = Path.cwd() / "mindnavigator.db"

    assert storage.is_network_database_path(local_path) is False
    storage._configure_connection_pragmas(fake_connection, local_path)

    assert fake_connection.commands[0] == "PRAGMA journal_mode=WAL;"
