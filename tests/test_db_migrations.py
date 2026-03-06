from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from mindnavigator.db_migrations import MigrationStep, apply_migrations, get_user_version
from mindnavigator.storage import DEFERRED_PRIORITY, LEGACY_DEFERRED_PRIORITY, Database

def test_apply_migrations_is_versioned_and_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    applied: list[str] = []

    def _step_v1(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE IF NOT EXISTS migration_probe (id INTEGER PRIMARY KEY, marker TEXT NOT NULL);")
        applied.append("v1")

    def _step_v2(connection: sqlite3.Connection) -> None:
        connection.execute("INSERT INTO migration_probe(marker) VALUES ('ok');")
        applied.append("v2")

    steps = [
        MigrationStep(1, "create_probe", _step_v1),
        MigrationStep(2, "seed_probe", _step_v2),
    ]

    assert apply_migrations(conn, steps) == 2
    assert applied == ["v1", "v2"]
    assert get_user_version(conn) == 2

    applied.clear()
    assert apply_migrations(conn, steps) == 2
    assert applied == []


def test_database_applies_versioned_schema_migrations_for_legacy_schema(unique_temp_path) -> None:
    db_path = unique_temp_path("legacy_migration", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        legacy_conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Legacy A", "01.01.2026", "Medium", 0),
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Legacy B", "02.01.2026", "High", 0),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("Legacy task", "2026-02-25", "10:00", "Medium", 0, now, now),
        )
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        project_columns = {
            row["name"] for row in database._conn.execute("PRAGMA table_info(projects);").fetchall()
        }
        task_columns = {
            row["name"] for row in database._conn.execute("PRAGMA table_info(tasks);").fetchall()
        }

        assert "sort_order" in project_columns
        assert "parent_project_id" in project_columns
        assert "marker_color" in project_columns
        assert "repository_catalog" in project_columns
        assert "project_id" in task_columns
        assert "description" in task_columns
        assert "parent_id" in task_columns
        assert "marker_theme" in task_columns
        assert "completion_delay_minutes" in task_columns

        user_version = database._conn.execute("PRAGMA user_version;").fetchone()[0]
        assert user_version == 3

        root_rows = database._conn.execute(
            """
            SELECT title, sort_order
            FROM projects
            WHERE title IN ('Legacy A', 'Legacy B')
            ORDER BY sort_order, id;
            """
        ).fetchall()
        assert [row["title"] for row in root_rows] == ["Legacy A", "Legacy B"]
        assert [int(row["sort_order"]) for row in root_rows] == [0, 1]
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_apply_schema_updates_is_safe_for_repeated_calls(unique_temp_path) -> None:
    db_path = unique_temp_path("apply_schema_updates", ".sqlite3")
    database = Database(path=db_path)
    try:
        with database._conn:
            database._conn.execute("PRAGMA user_version = 1;")
        assert database.apply_schema_updates() == 3
        assert database.apply_schema_updates() == 3
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_database_migration_normalizes_legacy_priority_values(unique_temp_path) -> None:
    db_path = unique_temp_path("legacy_priority_normalize", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        legacy_conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Legacy Deferred Canonical", "01.01.2026", DEFERRED_PRIORITY, 0),
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Legacy Deferred Mojibake", "02.01.2026", LEGACY_DEFERRED_PRIORITY, 0),
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Legacy Deferred Numeric", "03.01.2026", "4", 0),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("Task Deferred Canonical", "2026-02-25", "10:00", DEFERRED_PRIORITY, 0, now, now),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("Task Deferred Mojibake", "2026-02-25", "11:00", LEGACY_DEFERRED_PRIORITY, 0, now, now),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("Task Deferred Numeric", "2026-02-25", "12:00", "4", 0, now, now),
        )
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        valid_priorities = {"Low", "Medium", "High", DEFERRED_PRIORITY}
        task_priorities = {
            row["priority"] for row in database._conn.execute("SELECT DISTINCT priority FROM tasks;").fetchall()
        }
        project_priorities = {
            row["priority"] for row in database._conn.execute("SELECT DISTINCT priority FROM projects;").fetchall()
        }

        assert task_priorities <= valid_priorities
        assert project_priorities <= valid_priorities
        assert DEFERRED_PRIORITY in task_priorities
        assert DEFERRED_PRIORITY in project_priorities
        assert LEGACY_DEFERRED_PRIORITY not in task_priorities
        assert LEGACY_DEFERRED_PRIORITY not in project_priorities
        assert "4" not in task_priorities
        assert "4" not in project_priorities
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_database_migration_recovers_from_stale_projects_old_table(unique_temp_path) -> None:
    db_path = unique_temp_path("stale_projects_old", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        legacy_conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        legacy_conn.execute(
            """
            CREATE TABLE projects_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Current projects row", "01.01.2026", "Medium", 0),
        )
        legacy_conn.execute(
            "INSERT INTO projects_old(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Recovered from projects_old", "02.01.2026", LEGACY_DEFERRED_PRIORITY, 0),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("Task from stale state", "2026-02-25", "10:00", "Medium", 0, now, now),
        )
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        stale_row = database._conn.execute(
            "SELECT priority FROM projects WHERE title = ?;",
            ("Recovered from projects_old",),
        ).fetchone()
        assert stale_row is not None
        assert stale_row["priority"] == DEFERRED_PRIORITY

        projects_old_exists = database._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects_old';"
        ).fetchone()
        assert projects_old_exists is None
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_database_backfills_project_columns_when_user_version_is_current(unique_temp_path) -> None:
    db_path = unique_temp_path("projects_columns_backfill", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        legacy_conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        legacy_conn.execute(
            "INSERT INTO projects(area, title, updated, priority, archived) VALUES (?, ?, ?, ?, ?);",
            ("Work", "Legacy project", "2026-01-01", "Medium", 0),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
            ("Legacy task", "2026-02-25", "10:00", "Medium", 0, now, now),
        )
        # Simulate DB that already reports current user_version but still misses
        # extended projects columns.
        legacy_conn.execute("PRAGMA user_version = 3;")
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        project_columns = {
            row["name"] for row in database._conn.execute("PRAGMA table_info(projects);").fetchall()
        }
        assert "repository_catalog" in project_columns
        assert "marker_color" in project_columns
        assert "marker_theme" in project_columns

        projects = database.fetch_projects()
        assert projects
        assert projects[0].repository_catalog == ""
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
