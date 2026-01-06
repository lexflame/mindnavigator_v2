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
