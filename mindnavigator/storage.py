from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

PRIORITIES = ("Low", "Medium", "High")
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
        raise ValueError("Приоритет должен быть Low, Medium или High.")
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
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
                    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                    project_id INTEGER REFERENCES projects(id),
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
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
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
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);")

        self._ensure_task_project_column()
        self._ensure_task_description_column()
        self._ensure_map_tiles_path_column()
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

    def _ensure_map_tiles_path_column(self) -> None:
        """Добавляет колонку tiles_path, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(maps);").fetchall()
        names = {row["name"] for row in columns}
        if "tiles_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE maps ADD COLUMN tiles_path TEXT NOT NULL DEFAULT '';")

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
                COALESCE(p.title, '') AS project_title
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
                )
            )
        return tasks

    def create_task(
        self,
        title: str,
        description: str,
        day: date,
        time_text: str,
        priority: str,
        project_id: Optional[int] = None,
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
                INSERT INTO tasks (title, description, day, time_text, priority, done, project_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?);
                """,
                (title, description, day.isoformat(), time_text, priority, project_id, now, now),
            )
        project_title = ""
        if project_id is not None:
            row = self._conn.execute(
                "SELECT title FROM projects WHERE id = ?;",
                (project_id,),
            ).fetchone()
            if row:
                project_title = row["title"]
        return TaskData(cur.lastrowid, day, time_text, title, description, priority, False, project_id, project_title)

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
    ) -> TaskData:
        """Обновляет задачу."""
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
                SET title = ?, description = ?, day = ?, time_text = ?, priority = ?, done = ?, project_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, description, day.isoformat(), time_text, priority, int(done), project_id, now, task_id),
            )
        project_title = ""
        if project_id is not None:
            row = self._conn.execute(
                "SELECT title FROM projects WHERE id = ?;",
                (project_id,),
            ).fetchone()
            if row:
                project_title = row["title"]
        return TaskData(task_id, day, time_text, title, description, priority, bool(done), project_id, project_title)

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
            self._conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))

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


@lru_cache(maxsize=1)
def get_database() -> Database:
    """Возвращает singleton базы данных."""
    return Database()
