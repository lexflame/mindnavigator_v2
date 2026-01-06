from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    area        TEXT    NOT NULL DEFAULT 'Misc',
    title       TEXT    NOT NULL,
    priority    TEXT    NOT NULL DEFAULT 'Medium',   -- Low|Medium|High
    archived    INTEGER NOT NULL DEFAULT 0,          -- 0/1
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_area ON projects(area);
CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(archived);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER,
    day         TEXT    NOT NULL,                    -- YYYY-MM-DD
    time_text   TEXT    NOT NULL DEFAULT '',          -- HH:MM (UI text)
    title       TEXT    NOT NULL,
    priority    TEXT    NOT NULL DEFAULT 'Medium',    -- Low|Medium|High
    done        INTEGER NOT NULL DEFAULT 0,           -- 0/1
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_day ON tasks(day);
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);


-- =========================
-- Maps
-- =========================
CREATE TABLE IF NOT EXISTS maps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    tiles_path  TEXT    NOT NULL,                -- folder with tiles
    tiles_x     INTEGER NOT NULL,
    tiles_y     INTEGER NOT NULL,
    tile_size   INTEGER NOT NULL DEFAULT 512,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_maps_updated ON maps(updated_at);
CREATE INDEX IF NOT EXISTS idx_maps_deleted ON maps(deleted_at);

-- Map markers
CREATE TABLE IF NOT EXISTS map_markers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL,
    title       TEXT    NOT NULL,
    color       TEXT,
    icon        TEXT,
    x           REAL    NOT NULL,
    y           REAL    NOT NULL,
    note        TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at  TEXT,
    FOREIGN KEY(map_id) REFERENCES maps(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_markers_map ON map_markers(map_id);
CREATE INDEX IF NOT EXISTS idx_markers_deleted ON map_markers(deleted_at);

-- Marker links
CREATE TABLE IF NOT EXISTS marker_tasks (
    marker_id   INTEGER NOT NULL,
    task_id     INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(marker_id, task_id),
    FOREIGN KEY(marker_id) REFERENCES map_markers(id) ON DELETE CASCADE,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS marker_projects (
    marker_id   INTEGER NOT NULL,
    project_id  INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(marker_id, project_id),
    FOREIGN KEY(marker_id) REFERENCES map_markers(id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_marker_tasks_task ON marker_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_marker_projects_project ON marker_projects(project_id);

-- =========================
-- Notes
-- =========================
CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER,
    title       TEXT    NOT NULL,
    content     TEXT    NOT NULL DEFAULT '',
    cover_path  TEXT,
    source_url  TEXT,
    folder      TEXT    NOT NULL DEFAULT '',
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at  TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_id);
CREATE INDEX IF NOT EXISTS idx_notes_deleted ON notes(deleted_at);
CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);

-- =========================
-- File storage (files + folders)
-- =========================
CREATE TABLE IF NOT EXISTS files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id       INTEGER,
    is_dir          INTEGER NOT NULL DEFAULT 0,
    name            TEXT    NOT NULL,
    ext             TEXT,
    mime            TEXT,
    size_bytes      INTEGER,
    local_path      TEXT,
    s3_key          TEXT,
    preview_path    TEXT,
    hash_summ_name  TEXT,
    hash_summ_data  TEXT,
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT,
    FOREIGN KEY(parent_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_id);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(deleted_at);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);

CREATE TABLE IF NOT EXISTS file_links (
    file_id     INTEGER NOT NULL,
    entity_type TEXT    NOT NULL,
    entity_id   INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(file_id, entity_type, entity_id),
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_file_links_entity ON file_links(entity_type, entity_id);

"""


def app_root() -> Path:
    # project root is where main.py sits
    return Path(__file__).resolve().parents[1]


def default_db_path() -> Path:
    return app_root() / "data" / "mindnavigator.db"


def ensure_db(db_path: Optional[os.PathLike] = None) -> Path:
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    return path


def connect(db_path: Optional[os.PathLike] = None) -> sqlite3.Connection:
    path = ensure_db(db_path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn
