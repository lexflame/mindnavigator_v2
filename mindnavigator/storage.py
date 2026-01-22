"""Работа с локальной базой данных и валидаторами.

Входные данные:
    Параметры моделей, SQL-запросы и значения полей сущностей.

Выходные данные:
    Записи базы данных, проверенные строки и объект подключения.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

PRIORITIES = ("Low", "Medium", "High", "Отложенная")
MAX_TITLE_LEN = 160
MAX_AREA_LEN = 80


@dataclass(frozen=True)
class TaskData:
    id: int
    day: date
    time_text: str
    title: str
    description: str
    priority: str
    done: bool
    project_id: Optional[int] = None
    project_title: str = ""
    project_area: str = ""
    parent_id: Optional[int] = None


@dataclass(frozen=True)
class ProjectData:
    id: int
    area: str
    title: str
    updated: date
    priority: str
    archived: bool


@dataclass(frozen=True)
class MapData:
    id: int
    title: str
    description: str
    project: str
    tiles_path: str
    tiles_h: int
    tiles_w: int


@dataclass(frozen=True)
class MapMarkerData:
    id: int
    map_id: int
    name: str
    x: float
    y: float
    color: str
    type: str
    size: float
    description: str
    properties: str
    task_ids: List[int]
    project_ids: List[int]
    note_ids: List[int]
    object_ids: List[int]
    file_ids: List[int]
    map_ids: List[int]
    marker_ids: List[int]
    parent_path: str
    image_path: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class TaskAttachmentData:
    id: int
    task_id: int
    kind: str
    ref_id: int
    created_at: str


@dataclass(frozen=True)
class CloudFileData:
    id: int
    rel_path: str
    name: str
    description: str
    checksum: str
    hash_value: str
    size: int
    is_image: bool
    valid: bool
    updated_at: str


@dataclass(frozen=True)
class NoteData:
    id: int
    title: str
    preview: str
    tags: List[str]
    updated: datetime
    project: str
    favorite: bool = False
    attachment: bool = False
    locked: bool = False


@dataclass(frozen=True)
class IdeaData:
    id: int
    project_id: Optional[int]
    title: str
    summary: str
    body_md: str
    type: str
    status: str
    value_score: int
    effort_score: int
    source: str
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    project_title: str = ""


@dataclass(frozen=True)
class IdeaRelationData:
    id: int
    idea_id: int
    entity_type: str
    entity_id: int
    created_at: datetime


@dataclass(frozen=True)
class ObjectData:
    id: int
    title: str
    catalog: str
    object_type: str
    status: str
    description: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ObjectImageData:
    id: int
    object_id: int
    rel_path: str
    description: str
    created_at: str
    updated_at: str


def default_db_path() -> Path:
    """Возвращает путь к файлу базы данных приложения."""
    base = Path.home() / ".mindnavigator"
    base.mkdir(parents=True, exist_ok=True)
    return base / "mindnavigator.db"


def validate_title(title: str, field_name: str = "Название") -> str:
    """Проверяет и нормализует название."""
    title = (title or "").strip()
    if not title:
        raise ValueError(f"{field_name} не должно быть пустым.")
    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f"{field_name} слишком длинное (до {MAX_TITLE_LEN} символов).")
    return title


def validate_area(area: str) -> str:
    """Проверяет и нормализует область проекта."""
    area = (area or "").strip()
    if not area:
        raise ValueError("Область проекта не должна быть пустой.")
    if len(area) > MAX_AREA_LEN:
        raise ValueError(f"Область проекта слишком длинная (до {MAX_AREA_LEN} символов).")
    return area


def normalize_priority(priority: str) -> str:
    """Нормализует и проверяет значение приоритета."""
    priority = (priority or "").strip() or "Medium"
    if priority not in PRIORITIES:
        raise ValueError("Приоритет должен быть Low, Medium, High или Отложенная.")
    return priority


def validate_time_text(time_text: str) -> str:
    """Проверяет формат времени."""
    time_text = (time_text or "").strip()
    if not time_text:
        return ""
    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError as exc:
        raise ValueError("Время должно быть в формате HH:MM.") from exc
    return time_text


def parse_project_date(value: str) -> date:
    """Парсит дату проекта в формате dd.mm.yyyy."""
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError("Дата проекта должна быть в формате dd.mm.yyyy.") from exc


def format_project_date(value: date) -> str:
    """Форматирует дату проекта для интерфейса."""
    return value.strftime("%d.%m.%Y")


class Database:
    """Работает с локальной базой данных приложения."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else default_db_path()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._closed = False
        self._init_db()

    def _init_db(self) -> None:
        """Инициализирует схему и параметры SQLite."""
        with self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    day TEXT NOT NULL,
                    time_text TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
                    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                    project_id INTEGER REFERENCES projects(id),
                    parent_id INTEGER REFERENCES tasks(id),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area TEXT NOT NULL,
                    title TEXT NOT NULL,
                    updated TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
                    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS maps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    project TEXT NOT NULL DEFAULT '',
                    tiles_path TEXT NOT NULL DEFAULT '',
                    tiles_h INTEGER NOT NULL CHECK (tiles_h > 0),
                    tiles_w INTEGER NOT NULL CHECK (tiles_w > 0),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS map_markers (
                    id INTEGER PRIMARY KEY,
                    map_id INTEGER NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    color TEXT NOT NULL,
                    type TEXT NOT NULL,
                    size REAL NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    properties TEXT NOT NULL DEFAULT '',
                    task_ids TEXT NOT NULL DEFAULT '[]',
                    project_ids TEXT NOT NULL DEFAULT '[]',
                    note_ids TEXT NOT NULL DEFAULT '[]',
                    object_ids TEXT NOT NULL DEFAULT '[]',
                    file_ids TEXT NOT NULL DEFAULT '[]',
                    map_ids TEXT NOT NULL DEFAULT '[]',
                    marker_ids TEXT NOT NULL DEFAULT '[]',
                    parent_path TEXT NOT NULL DEFAULT '',
                    image_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
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
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
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
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idea_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(idea_id, url)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idea_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                    tag_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(idea_id, tag_text)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idea_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(idea_id, entity_type, entity_id)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    ref_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(task_id, kind, ref_id)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    catalog TEXT NOT NULL DEFAULT '',
                    object_type TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS object_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
                    rel_path TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(object_id, rel_path)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT ''
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cloud_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rel_path TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    checksum TEXT NOT NULL,
                    hash_value TEXT NOT NULL DEFAULT '',
                    size INTEGER NOT NULL DEFAULT 0,
                    is_image INTEGER NOT NULL DEFAULT 0 CHECK (is_image IN (0, 1)),
                    valid INTEGER NOT NULL DEFAULT 0 CHECK (valid IN (0, 1)),
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_day ON tasks(day);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_area ON projects(area);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(archived);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_maps_project ON maps(project);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_map_markers_map ON map_markers(map_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_project_id ON ideas(project_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_type ON ideas(type);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_updated_at ON ideas(updated_at);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_archived_at ON ideas(archived_at);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_links_idea_id ON idea_links(idea_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_tags_idea_id ON idea_tags(idea_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_relations_idea_id ON idea_relations(idea_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_task_attachments_task ON task_attachments(task_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_objects_catalog ON objects(catalog);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_object_images_object ON object_images(object_id);")

        self._ensure_task_project_column()
        self._ensure_task_description_column()
        self._ensure_task_parent_column()
        self._ensure_priority_values()
        self._ensure_map_tiles_path_column()
        self._ensure_marker_attachment_columns()
        self._ensure_marker_parent_path_column()
        self._ensure_marker_image_column()
        self._ensure_map_marker_foreign_keys()
        self._seed_defaults()

    def _ensure_task_project_column(self) -> None:
        """Добавляет колонку project_id, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "project_id" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER REFERENCES projects(id);")

    def _ensure_task_description_column(self) -> None:
        """Добавляет колонку description, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "description" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT '';")

    def _ensure_task_parent_column(self) -> None:
        """Добавляет колонку parent_id, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "parent_id" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER REFERENCES tasks(id);")

    def _ensure_priority_values(self) -> None:
        """Обновляет ограничения приоритета до актуального списка значений."""
        if (
            self._priority_constraint_is_current("tasks")
            and self._priority_constraint_is_current("projects")
            and not self._task_project_fk_needs_repair()
        ):
            return
        with self._conn:
            self._conn.execute("PRAGMA foreign_keys=OFF;")
            projects_rebuilt = False
            if not self._priority_constraint_is_current("projects"):
                self._rebuild_projects_table()
                projects_rebuilt = True
            if projects_rebuilt or not self._priority_constraint_is_current("tasks") or self._task_project_fk_needs_repair():
                self._rebuild_tasks_table()
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._ensure_priority_indexes()

    def _task_project_fk_needs_repair(self) -> bool:
        """Проверяет, что project_id в tasks ссылается на таблицу projects."""
        rows = self._conn.execute("PRAGMA foreign_key_list(tasks);").fetchall()
        project_refs = [row for row in rows if row["from"] == "project_id"]
        if not project_refs:
            return True
        return any(row["table"] != "projects" for row in project_refs)

    def _repair_task_project_fk(self) -> None:
        """Исправляет внешние ключи tasks.project_id, если они ссылаются на отсутствующую таблицу."""
        tables = {
            row["name"]
            for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        if "tasks" not in tables:
            return
        rows = self._conn.execute("PRAGMA foreign_key_list(tasks);").fetchall()
        project_refs = [row for row in rows if row["from"] == "project_id"]
        if not project_refs:
            return
        if all(ref["table"] == "projects" and ref["table"] in tables for ref in project_refs):
            return
        with self._conn:
            self._conn.execute("PRAGMA foreign_keys=OFF;")
            self._rebuild_tasks_table()
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._ensure_priority_indexes()

    def _map_marker_fk_needs_repair(self) -> bool:
        """Проверяет, что внешние ключи map_markers не ссылаются на отсутствующие таблицы."""
        tables = {
            row["name"]
            for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        if "map_markers" not in tables:
            return False
        rows = self._conn.execute("PRAGMA foreign_key_list(map_markers);").fetchall()
        if not rows:
            return False
        return any(row["table"] not in tables for row in rows)

    def _ensure_map_marker_foreign_keys(self) -> None:
        """Исправляет устаревшие внешние ключи map_markers, если таблица-источник отсутствует."""
        if not self._map_marker_fk_needs_repair():
            return
        with self._conn:
            self._conn.execute("PRAGMA foreign_keys=OFF;")
            self._rebuild_map_markers_table()
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_map_markers_map ON map_markers(map_id);")

    def _rebuild_map_markers_table(self) -> None:
        columns = self._conn.execute("PRAGMA table_info(map_markers);").fetchall()
        names = {row["name"] for row in columns}
        if not names:
            return
        self._conn.execute("ALTER TABLE map_markers RENAME TO map_markers_old;")
        self._conn.execute(
            """
            CREATE TABLE map_markers (
                id INTEGER PRIMARY KEY,
                map_id INTEGER NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                color TEXT NOT NULL,
                type TEXT NOT NULL,
                size REAL NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                properties TEXT NOT NULL DEFAULT '',
                task_ids TEXT NOT NULL DEFAULT '[]',
                project_ids TEXT NOT NULL DEFAULT '[]',
                note_ids TEXT NOT NULL DEFAULT '[]',
                object_ids TEXT NOT NULL DEFAULT '[]',
                file_ids TEXT NOT NULL DEFAULT '[]',
                map_ids TEXT NOT NULL DEFAULT '[]',
                marker_ids TEXT NOT NULL DEFAULT '[]',
                parent_path TEXT NOT NULL DEFAULT '',
                image_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        rows = self._conn.execute("SELECT * FROM map_markers_old;").fetchall()
        now = datetime.utcnow().isoformat(timespec="seconds")
        for row in rows:
            row_keys = set(row.keys())

            def _value(key: str, default):
                if key in row_keys and row[key] is not None:
                    return row[key]
                return default

            def _parse_ids(multi_key: str, single_key: str):
                if multi_key in row_keys:
                    value = row[multi_key] or "[]"
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return []
                if single_key in row_keys:
                    return [row[single_key]] if row[single_key] is not None else []
                return []

            payload = (
                _value("id", None),
                _value("map_id", 0),
                _value("name", ""),
                _value("x", 0.0),
                _value("y", 0.0),
                _value("color", "#4a90e2"),
                _value("type", "blue"),
                _value("size", 8.0),
                _value("description", ""),
                _value("properties", ""),
                json.dumps(_parse_ids("task_ids", "task_id"), ensure_ascii=False),
                json.dumps(_parse_ids("project_ids", "project_id"), ensure_ascii=False),
                json.dumps(_parse_ids("note_ids", "note_id"), ensure_ascii=False),
                json.dumps(_parse_ids("object_ids", "object_id"), ensure_ascii=False),
                json.dumps(_parse_ids("file_ids", "file_id"), ensure_ascii=False),
                json.dumps(_parse_ids("map_ids", "map_ref_id"), ensure_ascii=False),
                json.dumps(_parse_ids("marker_ids", "marker_ref_id"), ensure_ascii=False),
                _value("parent_path", ""),
                _value("image_path", ""),
                _value("created_at", now),
                _value("updated_at", now),
            )
            self._conn.execute(
                """
                INSERT INTO map_markers (
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )
        self._conn.execute("DROP TABLE map_markers_old;")

    def _priority_constraint_is_current(self, table: str) -> bool:
        row = self._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
            (table,),
        ).fetchone()
        if not row:
            return True
        return "Отложенная" in (row["sql"] or "")

    def _rebuild_tasks_table(self) -> None:
        self._conn.execute("ALTER TABLE tasks RENAME TO tasks_old;")
        self._conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                project_id INTEGER REFERENCES projects(id),
                parent_id INTEGER REFERENCES tasks(id),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.execute(
            """
            INSERT INTO tasks (
                id, title, description, day, time_text, priority, done, project_id, parent_id, created_at, updated_at
            )
            SELECT id, title, description, day, time_text, priority, done, project_id, parent_id, created_at, updated_at
            FROM tasks_old;
            """
        )
        self._conn.execute("DROP TABLE tasks_old;")

    def _rebuild_projects_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
                archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
            );
            """
        )

    def _ensure_priority_indexes(self) -> None:
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_day ON tasks(day);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_area ON projects(area);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(archived);")

    def _ensure_map_tiles_path_column(self) -> None:
        """Добавляет колонку tiles_path, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(maps);").fetchall()
        names = {row["name"] for row in columns}
        if "tiles_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE maps ADD COLUMN tiles_path TEXT NOT NULL DEFAULT '';")

    def _ensure_marker_attachment_columns(self) -> None:
        """Добавляет новые колонки для вложений маркера карты."""
        columns = self._conn.execute("PRAGMA table_info(map_markers);").fetchall()
        names = {row["name"] for row in columns}
        additions = {
            "task_ids": "ALTER TABLE map_markers ADD COLUMN task_ids TEXT NOT NULL DEFAULT '[]';",
            "project_ids": "ALTER TABLE map_markers ADD COLUMN project_ids TEXT NOT NULL DEFAULT '[]';",
            "note_ids": "ALTER TABLE map_markers ADD COLUMN note_ids TEXT NOT NULL DEFAULT '[]';",
            "object_ids": "ALTER TABLE map_markers ADD COLUMN object_ids TEXT NOT NULL DEFAULT '[]';",
            "file_ids": "ALTER TABLE map_markers ADD COLUMN file_ids TEXT NOT NULL DEFAULT '[]';",
            "map_ids": "ALTER TABLE map_markers ADD COLUMN map_ids TEXT NOT NULL DEFAULT '[]';",
            "marker_ids": "ALTER TABLE map_markers ADD COLUMN marker_ids TEXT NOT NULL DEFAULT '[]';",
        }
        legacy_columns = ("task_id", "project_id", "note_id", "object_id")
        for column, ddl in additions.items():
            if column not in names:
                with self._conn:
                    self._conn.execute(ddl)
        legacy_present = any(column in names for column in legacy_columns)
        if legacy_present:
            rows = self._conn.execute(
                """
                SELECT id, task_id, project_id, note_id, object_id
                FROM map_markers;
                """
            ).fetchall()
            with self._conn:
                for row in rows:
                    task_ids = [row["task_id"]] if row["task_id"] is not None else []
                    project_ids = [row["project_id"]] if row["project_id"] is not None else []
                    note_ids = [row["note_id"]] if row["note_id"] is not None else []
                    object_ids = [row["object_id"]] if row["object_id"] is not None else []
                    self._conn.execute(
                        """
                        UPDATE map_markers
                        SET task_ids = ?, project_ids = ?, note_ids = ?, object_ids = ?
                        WHERE id = ?;
                        """,
                        (
                            json.dumps(task_ids, ensure_ascii=False),
                            json.dumps(project_ids, ensure_ascii=False),
                            json.dumps(note_ids, ensure_ascii=False),
                            json.dumps(object_ids, ensure_ascii=False),
                            row["id"],
                        ),
                    )

    def _ensure_marker_image_column(self) -> None:
        """Добавляет колонку превью для маркеров, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(map_markers);").fetchall()
        names = {row["name"] for row in columns}
        if "image_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE map_markers ADD COLUMN image_path TEXT NOT NULL DEFAULT '';")

    def _ensure_marker_parent_path_column(self) -> None:
        """Добавляет колонку родительского каталога для маркеров, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(map_markers);").fetchall()
        names = {row["name"] for row in columns}
        if "parent_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE map_markers ADD COLUMN parent_path TEXT NOT NULL DEFAULT '';")

    def _seed_defaults(self) -> None:
        """Добавляет демонстрационные данные, если база пустая."""
        cur = self._conn.execute("SELECT COUNT(*) FROM tasks;")
        if cur.fetchone()[0] == 0:
            self._seed_tasks()

        cur = self._conn.execute("SELECT COUNT(*) FROM projects;")
        if cur.fetchone()[0] == 0:
            self._seed_projects()

        cur = self._conn.execute("SELECT COUNT(*) FROM maps;")
        if cur.fetchone()[0] == 0:
            self._seed_maps()

        cur = self._conn.execute("SELECT COUNT(*) FROM notes;")
        if cur.fetchone()[0] == 0:
            self._seed_notes()

        cur = self._conn.execute("SELECT COUNT(*) FROM objects;")
        if cur.fetchone()[0] == 0:
            self._seed_objects()

    def _seed_tasks(self) -> None:
        today = date.today()
        days = [today - timedelta(days=1), today, today + timedelta(days=1), today + timedelta(days=2)]
        examples = [
            (days[0], "13:00", "BorderDev", "High", 0),
            (days[0], "14:00", "Wiki → Picture", "High", 0),
            (days[1], "15:00", "Подумать над DragAndDrop для списка задач в режиме план", "Medium", 0),
            (days[1], "16:00", "Билеты ПДД", "Low", 0),
            (days[1], "17:00", "Просмотреть FAV", "Medium", 0),
            (days[1], "19:00", "Просмотреть записи во всех каналах Избранного", "Medium", 0),
            (days[2], "20:00", "SimCity Societies → KitBash → Здания усадьбы. Здание школы. Многоэтажка…", "High", 0),
            (days[3], "22:00", "Stygian · Reign of the Old Ones", "High", 0),
            (days[3], "23:00", "The Council", "High", 1),
        ]
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            for day, time_text, title, priority, done in examples:
                self._conn.execute(
                    """
                    INSERT INTO tasks (title, day, time_text, priority, done, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (title, day.isoformat(), time_text, priority, done, now, now),
                )

    def _seed_projects(self) -> None:
        examples = [
            ("SPACE", "MindNavigator v2", "06.01.2026", "High", 0),
            ("SPACE", "Синхронизация FastAPI + S3", "05.01.2026", "Medium", 0),
            ("TACMap", "Редактор слоёв / маркеров", "03.01.2026", "High", 0),
            ("MakerTask", "ProjectsWorkspace UI (прототип)", "02.10.2025", "Medium", 0),
            ("MakerTask", "Drag&Drop планировщика", "01.10.2025", "High", 1),
            ("Wiki", "Cities: Skylines → DokuWiki", "22.07.2025", "Low", 0),
            ("Misc", "Сбор референсов / moodboard", "01.01.2026", "Low", 0),
        ]
        with self._conn:
            for area, title, updated, priority, archived in examples:
                self._conn.execute(
                    """
                    INSERT INTO projects (area, title, updated, priority, archived)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (area, title, parse_project_date(updated).isoformat(), priority, archived),
                )

    def _seed_maps(self) -> None:
        examples = [
            ("Northern Ridge", "Точки обзора и маршруты патрулей.", "MindNavigator v2", "", 18, 24),
            ("Sector 12", "Зоны контроля и минные поля.", "TACMap", "", 32, 32),
            ("Green Hills", "Артиллерийские позиции и наблюдатели.", "Wiki", "", 12, 20),
        ]
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            for title, description, project, tiles_path, tiles_h, tiles_w in examples:
                self._conn.execute(
                    """
                    INSERT INTO maps (title, description, project, tiles_path, tiles_h, tiles_w, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (title, description, project, tiles_path, tiles_h, tiles_w, now, now),
                )

    def _seed_notes(self) -> None:
        now = datetime.utcnow()
        examples = [
            (
                "Онбординг продукта",
                "Ключевые шаги запуска, список рисков и список блокеров для первой версии...",
                ["product", "launch", "priority"],
                now - timedelta(hours=2),
                "MindNavigator",
                True,
                True,
                False,
            ),
            (
                "Исследование пользователей",
                "Сводка интервью: болевые точки, привычки ведения заметок, ожидания от поиска...",
                ["research", "ux"],
                now - timedelta(days=1, hours=3),
                "Discovery",
                False,
                False,
                False,
            ),
            (
                "Архитектура синхронизации",
                "Контуры API: FastAPI, SQLite, оффлайн-очереди, форматы событий...",
                ["backend", "sync"],
                now - timedelta(days=2),
                "Platform",
                False,
                False,
                True,
            ),
            (
                "UI-референсы",
                "Obsidian + Notion + IDE: контраст, карточки, минимализм, быстрые экшены...",
                ["ui", "references"],
                now - timedelta(days=3, hours=5),
                "Design",
                True,
                False,
                False,
            ),
            (
                "Чеклист релиза",
                "Checklist: тесты, документация, скриншоты, релизные заметки...",
                ["release", "ops"],
                now - timedelta(days=4),
                "Delivery",
                False,
                True,
                False,
            ),
        ]
        with self._conn:
            for title, preview, tags, updated, project, favorite, attachment, locked in examples:
                created_at = updated.isoformat(timespec="seconds")
                self._conn.execute(
                    """
                    INSERT INTO notes (title, preview, tags, project, favorite, attachment, locked, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        title,
                        preview,
                        json.dumps(tags),
                        project,
                        int(favorite),
                        int(attachment),
                        int(locked),
                        created_at,
                        updated.isoformat(timespec="seconds"),
                    ),
                )

    def fetch_tasks(self) -> List[TaskData]:
        """Возвращает список всех задач."""
        rows = self._conn.execute(
            """
            SELECT
                t.id,
                t.day,
                t.time_text,
                t.title,
                t.description,
                t.priority,
                t.done,
                t.project_id,
                COALESCE(p.title, '') AS project_title,
                COALESCE(p.area, '') AS project_area,
                t.parent_id
            FROM tasks t
            LEFT JOIN projects p ON p.id = t.project_id;
            """
        ).fetchall()
        tasks = []
        for row in rows:
            tasks.append(
                TaskData(
                    id=row["id"],
                    day=date.fromisoformat(row["day"]),
                    time_text=row["time_text"],
                    title=row["title"],
                    description=row["description"] or "",
                    priority=row["priority"],
                    done=bool(row["done"]),
                    project_id=row["project_id"],
                    project_title=row["project_title"] or "",
                    project_area=row["project_area"] or "",
                    parent_id=row["parent_id"],
                )
            )
        return tasks

    def _seed_objects(self) -> None:
        now = datetime.utcnow().isoformat(timespec="seconds")
        examples = [
            (
                "Центральный офис",
                "Город / Административные",
                "Бизнес-центр",
                "В эксплуатации",
                "Главный офис с зонами приема и переговорными.",
            ),
            (
                "Складская зона Север",
                "Логистика",
                "Склад",
                "Проектирование",
                "Площадка под распределительный центр и технологические блоки.",
            ),
        ]
        with self._conn:
            for title, catalog, object_type, status, description in examples:
                self._conn.execute(
                    """
                    INSERT INTO objects (title, catalog, object_type, status, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (title, catalog, object_type, status, description, now, now),
                )

    def create_task(
        self,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> TaskData:
        """Создает задачу в базе данных."""
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        if not isinstance(day, date):
            raise ValueError("Дата задачи некорректна.")

        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO tasks (title, description, day, time_text, priority, done, project_id, parent_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?);
                """,
                (title, description, day.isoformat(), time_text, priority, project_id, parent_id, now, now),
            )
        project_title = ""
        project_area = ""
        if project_id is not None:
            row = self._conn.execute(
                "SELECT area, title FROM projects WHERE id = ?;",
                (project_id,),
            ).fetchone()
            if row:
                project_area = row["area"]
                project_title = row["title"]
        return TaskData(
            cur.lastrowid,
            day,
            time_text,
            title,
            description,
            priority,
            False,
            project_id,
            project_title,
            project_area,
            parent_id,
        )

    def update_task(
        self,
        task_id: int,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        done: bool,
        project_id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> TaskData:
        """Обновляет задачу."""
        prev_row = self._conn.execute(
            "SELECT priority FROM tasks WHERE id = ?;",
            (task_id,),
        ).fetchone()
        prev_priority = prev_row["priority"] if prev_row else priority
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        if not isinstance(day, date):
            raise ValueError("Дата задачи некорректна.")

        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, day = ?, time_text = ?, priority = ?, done = ?, project_id = ?, parent_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, description, day.isoformat(), time_text, priority, int(done), project_id, parent_id, now, task_id),
            )
            cascade_priority = None
            if priority == "Отложенная" and prev_priority != "Отложенная":
                cascade_priority = priority
            elif prev_priority == "Отложенная" and priority != "Отложенная":
                cascade_priority = priority
            if cascade_priority is not None:
                self._conn.execute(
                    """
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id FROM tasks WHERE parent_id = ?
                        UNION ALL
                        SELECT t.id FROM tasks t
                        JOIN descendants d ON t.parent_id = d.id
                    )
                    UPDATE tasks
                    SET priority = ?, updated_at = ?
                    WHERE id IN (SELECT id FROM descendants);
                    """,
                    (task_id, cascade_priority, now),
                )
        project_title = ""
        project_area = ""
        if project_id is not None:
            row = self._conn.execute(
                "SELECT area, title FROM projects WHERE id = ?;",
                (project_id,),
            ).fetchone()
            if row:
                project_area = row["area"]
                project_title = row["title"]
        return TaskData(
            task_id,
            day,
            time_text,
            title,
            description,
            priority,
            bool(done),
            project_id,
            project_title,
            project_area,
            parent_id,
        )

    def set_task_done(self, task_id: int, done: bool) -> None:
        """Обновляет статус выполнения задачи."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                "UPDATE tasks SET done = ?, updated_at = ? WHERE id = ?;",
                (int(done), now, task_id),
            )

    def delete_task(self, task_id: int) -> None:
        """Удаляет задачу по id."""
        with self._conn:
            self._conn.execute(
                """
                WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM tasks WHERE id = ?
                    UNION ALL
                    SELECT t.id FROM tasks t
                    JOIN descendants d ON t.parent_id = d.id
                )
                DELETE FROM tasks WHERE id IN (SELECT id FROM descendants);
                """,
                (task_id,),
            )

    def fetch_task_attachments(self, task_id: int) -> List[TaskAttachmentData]:
        """Возвращает список вложений задачи."""
        rows = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at
            FROM task_attachments
            WHERE task_id = ?
            ORDER BY created_at ASC;
            """,
            (task_id,),
        ).fetchall()
        attachments = []
        for row in rows:
            attachments.append(
                TaskAttachmentData(
                    id=row["id"],
                    task_id=row["task_id"],
                    kind=row["kind"],
                    ref_id=row["ref_id"],
                    created_at=row["created_at"],
                )
            )
        return attachments

    def add_task_attachment(self, task_id: int, kind: str, ref_id: int) -> TaskAttachmentData:
        """Добавляет вложение к задаче."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO task_attachments (task_id, kind, ref_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (task_id, kind, ref_id, now),
            )
        row = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at
            FROM task_attachments
            WHERE task_id = ? AND kind = ? AND ref_id = ?;
            """,
            (task_id, kind, ref_id),
        ).fetchone()
        return TaskAttachmentData(
            id=row["id"],
            task_id=row["task_id"],
            kind=row["kind"],
            ref_id=row["ref_id"],
            created_at=row["created_at"],
        )

    def delete_task_attachment(self, attachment_id: int) -> None:
        """Удаляет вложение задачи."""
        with self._conn:
            self._conn.execute("DELETE FROM task_attachments WHERE id = ?;", (attachment_id,))

    def fetch_projects(self) -> List[ProjectData]:
        """Возвращает список проектов."""
        rows = self._conn.execute(
            "SELECT id, area, title, updated, priority, archived FROM projects;"
        ).fetchall()
        projects = []
        for row in rows:
            projects.append(
                ProjectData(
                    id=row["id"],
                    area=row["area"],
                    title=row["title"],
                    updated=date.fromisoformat(row["updated"]),
                    priority=row["priority"],
                    archived=bool(row["archived"]),
                )
            )
        return projects

    def create_project(self, area: str, title: str, updated: date, priority: str, archived: bool = False) -> ProjectData:
        """Создает проект в базе данных."""
        area = validate_area(area)
        title = validate_title(title, field_name="Название проекта")
        priority = normalize_priority(priority)
        if not isinstance(updated, date):
            raise ValueError("Дата проекта некорректна.")

        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO projects (area, title, updated, priority, archived)
                VALUES (?, ?, ?, ?, ?);
                """,
                (area, title, updated.isoformat(), priority, int(archived)),
            )
        return ProjectData(cur.lastrowid, area, title, updated, priority, bool(archived))

    def update_project(
        self,
        project_id: int,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
    ) -> ProjectData:
        """Обновляет данные проекта."""
        area = validate_area(area)
        title = validate_title(title, field_name="Название проекта")
        priority = normalize_priority(priority)
        if not isinstance(updated, date):
            raise ValueError("Дата проекта некорректна.")

        with self._conn:
            self._conn.execute(
                """
                UPDATE projects
                SET area = ?, title = ?, updated = ?, priority = ?, archived = ?
                WHERE id = ?;
                """,
                (area, title, updated.isoformat(), priority, int(archived), project_id),
            )
        return ProjectData(project_id, area, title, updated, priority, bool(archived))

    def delete_project(self, project_id: int) -> None:
        """Удаляет проект по id."""
        with self._conn:
            self._conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))

    def set_project_archived(self, project_id: int, archived: bool) -> None:
        """Обновляет статус архивирования проекта."""
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET archived = ? WHERE id = ?;",
                (int(archived), project_id),
            )

    def set_projects_archived_for_area(self, area: str, archived: bool) -> None:
        """Архивирует все проекты в области."""
        area = validate_area(area)
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET archived = ? WHERE area = ?;",
                (int(archived), area),
            )

    def delete_projects_by_area(self, area: str) -> None:
        """Удаляет все проекты в области."""
        area = validate_area(area)
        with self._conn:
            self._conn.execute("DELETE FROM projects WHERE area = ?;", (area,))

    def rename_project_area(self, area: str, new_area: str) -> None:
        """Переименовывает область проектов."""
        area = validate_area(area)
        new_area = validate_area(new_area)
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET area = ? WHERE area = ?;",
                (new_area, area),
            )

    def project_areas(self) -> List[str]:
        """Возвращает отсортированный список областей проекта."""
        rows = self._conn.execute("SELECT DISTINCT area FROM projects ORDER BY area;").fetchall()
        return [row["area"] for row in rows]

    def fetch_maps(self) -> List[MapData]:
        """Возвращает список карт."""
        rows = self._conn.execute(
            "SELECT id, title, description, project, tiles_path, tiles_h, tiles_w FROM maps;"
        ).fetchall()
        maps = []
        for row in rows:
            maps.append(
                MapData(
                    id=row["id"],
                    title=row["title"],
                    description=row["description"] or "",
                    project=row["project"] or "",
                    tiles_path=row["tiles_path"] or "",
                    tiles_h=row["tiles_h"],
                    tiles_w=row["tiles_w"],
                )
            )
        return maps

    def create_map(
        self,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> MapData:
        """Создает карту."""
        title = validate_title(title, field_name="Название карты")
        description = (description or "").strip()
        project = (project or "").strip()
        tiles_path = (tiles_path or "").strip()
        if tiles_h <= 0 or tiles_w <= 0:
            raise ValueError("Размер сетки должен быть больше нуля.")

        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO maps (title, description, project, tiles_path, tiles_h, tiles_w, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (title, description, project, tiles_path, tiles_h, tiles_w, now, now),
            )
        return MapData(cur.lastrowid, title, description, project, tiles_path, tiles_h, tiles_w)

    def update_map(
        self,
        map_id: int,
        title: str,
        description: str,
        project: str,
        tiles_path: str,
        tiles_h: int,
        tiles_w: int,
    ) -> MapData:
        """Обновляет свойства карты."""
        title = validate_title(title, field_name="Название карты")
        description = (description or "").strip()
        project = (project or "").strip()
        tiles_path = (tiles_path or "").strip()
        if tiles_h <= 0 or tiles_w <= 0:
            raise ValueError("Размер сетки должен быть больше нуля.")

        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE maps
                SET title = ?, description = ?, project = ?, tiles_path = ?, tiles_h = ?, tiles_w = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, description, project, tiles_path, tiles_h, tiles_w, now, map_id),
            )
        return MapData(map_id, title, description, project, tiles_path, tiles_h, tiles_w)

    def fetch_map_markers(self, map_id: Optional[int] = None) -> List[MapMarkerData]:
        """Возвращает список меток карты."""
        if map_id is None:
            rows = self._conn.execute(
                """
                SELECT
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                FROM map_markers;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                FROM map_markers
                WHERE map_id = ?;
                """,
                (map_id,),
            ).fetchall()
        markers = []
        for row in rows:
            markers.append(
                MapMarkerData(
                    id=row["id"],
                    map_id=row["map_id"],
                    name=row["name"],
                    x=row["x"],
                    y=row["y"],
                    color=row["color"],
                    type=row["type"],
                    size=row["size"],
                    description=row["description"] or "",
                    properties=row["properties"] or "",
                    task_ids=json.loads(row["task_ids"] or "[]"),
                    project_ids=json.loads(row["project_ids"] or "[]"),
                    note_ids=json.loads(row["note_ids"] or "[]"),
                    object_ids=json.loads(row["object_ids"] or "[]"),
                    file_ids=json.loads(row["file_ids"] or "[]"),
                    map_ids=json.loads(row["map_ids"] or "[]"),
                    marker_ids=json.loads(row["marker_ids"] or "[]"),
                    parent_path=row["parent_path"] or "",
                    image_path=row["image_path"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return markers

    def upsert_map_marker(
        self,
        marker_id: int,
        map_id: int,
        name: str,
        x: float,
        y: float,
        color: str,
        marker_type: str,
        size: float,
        description: str = "",
        properties: str = "",
        task_ids: Optional[List[int]] = None,
        project_ids: Optional[List[int]] = None,
        note_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
        file_ids: Optional[List[int]] = None,
        map_ids: Optional[List[int]] = None,
        marker_ids: Optional[List[int]] = None,
        parent_path: str = "",
        image_path: str = "",
    ) -> MapMarkerData:
        """Создает или обновляет метку карты."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        task_ids = task_ids or []
        project_ids = project_ids or []
        note_ids = note_ids or []
        object_ids = object_ids or []
        file_ids = file_ids or []
        map_ids = map_ids or []
        marker_ids = marker_ids or []
        parent_path = (parent_path or "").strip()
        image_path = (image_path or "").strip()
        payload = (
            marker_id,
            map_id,
            name,
            x,
            y,
            color,
            marker_type,
            size,
            description,
            properties,
            json.dumps(task_ids, ensure_ascii=False),
            json.dumps(project_ids, ensure_ascii=False),
            json.dumps(note_ids, ensure_ascii=False),
            json.dumps(object_ids, ensure_ascii=False),
            json.dumps(file_ids, ensure_ascii=False),
            json.dumps(map_ids, ensure_ascii=False),
            json.dumps(marker_ids, ensure_ascii=False),
            parent_path,
            image_path,
            now,
            now,
        )
        if self._task_project_fk_needs_repair():
            self._repair_task_project_fk()
        self._ensure_map_marker_foreign_keys()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO map_markers (
                    id,
                    map_id,
                    name,
                    x,
                    y,
                    color,
                    type,
                    size,
                    description,
                    properties,
                    task_ids,
                    project_ids,
                    note_ids,
                    object_ids,
                    file_ids,
                    map_ids,
                    marker_ids,
                    parent_path,
                    image_path,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    map_id = excluded.map_id,
                    name = excluded.name,
                    x = excluded.x,
                    y = excluded.y,
                    color = excluded.color,
                    type = excluded.type,
                    size = excluded.size,
                    description = excluded.description,
                    properties = excluded.properties,
                    task_ids = excluded.task_ids,
                    project_ids = excluded.project_ids,
                    note_ids = excluded.note_ids,
                    object_ids = excluded.object_ids,
                    file_ids = excluded.file_ids,
                    map_ids = excluded.map_ids,
                    marker_ids = excluded.marker_ids,
                    parent_path = excluded.parent_path,
                    image_path = excluded.image_path,
                    created_at = map_markers.created_at,
                    updated_at = excluded.updated_at;
                """,
                payload,
            )
        row = self._conn.execute(
            """
            SELECT
                id,
                map_id,
                name,
                x,
                y,
                color,
                type,
                size,
                description,
                properties,
                task_ids,
                project_ids,
                note_ids,
                object_ids,
                file_ids,
                map_ids,
                marker_ids,
                parent_path,
                image_path,
                created_at,
                updated_at
            FROM map_markers
            WHERE id = ?;
            """,
            (marker_id,),
        ).fetchone()
        return MapMarkerData(
            id=row["id"],
            map_id=row["map_id"],
            name=row["name"],
            x=row["x"],
            y=row["y"],
            color=row["color"],
            type=row["type"],
            size=row["size"],
            description=row["description"] or "",
            properties=row["properties"] or "",
            task_ids=json.loads(row["task_ids"] or "[]"),
            project_ids=json.loads(row["project_ids"] or "[]"),
            note_ids=json.loads(row["note_ids"] or "[]"),
            object_ids=json.loads(row["object_ids"] or "[]"),
            file_ids=json.loads(row["file_ids"] or "[]"),
            map_ids=json.loads(row["map_ids"] or "[]"),
            marker_ids=json.loads(row["marker_ids"] or "[]"),
            parent_path=row["parent_path"] or "",
            image_path=row["image_path"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete_map_marker(self, marker_id: int) -> None:
        """Удаляет метку карты."""
        with self._conn:
            self._conn.execute("DELETE FROM map_markers WHERE id = ?;", (marker_id,))

    def fetch_notes(self) -> List[NoteData]:
        """Возвращает список всех заметок."""
        rows = self._conn.execute(
            """
            SELECT
                id,
                title,
                preview,
                tags,
                project,
                favorite,
                attachment,
                locked,
                updated_at
            FROM notes
            ORDER BY updated_at DESC;
            """
        ).fetchall()
        notes = []
        for row in rows:
            tags = json.loads(row["tags"] or "[]")
            notes.append(
                NoteData(
                    id=row["id"],
                    title=row["title"],
                    preview=row["preview"] or "",
                    tags=tags if isinstance(tags, list) else [],
                    updated=datetime.fromisoformat(row["updated_at"]),
                    project=row["project"] or "",
                    favorite=bool(row["favorite"]),
                    attachment=bool(row["attachment"]),
                    locked=bool(row["locked"]),
                )
            )
        return notes

    def create_note(
        self,
        title: str,
        preview: str,
        tags: List[str],
        project: str,
        favorite: bool = False,
        attachment: bool = False,
        locked: bool = False,
    ) -> NoteData:
        """Создает заметку в базе данных."""
        title = validate_title(title, field_name="Название заметки")
        preview = (preview or "").strip()
        project = (project or "").strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO notes (title, preview, tags, project, favorite, attachment, locked, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    preview,
                    json.dumps(tags),
                    project,
                    int(bool(favorite)),
                    int(bool(attachment)),
                    int(bool(locked)),
                    now,
                    now,
                ),
            )
        return NoteData(
            id=cur.lastrowid,
            title=title,
            preview=preview,
            tags=tags,
            updated=datetime.fromisoformat(now),
            project=project,
            favorite=bool(favorite),
            attachment=bool(attachment),
            locked=bool(locked),
        )

    def update_note(
        self,
        note_id: int,
        title: str,
        preview: str,
        tags: List[str],
    ) -> NoteData:
        """Обновляет данные заметки."""
        title = validate_title(title, field_name="Название заметки")
        preview = (preview or "").strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE notes
                SET title = ?, preview = ?, tags = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, preview, json.dumps(tags), now, note_id),
            )
        row = self._conn.execute(
            """
            SELECT id, project, favorite, attachment, locked
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        return NoteData(
            id=note_id,
            title=title,
            preview=preview,
            tags=tags,
            updated=datetime.fromisoformat(now),
            project=row["project"] if row else "",
            favorite=bool(row["favorite"]) if row else False,
            attachment=bool(row["attachment"]) if row else False,
            locked=bool(row["locked"]) if row else False,
        )

    def _fetch_project_title(self, project_id: Optional[int]) -> str:
        if project_id is None:
            return ""
        row = self._conn.execute(
            "SELECT title FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        return row["title"] if row else ""

    def fetch_ideas(
        self,
        project_id: Optional[int] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        idea_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        archived: bool = False,
    ) -> List[IdeaData]:
        """Возвращает список идей с учетом фильтров."""
        conditions = []
        params: list[object] = []
        if project_id is not None:
            conditions.append("ideas.project_id = ?")
            params.append(project_id)
        if search:
            like = f"%{search.strip().lower()}%"
            conditions.append("(lower(ideas.title) LIKE ? OR lower(ideas.body_md) LIKE ?)")
            params.extend([like, like])
        if status:
            conditions.append("ideas.status = ?")
            params.append(status)
        if idea_type:
            conditions.append("ideas.type = ?")
            params.append(idea_type)
        if archived:
            conditions.append("ideas.archived_at IS NOT NULL")
        else:
            conditions.append("ideas.archived_at IS NULL")
        if tags:
            tag_list = [tag.strip() for tag in tags if tag.strip()]
            if tag_list:
                placeholders = ",".join("?" for _ in tag_list)
                conditions.append(
                    "EXISTS (SELECT 1 FROM idea_tags WHERE idea_tags.idea_id = ideas.id "
                    f"AND idea_tags.tag_text IN ({placeholders}))"
                )
                params.extend(tag_list)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self._conn.execute(
            f"""
            SELECT
                ideas.id,
                ideas.project_id,
                ideas.title,
                ideas.summary,
                ideas.body_md,
                ideas.type,
                ideas.status,
                ideas.value_score,
                ideas.effort_score,
                ideas.source,
                ideas.created_at,
                ideas.updated_at,
                ideas.archived_at,
                projects.title AS project_title
            FROM ideas
            LEFT JOIN projects ON projects.id = ideas.project_id
            {where}
            ORDER BY ideas.updated_at DESC;
            """,
            params,
        ).fetchall()
        ideas: List[IdeaData] = []
        for row in rows:
            ideas.append(
                IdeaData(
                    id=row["id"],
                    project_id=row["project_id"],
                    title=row["title"] or "",
                    summary=row["summary"] or "",
                    body_md=row["body_md"] or "",
                    type=row["type"],
                    status=row["status"],
                    value_score=row["value_score"],
                    effort_score=row["effort_score"],
                    source=row["source"] or "",
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    archived_at=datetime.fromisoformat(row["archived_at"])
                    if row["archived_at"]
                    else None,
                    project_title=row["project_title"] or "",
                )
            )
        return ideas

    def get_idea(self, idea_id: int) -> Optional[IdeaData]:
        """Возвращает идею по ID."""
        row = self._conn.execute(
            """
            SELECT
                ideas.id,
                ideas.project_id,
                ideas.title,
                ideas.summary,
                ideas.body_md,
                ideas.type,
                ideas.status,
                ideas.value_score,
                ideas.effort_score,
                ideas.source,
                ideas.created_at,
                ideas.updated_at,
                ideas.archived_at,
                projects.title AS project_title
            FROM ideas
            LEFT JOIN projects ON projects.id = ideas.project_id
            WHERE ideas.id = ?;
            """,
            (idea_id,),
        ).fetchone()
        if row is None:
            return None
        return IdeaData(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"] or "",
            summary=row["summary"] or "",
            body_md=row["body_md"] or "",
            type=row["type"],
            status=row["status"],
            value_score=row["value_score"],
            effort_score=row["effort_score"],
            source=row["source"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            archived_at=datetime.fromisoformat(row["archived_at"]) if row["archived_at"] else None,
            project_title=row["project_title"] or "",
        )

    def create_idea(
        self,
        title: str,
        summary: str = "",
        body_md: str = "",
        idea_type: str = "other",
        status: str = "inbox",
        value_score: int = 3,
        effort_score: int = 3,
        project_id: Optional[int] = None,
        source: str = "",
    ) -> IdeaData:
        """Создает идею в базе данных."""
        title = (title or "").strip() or "Без названия"
        summary = (summary or "").strip()
        body_md = (body_md or "").strip()
        idea_type = (idea_type or "other").strip() or "other"
        status = (status or "inbox").strip() or "inbox"
        value_score = int(value_score or 3)
        effort_score = int(effort_score or 3)
        source = (source or "").strip()
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO ideas (
                    project_id, title, summary, body_md, type, status,
                    value_score, effort_score, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    title,
                    summary,
                    body_md,
                    idea_type,
                    status,
                    value_score,
                    effort_score,
                    source,
                    now,
                    now,
                ),
            )
        return IdeaData(
            id=cur.lastrowid,
            project_id=project_id,
            title=title,
            summary=summary,
            body_md=body_md,
            type=idea_type,
            status=status,
            value_score=value_score,
            effort_score=effort_score,
            source=source,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            archived_at=None,
            project_title=self._fetch_project_title(project_id),
        )

    def update_idea(
        self,
        idea_id: int,
        title: str,
        summary: str,
        body_md: str,
        idea_type: str,
        status: str,
        value_score: int,
        effort_score: int,
        project_id: Optional[int] = None,
        source: str = "",
    ) -> IdeaData:
        """Обновляет идею."""
        title = (title or "").strip() or "Без названия"
        summary = (summary or "").strip()
        body_md = (body_md or "").strip()
        idea_type = (idea_type or "other").strip() or "other"
        status = (status or "inbox").strip() or "inbox"
        value_score = int(value_score or 3)
        effort_score = int(effort_score or 3)
        source = (source or "").strip()
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE ideas
                SET project_id = ?, title = ?, summary = ?, body_md = ?, type = ?, status = ?,
                    value_score = ?, effort_score = ?, source = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    project_id,
                    title,
                    summary,
                    body_md,
                    idea_type,
                    status,
                    value_score,
                    effort_score,
                    source,
                    now,
                    idea_id,
                ),
            )
        meta_row = self._conn.execute(
            "SELECT created_at, archived_at FROM ideas WHERE id = ?;",
            (idea_id,),
        ).fetchone()
        created_at = (
            datetime.fromisoformat(meta_row["created_at"])
            if meta_row and meta_row["created_at"]
            else datetime.fromisoformat(now)
        )
        archived_at = (
            datetime.fromisoformat(meta_row["archived_at"])
            if meta_row and meta_row["archived_at"]
            else None
        )
        return IdeaData(
            id=idea_id,
            project_id=project_id,
            title=title,
            summary=summary,
            body_md=body_md,
            type=idea_type,
            status=status,
            value_score=value_score,
            effort_score=effort_score,
            source=source,
            created_at=created_at,
            updated_at=datetime.fromisoformat(now),
            archived_at=archived_at,
            project_title=self._fetch_project_title(project_id),
        )

    def set_idea_archived(self, idea_id: int, archived: bool) -> None:
        """Архивирует или восстанавливает идею."""
        archived_at = datetime.utcnow().isoformat(timespec="seconds") if archived else None
        with self._conn:
            self._conn.execute(
                "UPDATE ideas SET archived_at = ?, updated_at = ? WHERE id = ?;",
                (archived_at, datetime.utcnow().isoformat(timespec="seconds"), idea_id),
            )

    def delete_idea(self, idea_id: int) -> None:
        """Удаляет идею."""
        with self._conn:
            self._conn.execute("DELETE FROM ideas WHERE id = ?;", (idea_id,))

    def fetch_idea_relations(self, idea_id: int) -> List[IdeaRelationData]:
        """Возвращает список связей идеи."""
        rows = self._conn.execute(
            """
            SELECT id, idea_id, entity_type, entity_id, created_at
            FROM idea_relations
            WHERE idea_id = ?
            ORDER BY created_at DESC;
            """,
            (idea_id,),
        ).fetchall()
        return [
            IdeaRelationData(
                id=row["id"],
                idea_id=row["idea_id"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def add_idea_relation(self, idea_id: int, entity_type: str, entity_id: int) -> None:
        """Создает связь идеи с сущностью."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO idea_relations (idea_id, entity_type, entity_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (idea_id, entity_type, entity_id, now),
            )

    def toggle_note_favorite(self, note_id: int) -> NoteData:
        """Переключает избранное у заметки."""
        row = self._conn.execute(
            """
            SELECT title, preview, tags, project, favorite, attachment, locked
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        if not row:
            raise ValueError("Заметка не найдена.")
        favorite = not bool(row["favorite"])
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE notes
                SET favorite = ?, updated_at = ?
                WHERE id = ?;
                """,
                (int(favorite), now, note_id),
            )
        tags = json.loads(row["tags"] or "[]")
        return NoteData(
            id=note_id,
            title=row["title"],
            preview=row["preview"] or "",
            tags=tags if isinstance(tags, list) else [],
            updated=datetime.fromisoformat(now),
            project=row["project"] or "",
            favorite=favorite,
            attachment=bool(row["attachment"]),
            locked=bool(row["locked"]),
        )

    def delete_note(self, note_id: int) -> None:
        """Удаляет заметку."""
        with self._conn:
            self._conn.execute("DELETE FROM notes WHERE id = ?;", (note_id,))

    def fetch_objects(self) -> List[ObjectData]:
        """Возвращает список архитектурных объектов."""
        rows = self._conn.execute(
            """
            SELECT id, title, catalog, object_type, status, description, created_at, updated_at
            FROM objects
            ORDER BY updated_at DESC;
            """
        ).fetchall()
        return [
            ObjectData(
                row["id"],
                row["title"],
                row["catalog"] or "",
                row["object_type"] or "",
                row["status"] or "",
                row["description"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def create_object(
        self,
        title: str,
        catalog: str,
        object_type: str,
        status: str,
        description: str,
    ) -> ObjectData:
        """Создает архитектурный объект."""
        title = validate_title(title, field_name="Название объекта")
        catalog = (catalog or "").strip()
        object_type = (object_type or "").strip()
        status = (status or "").strip()
        description = (description or "").strip()
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO objects (title, catalog, object_type, status, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (title, catalog, object_type, status, description, now, now),
            )
        return ObjectData(cur.lastrowid, title, catalog, object_type, status, description, now, now)

    def update_object(
        self,
        object_id: int,
        title: str,
        catalog: str,
        object_type: str,
        status: str,
        description: str,
    ) -> ObjectData:
        """Обновляет архитектурный объект."""
        title = validate_title(title, field_name="Название объекта")
        catalog = (catalog or "").strip()
        object_type = (object_type or "").strip()
        status = (status or "").strip()
        description = (description or "").strip()
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE objects
                SET title = ?, catalog = ?, object_type = ?, status = ?, description = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, catalog, object_type, status, description, now, object_id),
            )
        row = self._conn.execute(
            """
            SELECT created_at
            FROM objects
            WHERE id = ?;
            """,
            (object_id,),
        ).fetchone()
        created_at = row["created_at"] if row else now
        return ObjectData(object_id, title, catalog, object_type, status, description, created_at, now)

    def delete_object(self, object_id: int) -> None:
        """Удаляет архитектурный объект."""
        with self._conn:
            self._conn.execute("DELETE FROM objects WHERE id = ?;", (object_id,))

    def create_object_from_folder_path(self, folder_path: str) -> ObjectData:
        """Создает объект на основе пути к папке."""
        path = (folder_path or "").strip().strip("/")
        if not path:
            raise ValueError("Путь к папке не должен быть пустым.")
        parts = [part for part in path.split("/") if part]
        title = parts[-1] if parts else "Новый объект"
        catalog = " / ".join(parts[:-1])
        description = f"Объект создан из папки: {path}"
        return self.create_object(title, catalog, "", "", description)

    def fetch_object_images(self, object_id: int) -> List[ObjectImageData]:
        """Возвращает список изображений объекта."""
        rows = self._conn.execute(
            """
            SELECT id, object_id, rel_path, description, created_at, updated_at
            FROM object_images
            WHERE object_id = ?
            ORDER BY created_at ASC;
            """,
            (object_id,),
        ).fetchall()
        return [
            ObjectImageData(
                row["id"],
                row["object_id"],
                row["rel_path"],
                row["description"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def add_object_image(self, object_id: int, rel_path: str, description: str = "") -> ObjectImageData:
        """Добавляет изображение к объекту."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("Путь к изображению не должен быть пустым.")
        description = (description or "").strip()
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO object_images (object_id, rel_path, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (object_id, rel_path, description, now, now),
            )
        row = self._conn.execute(
            """
            SELECT id, object_id, rel_path, description, created_at, updated_at
            FROM object_images
            WHERE object_id = ? AND rel_path = ?;
            """,
            (object_id, rel_path),
        ).fetchone()
        return ObjectImageData(
            row["id"],
            row["object_id"],
            row["rel_path"],
            row["description"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def update_object_image(self, image_id: int, description: str) -> ObjectImageData:
        """Обновляет описание изображения объекта."""
        description = (description or "").strip()
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE object_images
                SET description = ?, updated_at = ?
                WHERE id = ?;
                """,
                (description, now, image_id),
            )
        row = self._conn.execute(
            """
            SELECT id, object_id, rel_path, description, created_at, updated_at
            FROM object_images
            WHERE id = ?;
            """,
            (image_id,),
        ).fetchone()
        return ObjectImageData(
            row["id"],
            row["object_id"],
            row["rel_path"],
            row["description"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def delete_object_image(self, image_id: int) -> None:
        """Удаляет изображение объекта."""
        with self._conn:
            self._conn.execute("DELETE FROM object_images WHERE id = ?;", (image_id,))

    def get_setting(self, key: str, default: str = "") -> str:
        """Возвращает значение настройки."""
        key = (key or "").strip()
        if not key:
            raise ValueError("Ключ настройки не должен быть пустым.")
        cur = self._conn.execute("SELECT value FROM settings WHERE key = ?;", (key,))
        row = cur.fetchone()
        if not row:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        """Сохраняет значение настройки."""
        key = (key or "").strip()
        if not key:
            raise ValueError("Ключ настройки не должен быть пустым.")
        value = (value or "").strip()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """,
                (key, value),
            )

    def upsert_cloud_file(
        self,
        *,
        rel_path: str,
        name: str,
        description: str,
        checksum: str,
        hash_value: str,
        size: int,
        is_image: bool,
        valid: bool,
    ) -> CloudFileData:
        """Создает или обновляет запись о файле облака."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("Путь файла не должен быть пустым.")
        name = (name or "").strip()
        checksum = (checksum or "").strip()
        if not name or not checksum:
            raise ValueError("Имя файла и контрольная сумма обязательны.")
        description = (description or "").strip()
        hash_value = (hash_value or "").strip()
        size = max(0, int(size))
        now = datetime.utcnow().isoformat(timespec="seconds")

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO cloud_files (rel_path, name, description, checksum, hash_value, size, is_image, valid, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rel_path) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    checksum = excluded.checksum,
                    hash_value = excluded.hash_value,
                    size = excluded.size,
                    is_image = excluded.is_image,
                    valid = excluded.valid,
                    updated_at = excluded.updated_at;
                """,
                (
                    rel_path,
                    name,
                    description,
                    checksum,
                    hash_value,
                    size,
                    int(bool(is_image)),
                    int(bool(valid)),
                    now,
                ),
            )
        row = self._conn.execute(
            """
            SELECT id, rel_path, name, description, checksum, hash_value, size, is_image, valid, updated_at
            FROM cloud_files
            WHERE rel_path = ?;
            """,
            (rel_path,),
        ).fetchone()
        return CloudFileData(
            row["id"],
            row["rel_path"],
            row["name"],
            row["description"],
            row["checksum"],
            row["hash_value"],
            row["size"],
            bool(row["is_image"]),
            bool(row["valid"]),
            row["updated_at"],
        )

    def fetch_cloud_files(self) -> List[CloudFileData]:
        """Возвращает список файлов облака."""
        rows = self._conn.execute(
            """
            SELECT id, rel_path, name, description, checksum, hash_value, size, is_image, valid, updated_at
            FROM cloud_files
            ORDER BY rel_path;
            """
        ).fetchall()
        return [
            CloudFileData(
                row["id"],
                row["rel_path"],
                row["name"],
                row["description"],
                row["checksum"],
                row["hash_value"],
                row["size"],
                bool(row["is_image"]),
                bool(row["valid"]),
                row["updated_at"],
            )
            for row in rows
        ]

    def remove_missing_cloud_files(self, rel_paths: Iterable[str]) -> None:
        """Удаляет записи о файлах, которых нет в облачном каталоге."""
        rel_paths = [path for path in rel_paths if path]
        with self._conn:
            if not rel_paths:
                self._conn.execute("DELETE FROM cloud_files;")
                return
            placeholders = ",".join("?" for _ in rel_paths)
            self._conn.execute(
                f"DELETE FROM cloud_files WHERE rel_path NOT IN ({placeholders});",
                rel_paths,
            )

    def reindex(self) -> None:
        """Переиндексирует таблицы базы данных."""
        with self._conn:
            self._conn.execute("REINDEX;")

    def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self._closed:
            return
        self._conn.close()
        self._closed = True


@lru_cache(maxsize=1)
def get_database() -> Database:
    """Возвращает singleton базы данных."""
    return Database()
