from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from mindnavigator.spaceenity.db_migrations import MigrationStep, apply_migrations, get_user_version
from mindnavigator.storage import BOARD_COLUMN_DEFERRED, BOARD_COLUMN_QUEUE, DEFERRED_PRIORITY, LEGACY_DEFERRED_PRIORITY, Database

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
        assert "board_column" in task_columns
        assert "description" in task_columns
        assert "parent_id" in task_columns
        assert "is_plan_task" in task_columns
        assert "plan_order" in task_columns
        assert "marker_theme" in task_columns
        assert "completion_delay_minutes" in task_columns
        assert "started_at" in task_columns
        assert "finished_at" in task_columns
        assert "actual_minutes" in task_columns
        dossier_tables = {
            row["name"]
            for row in database._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('dossiers', 'dossier_links');"
            ).fetchall()
        }
        assert dossier_tables == {"dossiers", "dossier_links"}

        user_version = database._conn.execute("PRAGMA user_version;").fetchone()[0]
        assert user_version == 7

        board_rows = database._conn.execute(
            "SELECT title, board_column FROM tasks WHERE title = 'Legacy task';"
        ).fetchall()
        assert len(board_rows) == 1
        assert board_rows[0]["board_column"] == BOARD_COLUMN_QUEUE

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
        assert database.apply_schema_updates() == 7
        assert database.apply_schema_updates() == 7
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_apply_schema_updates_backfills_dossier_schema_when_user_version_is_current(unique_temp_path) -> None:
    db_path = unique_temp_path("apply_schema_updates_dossier_backfill", ".sqlite3")
    database = Database(path=db_path)
    try:
        with database._conn:
            database._conn.execute("DROP TABLE dossier_links;")
            database._conn.execute("DROP TABLE dossiers;")
            database._conn.execute("PRAGMA user_version = 5;")

        assert database.apply_schema_updates() == 7

        dossier_tables = {
            row["name"]
            for row in database._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('dossiers', 'dossier_links');"
            ).fetchall()
        }
        assert dossier_tables == {"dossiers", "dossier_links"}
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


