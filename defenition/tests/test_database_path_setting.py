from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from mindnavigator import storage
from mindnavigator.storage import Database


def _new_temp_dir(prefix: str) -> Path:
    base_dir = Path.cwd() / ".pytest_dir" / "tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{prefix}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_configured_database_path_overrides_default(monkeypatch) -> None:
    root_dir = _new_temp_dir("cfg_path")
    app_home = root_dir / "app_home"
    monkeypatch.setattr(storage, "_app_base_dir", lambda: app_home)

    assert storage.get_configured_db_path() is None
    assert storage.default_db_path() == app_home / "mindnavigator.db"

    configured_path = root_dir / "custom" / "mindnavigator.custom.db"
    saved_path = storage.set_configured_db_path(configured_path)

    assert saved_path == configured_path
    assert storage.get_configured_db_path() == configured_path
    assert storage.default_db_path() == configured_path

    storage.set_configured_db_path(None)
    assert storage.get_configured_db_path() is None
    assert storage.default_db_path() == app_home / "mindnavigator.db"


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