def test_database_migration_repairs_idea_project_fk_after_projects_rebuild(unique_temp_path) -> None:
    db_path = unique_temp_path("ideas_projects_old_fk", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.executescript(
            f"""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
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
            CREATE TABLE ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                body_md TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT 'other',
                status TEXT NOT NULL DEFAULT 'inbox',
                value_score INTEGER NOT NULL DEFAULT 3,
                effort_score INTEGER NOT NULL DEFAULT 3,
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT
            );
            CREATE TABLE projects_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO projects(area, title, updated, priority, archived)
            VALUES ('Work', 'Current projects row', '01.01.2026', 'Medium', 0);
            INSERT INTO projects_old(area, title, updated, priority, archived)
            VALUES ('Work', 'Recovered from projects_old', '02.01.2026', '{LEGACY_DEFERRED_PRIORITY}', 0);
            INSERT INTO tasks(title, day, time_text, priority, done, created_at, updated_at)
            VALUES ('Task from stale state', '2026-02-25', '10:00', 'Medium', 0, '{now}', '{now}');
            INSERT INTO ideas(project_id, title, summary, body_md, type, status, value_score, effort_score, source, created_at, updated_at, archived_at)
            VALUES (1, 'Idea from stale state', '', '', 'other', 'inbox', 3, 3, '', '{now}', '{now}', NULL);
            """
        )
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        fk_rows = database._conn.execute("PRAGMA foreign_key_list(ideas);").fetchall()
        project_refs = [row for row in fk_rows if row["from"] == "project_id"]
        assert project_refs
        assert all(row["table"] == "projects" for row in project_refs)

        updated = database.update_idea(
            1,
            title="Idea after repair",
            summary="updated",
            body_md="body",
            idea_type="other",
            status="work",
            value_score=4,
            effort_score=2,
            project_id=1,
        )
        assert updated.title == "Idea after repair"
        assert updated.status == "work"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_database_repairs_idea_project_fk_even_when_user_version_is_current(unique_temp_path) -> None:
    db_path = unique_temp_path("ideas_projects_old_fk_current_version", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.executescript(
            f"""
            PRAGMA user_version = 6;
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', '{DEFERRED_PRIORITY}')),
                archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
                parent_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                default_task_priority TEXT NOT NULL DEFAULT '',
                force_recurrence_kind TEXT NOT NULL DEFAULT '',
                linked_map_id INTEGER REFERENCES maps(id) ON DELETE SET NULL,
                linked_note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
                linked_object_id INTEGER REFERENCES objects(id) ON DELETE SET NULL,
                repository_catalog TEXT NOT NULL DEFAULT '',
                marker_color TEXT NOT NULL DEFAULT '',
                marker_theme TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', '{DEFERRED_PRIORITY}')),
                board_column TEXT NOT NULL DEFAULT '{BOARD_COLUMN_QUEUE}' CHECK (board_column IN ('{BOARD_COLUMN_DEFERRED}', '{BOARD_COLUMN_QUEUE}', 'in_progress', 'completed')),
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                completion_delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK (completion_delay_minutes >= 0),
                gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0 CHECK (gantt_estimate_minutes >= 0),
                gantt_forecasted INTEGER NOT NULL DEFAULT 0 CHECK (gantt_forecasted IN (0, 1)),
                project_id INTEGER REFERENCES projects_old(id),
                parent_id INTEGER REFERENCES tasks(id),
                recurrence_kind TEXT NOT NULL DEFAULT '',
                recurrence_interval INTEGER NOT NULL DEFAULT 1 CHECK (recurrence_interval >= 1),
                is_plan_task INTEGER NOT NULL DEFAULT 0 CHECK (is_plan_task IN (0, 1)),
                plan_order INTEGER NOT NULL DEFAULT 0,
                marker_color TEXT NOT NULL DEFAULT '',
                marker_theme TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects_old(id) ON DELETE SET NULL,
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                body_md TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT 'other' CHECK (type IN ('feature', 'story', 'art', 'research', 'tech', 'other')),
                status TEXT NOT NULL DEFAULT 'inbox' CHECK (status IN ('inbox', 'work', 'ripe', 'done', 'archived')),
                value_score INTEGER NOT NULL DEFAULT 3 CHECK (value_score BETWEEN 1 AND 5),
                effort_score INTEGER NOT NULL DEFAULT 3 CHECK (effort_score BETWEEN 1 AND 5),
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT
            );
            CREATE TABLE projects_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                project TEXT NOT NULL DEFAULT '',
                tiles_path TEXT NOT NULL DEFAULT '',
                tiles_h INTEGER NOT NULL,
                tiles_w INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                preview TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                project TEXT NOT NULL DEFAULT '',
                favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
                attachment INTEGER NOT NULL DEFAULT 0 CHECK (attachment IN (0, 1)),
                locked INTEGER NOT NULL DEFAULT 0 CHECK (locked IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                catalog TEXT NOT NULL DEFAULT '',
                object_type TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO projects(area, title, updated, priority, archived, sort_order)
            VALUES ('Work', 'Current projects row', '2026-01-01', 'Medium', 0, 0);
            INSERT INTO ideas(project_id, title, summary, body_md, type, status, value_score, effort_score, source, created_at, updated_at, archived_at)
            VALUES (1, 'Idea from stale current schema', '', '', 'other', 'inbox', 3, 3, '', '{now}', '{now}', NULL);
            """
        )
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        fk_rows = database._conn.execute("PRAGMA foreign_key_list(ideas);").fetchall()
        project_refs = [row for row in fk_rows if row["from"] == "project_id"]
        assert project_refs
        assert all(row["table"] == "projects" for row in project_refs)

        updated = database.update_idea(
            1,
            title="Idea after current-version repair",
            summary="updated",
            body_md="body",
            idea_type="other",
            status="work",
            value_score=4,
            effort_score=2,
            project_id=1,
        )
        assert updated.title == "Idea after current-version repair"
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
        legacy_conn.execute("PRAGMA user_version = 5;")
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


def test_database_backfills_task_board_column_when_missing(unique_temp_path) -> None:
    db_path = unique_temp_path("tasks_board_column_backfill", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
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
            "INSERT INTO tasks(title, description, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            ("Deferred legacy", "", "2026-02-25", "10:00", DEFERRED_PRIORITY, 0, now, now),
        )
        legacy_conn.execute(
            "INSERT INTO tasks(title, description, day, time_text, priority, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            ("Queued legacy", "", "2026-02-25", "11:00", "Medium", 0, now, now),
        )
        legacy_conn.execute("PRAGMA user_version = 5;")
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        board_rows = {
            row["title"]: row["board_column"]
            for row in database._conn.execute("SELECT title, board_column FROM tasks;").fetchall()
        }
        assert board_rows["Deferred legacy"] == BOARD_COLUMN_DEFERRED
        assert board_rows["Queued legacy"] == BOARD_COLUMN_QUEUE
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_database_backfills_task_execution_columns_when_migrating_from_v6(unique_temp_path) -> None:
    db_path = unique_temp_path("tasks_execution_column_backfill", ".sqlite3")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    legacy_conn = sqlite3.connect(db_path)
    with legacy_conn:
        legacy_conn.execute(
            f"""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', '{DEFERRED_PRIORITY}')),
                board_column TEXT NOT NULL DEFAULT '{BOARD_COLUMN_QUEUE}' CHECK (board_column IN ('{BOARD_COLUMN_DEFERRED}', '{BOARD_COLUMN_QUEUE}', 'in_progress', 'completed')),
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                completion_delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK (completion_delay_minutes >= 0),
                gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0 CHECK (gantt_estimate_minutes >= 0),
                gantt_forecasted INTEGER NOT NULL DEFAULT 0 CHECK (gantt_forecasted IN (0, 1)),
                project_id INTEGER,
                parent_id INTEGER REFERENCES tasks(id),
                recurrence_kind TEXT NOT NULL DEFAULT '',
                recurrence_interval INTEGER NOT NULL DEFAULT 1 CHECK (recurrence_interval >= 1),
                is_plan_task INTEGER NOT NULL DEFAULT 0 CHECK (is_plan_task IN (0, 1)),
                plan_order INTEGER NOT NULL DEFAULT 0,
                marker_color TEXT NOT NULL DEFAULT '',
                marker_theme TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        legacy_conn.execute(
            """
            INSERT INTO tasks(title, description, day, time_text, priority, done, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("Legacy execution task", "", "2026-02-25", "10:00", "Medium", 0, now, now),
        )
        legacy_conn.execute("PRAGMA user_version = 6;")
    legacy_conn.close()

    database = Database(path=db_path)
    try:
        task_columns = {
            row["name"] for row in database._conn.execute("PRAGMA table_info(tasks);").fetchall()
        }
        assert "started_at" in task_columns
        assert "finished_at" in task_columns
        assert "actual_minutes" in task_columns
        assert database._conn.execute("PRAGMA user_version;").fetchone()[0] == 7

        row = database._conn.execute(
            "SELECT started_at, finished_at, actual_minutes FROM tasks WHERE title = ?;",
            ("Legacy execution task",),
        ).fetchone()
        assert row is not None
        assert row["started_at"] == ""
        assert row["finished_at"] == ""
        assert int(row["actual_minutes"]) == 0
    finally:
        database.close()
        db_path.unlink(missing_ok=True)
