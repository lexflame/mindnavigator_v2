"""Р Р°Р±РѕС‚Р° СЃ Р»РѕРєР°Р»СЊРЅРѕР№ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С… Рё РІР°Р»РёРґР°С‚РѕСЂР°РјРё.

Р’С…РѕРґРЅС‹Рµ РґР°РЅРЅС‹Рµ:
    РџР°СЂР°РјРµС‚СЂС‹ РјРѕРґРµР»РµР№, SQL-Р·Р°РїСЂРѕСЃС‹ Рё Р·РЅР°С‡РµРЅРёСЏ РїРѕР»РµР№ СЃСѓС‰РЅРѕСЃС‚РµР№.

Р’С‹С…РѕРґРЅС‹Рµ РґР°РЅРЅС‹Рµ:
    Р—Р°РїРёСЃРё Р±Р°Р·С‹ РґР°РЅРЅС‹С…, РїСЂРѕРІРµСЂРµРЅРЅС‹Рµ СЃС‚СЂРѕРєРё Рё РѕР±СЉРµРєС‚ РїРѕРґРєР»СЋС‡РµРЅРёСЏ.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Iterable, List, Mapping, Optional, Tuple

from .db_migrations import MigrationStep, apply_migrations

PRIORITIES = ("Low", "Medium", "High", "РћС‚Р»РѕР¶РµРЅРЅР°СЏ")
MAX_TITLE_LEN = 160
MAX_AREA_LEN = 80
COLLECTION_ENTITY_TYPES = ("building", "city", "film", "game", "character", "other")
APP_CONFIG_FILE = "app_config.json"
APP_CONFIG_DB_PATH_KEY = "db_path"


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
    recurrence_kind: str = ""
    recurrence_interval: int = 1
    completion_delay_minutes: int = 0
    gantt_estimate_minutes: int = 0
    gantt_forecasted: bool = False
    marker_color: str = ""
    marker_theme: str = ""


@dataclass(frozen=True)
class ProjectData:
    id: int
    area: str
    title: str
    updated: date
    priority: str
    archived: bool
    parent_project_id: Optional[int] = None
    default_task_priority: str = ""
    force_recurrence_kind: str = ""
    linked_map_id: Optional[int] = None
    linked_note_id: Optional[int] = None
    linked_object_id: Optional[int] = None
    sort_order: int = 0
    marker_color: str = ""
    marker_theme: str = ""


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
class MapOverlayData:
    id: int
    map_id: int
    kind: str
    points: List[Tuple[float, float]]
    color: str
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class TaskAttachmentData:
    id: int
    task_id: int
    kind: str
    ref_id: int
    created_at: str

    SUPPORTED_KINDS: ClassVar[tuple[str, ...]] = (
        "note",
        "object",
        "map",
        "marker",
        "file",
        "image",
        "idea",
    )

    @classmethod
    def normalize_kind(cls, kind: str) -> str:
        normalized = (kind or "").strip().lower()
        if normalized not in cls.SUPPORTED_KINDS:
            supported = ", ".join(cls.SUPPORTED_KINDS)
            raise ValueError(f"РќРµРїРѕРґРґРµСЂР¶РёРІР°РµРјС‹Р№ С‚РёРї РІР»РѕР¶РµРЅРёСЏ: {kind!r}. РћР¶РёРґР°РµС‚СЃСЏ: {supported}.")
        return normalized

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "TaskAttachmentData":
        return cls(
            id=int(row["id"]),
            task_id=int(row["task_id"]),
            kind=cls.normalize_kind(str(row["kind"])),
            ref_id=int(row["ref_id"]),
            created_at=str(row["created_at"]),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TaskAttachmentData":
        return cls(
            id=int(payload.get("id", 0)),
            task_id=int(payload["task_id"]),
            kind=cls.normalize_kind(str(payload["kind"])),
            ref_id=int(payload["ref_id"]),
            created_at=str(payload.get("created_at", "")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": int(self.id),
            "task_id": int(self.task_id),
            "kind": self.kind,
            "ref_id": int(self.ref_id),
            "created_at": self.created_at,
        }


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


@dataclass(frozen=True)
class CollectionItemData:
    id: int
    title: str
    category_id: Optional[int]
    entity_type: str
    topic: str
    image_url: str
    source_url: str
    description: str
    source_folder_path: str
    import_options_json: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CollectionCategoryData:
    id: int
    title: str
    parent_id: Optional[int]
    sort_index: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CollectionRelationData:
    id: int
    left_item_id: int
    right_item_id: int
    relation_kind: str
    created_at: str


@dataclass(frozen=True)
class CollectionEntryData:
    id: int
    collection_id: int
    source_path: str
    rel_path: str
    title: str
    ext: str
    mime: str
    size_bytes: int
    meta_json: str
    is_missing: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ShopCategoryData:
    id: int
    title: str
    parent_id: Optional[int]


@dataclass(frozen=True)
class ShopItemData:
    id: int
    title: str
    category_id: Optional[int]
    user_notes: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ShopSourceData:
    id: int
    item_id: int
    shop_code: str
    url: str
    sku: str
    currency: str
    price: Optional[float]
    in_stock: bool
    stock_text: str
    parsed_at: str
    raw_json: str


@dataclass(frozen=True)
class ShopPriceHistoryData:
    id: int
    source_id: int
    price: Optional[float]
    currency: str
    in_stock: bool
    captured_at: str


@dataclass(frozen=True)
class ShopItemPropertyData:
    id: int
    item_id: int
    name: str
    value: str
    unit: str
    normalized_key: str


@dataclass(frozen=True)
class ShopSourcePropertyData:
    id: int
    source_id: int
    name: str
    value: str
    unit: str
    normalized_key: str


@dataclass(frozen=True)
class WishlistData:
    id: int
    title: str
    notes: str


@dataclass(frozen=True)
class WishlistItemData:
    wishlist_id: int
    item_id: int
    qty: int
    priority: int
    target_price: Optional[float]
    chosen_source_id: Optional[int]


def _app_base_dir() -> Path:
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ Р±Р°Р·РѕРІСѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ РїСЂРёР»РѕР¶РµРЅРёСЏ РІ РїСЂРѕС„РёР»Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ."""
    base = Path.home() / ".mindnavigator"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _app_config_path() -> Path:
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСѓС‚СЊ Рє С„Р°Р№Р»Сѓ РІРЅРµС€РЅРµР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё РїСЂРёР»РѕР¶РµРЅРёСЏ."""
    return _app_base_dir() / APP_CONFIG_FILE


def _read_app_config() -> dict:
    """Р§РёС‚Р°РµС‚ JSON-РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ РїСЂРёР»РѕР¶РµРЅРёСЏ РёР· РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ РїСЂРѕС„РёР»СЏ."""
    config_path = _app_config_path()
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_app_config(config: dict) -> None:
    """РЎРѕС…СЂР°РЅСЏРµС‚ JSON-РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ РїСЂРёР»РѕР¶РµРЅРёСЏ РІ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёР№ РїСЂРѕС„РёР»СЊ."""
    config_path = _app_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get_configured_db_path() -> Optional[Path]:
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїРµСЂРµРѕРїСЂРµРґРµР»РµРЅРЅС‹Р№ РїСѓС‚СЊ Р‘Р” РёР· РІРЅРµС€РЅРµР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё."""
    config = _read_app_config()
    raw_path = str(config.get(APP_CONFIG_DB_PATH_KEY, "")).strip()
    if not raw_path:
        return None
    return Path(raw_path)


def set_configured_db_path(path: Optional[Path | str]) -> Optional[Path]:
    """РЎРѕС…СЂР°РЅСЏРµС‚ РїСѓС‚СЊ Р‘Р” РІРѕ РІРЅРµС€РЅРµР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё; None СЃР±СЂР°СЃС‹РІР°РµС‚ РЅР°СЃС‚СЂРѕР№РєСѓ."""
    config = _read_app_config()
    if path is None:
        config.pop(APP_CONFIG_DB_PATH_KEY, None)
        _write_app_config(config)
        return None
    normalized_path = Path(path)
    config[APP_CONFIG_DB_PATH_KEY] = str(normalized_path)
    _write_app_config(config)
    return normalized_path


def default_db_path() -> Path:
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСѓС‚СЊ Рє С„Р°Р№Р»Сѓ Р±Р°Р·С‹ РґР°РЅРЅС‹С… РїСЂРёР»РѕР¶РµРЅРёСЏ."""
    configured = get_configured_db_path()
    if configured is not None:
        configured.parent.mkdir(parents=True, exist_ok=True)
        return configured
    return _app_base_dir() / "mindnavigator.db"


def validate_title(title: str, field_name: str = "РќР°Р·РІР°РЅРёРµ") -> str:
    """РџСЂРѕРІРµСЂСЏРµС‚ Рё РЅРѕСЂРјР°Р»РёР·СѓРµС‚ РЅР°Р·РІР°РЅРёРµ."""
    title = (title or "").strip()
    if not title:
        raise ValueError(f"{field_name} РЅРµ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f"{field_name} СЃР»РёС€РєРѕРј РґР»РёРЅРЅРѕРµ (РґРѕ {MAX_TITLE_LEN} СЃРёРјРІРѕР»РѕРІ).")
    return title


def validate_area(area: str) -> str:
    """РџСЂРѕРІРµСЂСЏРµС‚ Рё РЅРѕСЂРјР°Р»РёР·СѓРµС‚ РѕР±Р»Р°СЃС‚СЊ РїСЂРѕРµРєС‚Р°."""
    area = (area or "").strip()
    if not area:
        raise ValueError("РћР±Р»Р°СЃС‚СЊ РїСЂРѕРµРєС‚Р° РЅРµ РґРѕР»Р¶РЅР° Р±С‹С‚СЊ РїСѓСЃС‚РѕР№.")
    if len(area) > MAX_AREA_LEN:
        raise ValueError(f"РћР±Р»Р°СЃС‚СЊ РїСЂРѕРµРєС‚Р° СЃР»РёС€РєРѕРј РґР»РёРЅРЅР°СЏ (РґРѕ {MAX_AREA_LEN} СЃРёРјРІРѕР»РѕРІ).")
    return area


def normalize_priority(priority: str) -> str:
    """РќРѕСЂРјР°Р»РёР·СѓРµС‚ Рё РїСЂРѕРІРµСЂСЏРµС‚ Р·РЅР°С‡РµРЅРёРµ РїСЂРёРѕСЂРёС‚РµС‚Р°."""
    priority = (priority or "").strip() or "Medium"
    if priority not in PRIORITIES:
        raise ValueError("РџСЂРёРѕСЂРёС‚РµС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ Low, Medium, High РёР»Рё РћС‚Р»РѕР¶РµРЅРЅР°СЏ.")
    return priority


def validate_time_text(time_text: str) -> str:
    """РџСЂРѕРІРµСЂСЏРµС‚ С„РѕСЂРјР°С‚ РІСЂРµРјРµРЅРё."""
    time_text = (time_text or "").strip()
    if not time_text:
        return ""
    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError as exc:
        raise ValueError("Р’СЂРµРјСЏ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РІ С„РѕСЂРјР°С‚Рµ HH:MM.") from exc
    return time_text


def parse_project_date(value: str) -> date:
    """РџР°СЂСЃРёС‚ РґР°С‚Сѓ РїСЂРѕРµРєС‚Р° РІ С„РѕСЂРјР°С‚Рµ dd.mm.yyyy."""
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError("Р”Р°С‚Р° РїСЂРѕРµРєС‚Р° РґРѕР»Р¶РЅР° Р±С‹С‚СЊ РІ С„РѕСЂРјР°С‚Рµ dd.mm.yyyy.") from exc


def format_project_date(value: date) -> str:
    """Р¤РѕСЂРјР°С‚РёСЂСѓРµС‚ РґР°С‚Сѓ РїСЂРѕРµРєС‚Р° РґР»СЏ РёРЅС‚РµСЂС„РµР№СЃР°."""
    return value.strftime("%d.%m.%Y")


class Database:
    """Р Р°Р±РѕС‚Р°РµС‚ СЃ Р»РѕРєР°Р»СЊРЅРѕР№ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С… РїСЂРёР»РѕР¶РµРЅРёСЏ."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else default_db_path()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._closed = False
        self._init_db()

    def _init_db(self) -> None:
        """РРЅРёС†РёР°Р»РёР·РёСЂСѓРµС‚ СЃС…РµРјСѓ Рё РїР°СЂР°РјРµС‚СЂС‹ SQLite."""
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
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'РћС‚Р»РѕР¶РµРЅРЅР°СЏ')),
                    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                    completion_delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK (completion_delay_minutes >= 0),
                    gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0 CHECK (gantt_estimate_minutes >= 0),
                    gantt_forecasted INTEGER NOT NULL DEFAULT 0 CHECK (gantt_forecasted IN (0, 1)),
                    project_id INTEGER REFERENCES projects(id),
                    parent_id INTEGER REFERENCES tasks(id),
                    recurrence_kind TEXT NOT NULL DEFAULT '',
                    recurrence_interval INTEGER NOT NULL DEFAULT 1 CHECK (recurrence_interval >= 1),
                    marker_color TEXT NOT NULL DEFAULT '',
                    marker_theme TEXT NOT NULL DEFAULT '',
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
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'РћС‚Р»РѕР¶РµРЅРЅР°СЏ')),
                    archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
                    parent_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    default_task_priority TEXT NOT NULL DEFAULT '',
                    force_recurrence_kind TEXT NOT NULL DEFAULT '',
                    linked_map_id INTEGER REFERENCES maps(id) ON DELETE SET NULL,
                    linked_note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
                    linked_object_id INTEGER REFERENCES objects(id) ON DELETE SET NULL,
                    marker_color TEXT NOT NULL DEFAULT '',
                    marker_theme TEXT NOT NULL DEFAULT ''
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
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS map_overlays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    map_id INTEGER NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL CHECK (kind IN ('region', 'path')),
                    points TEXT NOT NULL DEFAULT '[]',
                    color TEXT NOT NULL DEFAULT '#6cb5ff',
                    title TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category_id INTEGER REFERENCES collection_category(id) ON DELETE SET NULL,
                    entity_type TEXT NOT NULL CHECK (entity_type IN ('building', 'city', 'film', 'game', 'character', 'other')),
                    topic TEXT NOT NULL DEFAULT '',
                    image_url TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    source_folder_path TEXT NOT NULL DEFAULT '',
                    import_options_json TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_category (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    parent_id INTEGER REFERENCES collection_category(id) ON DELETE SET NULL,
                    sort_index INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(title, parent_id)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    left_item_id INTEGER NOT NULL REFERENCES collection_items(id) ON DELETE CASCADE,
                    right_item_id INTEGER NOT NULL REFERENCES collection_items(id) ON DELETE CASCADE,
                    relation_kind TEXT NOT NULL DEFAULT '=',
                    created_at TEXT NOT NULL,
                    CHECK (left_item_id < right_item_id),
                    UNIQUE(left_item_id, right_item_id, relation_kind)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER NOT NULL REFERENCES collection_items(id) ON DELETE CASCADE,
                    source_path TEXT NOT NULL,
                    rel_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    ext TEXT NOT NULL DEFAULT '',
                    mime TEXT NOT NULL DEFAULT '',
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    meta_json TEXT NOT NULL DEFAULT '',
                    is_missing INTEGER NOT NULL DEFAULT 0 CHECK (is_missing IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_category (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    parent_id INTEGER REFERENCES shop_category(id) ON DELETE SET NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category_id INTEGER REFERENCES shop_category(id) ON DELETE SET NULL,
                    user_notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_source (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL REFERENCES shop_item(id) ON DELETE CASCADE,
                    shop_code TEXT NOT NULL,
                    url TEXT NOT NULL,
                    sku TEXT NOT NULL DEFAULT '',
                    currency TEXT NOT NULL DEFAULT '',
                    price REAL,
                    in_stock INTEGER NOT NULL DEFAULT 0 CHECK (in_stock IN (0, 1)),
                    stock_text TEXT NOT NULL DEFAULT '',
                    parsed_at TEXT NOT NULL DEFAULT '',
                    raw_json TEXT NOT NULL DEFAULT '',
                    UNIQUE(url)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES shop_source(id) ON DELETE CASCADE,
                    price REAL,
                    currency TEXT NOT NULL DEFAULT '',
                    in_stock INTEGER NOT NULL DEFAULT 0 CHECK (in_stock IN (0, 1)),
                    captured_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_item_property (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL REFERENCES shop_item(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    unit TEXT NOT NULL DEFAULT '',
                    normalized_key TEXT NOT NULL DEFAULT ''
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_source_property (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES shop_source(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    unit TEXT NOT NULL DEFAULT '',
                    normalized_key TEXT NOT NULL DEFAULT ''
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_compare_set (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER REFERENCES shop_category(id) ON DELETE SET NULL,
                    item_id INTEGER NOT NULL REFERENCES shop_item(id) ON DELETE CASCADE,
                    UNIQUE(category_id, item_id)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shop_parse_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER REFERENCES shop_source(id) ON DELETE SET NULL,
                    shop_code TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL,
                    status_code INTEGER,
                    content_type TEXT NOT NULL DEFAULT '',
                    fetched_at TEXT NOT NULL,
                    raw_snippet TEXT NOT NULL DEFAULT ''
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wishlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wishlist_item (
                    wishlist_id INTEGER NOT NULL REFERENCES wishlist(id) ON DELETE CASCADE,
                    item_id INTEGER NOT NULL REFERENCES shop_item(id) ON DELETE CASCADE,
                    qty INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 3,
                    target_price REAL,
                    chosen_source_id INTEGER REFERENCES shop_source(id) ON DELETE SET NULL,
                    UNIQUE(wishlist_id, item_id)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_day ON tasks(day);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
            task_columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
            task_column_names = {row["name"] for row in task_columns}
            if "project_id" in task_column_names:
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_area ON projects(area);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(archived);")
            project_columns = self._conn.execute("PRAGMA table_info(projects);").fetchall()
            project_column_names = {row["name"] for row in project_columns}
            if "parent_project_id" in project_column_names:
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_parent ON projects(parent_project_id);")
            if "parent_project_id" in project_column_names and "sort_order" in project_column_names:
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_projects_parent_order ON projects(parent_project_id, sort_order, id);"
                )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_maps_project ON maps(project);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_map_markers_map ON map_markers(map_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_map_overlays_map ON map_overlays(map_id);")
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
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_items_topic ON collection_items(topic);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_items_entity_type ON collection_items(entity_type);")
            columns = self._conn.execute("PRAGMA table_info(collection_items);").fetchall()
            names = {row["name"] for row in columns}
            if "category_id" in names:
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_collection_items_category ON collection_items(category_id);"
                )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_relations_left ON collection_relations(left_item_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_relations_right ON collection_relations(right_item_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_category_parent ON collection_category(parent_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_item_collection ON collection_item(collection_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_item_source ON collection_item(source_path);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_shop_source_item ON shop_source(item_id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shop_price_history_source ON shop_price_history(source_id, captured_at);"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_shop_compare_item ON shop_compare_set(item_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_item_wishlist ON wishlist_item(wishlist_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_item_item ON wishlist_item(item_id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_shop_parse_log_source ON shop_parse_log(source_id);")

        self._run_schema_migrations()
        self._seed_defaults()

    def _run_schema_migrations(self) -> None:
        """РџСЂРёРјРµРЅСЏРµС‚ РІРµСЂСЃРёРѕРЅРёСЂРѕРІР°РЅРЅС‹Рµ РјРёРіСЂР°С†РёРё СЃС…РµРјС‹ SQLite."""
        steps = [
            MigrationStep(1, "core_task_project_schema", self._migration_v1_core_task_project_schema),
            MigrationStep(2, "map_marker_and_attachment_schema", self._migration_v2_map_marker_and_attachment_schema),
            MigrationStep(3, "collection_schema", self._migration_v3_collection_schema),
        ]
        apply_migrations(self._conn, steps)

    def apply_schema_updates(self) -> int:
        """РџСЂРёРјРµРЅСЏРµС‚ РІСЃРµ РґРѕСЃС‚СѓРїРЅС‹Рµ РјРёРіСЂР°С†РёРё СЃС…РµРјС‹ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ user_version."""
        self._run_schema_migrations()
        row = self._conn.execute("PRAGMA user_version;").fetchone()
        return int(row[0]) if row else 0

    def _migration_v1_core_task_project_schema(self, _connection: sqlite3.Connection) -> None:
        """РњРёРіСЂР°С†РёСЏ v1: РІС‹СЂР°РІРЅРёРІР°РЅРёРµ Р±Р°Р·РѕРІС‹С… РєРѕР»РѕРЅРѕРє Р·Р°РґР°С‡/РїСЂРѕРµРєС‚РѕРІ Рё РёРЅРґРµРєСЃРѕРІ."""
        self._ensure_task_project_column()
        self._ensure_project_extended_columns()
        self._ensure_task_description_column()
        self._ensure_task_parent_column()
        self._ensure_task_recurrence_columns()
        self._ensure_task_marker_columns()
        self._ensure_task_completion_delay_column()
        self._ensure_task_gantt_columns()
        self._ensure_priority_values()
        self._ensure_map_tiles_path_column()
        self._ensure_project_marker_columns()

    def _migration_v2_map_marker_and_attachment_schema(self, _connection: sqlite3.Connection) -> None:
        """РњРёРіСЂР°С†РёСЏ v2: РїСЂРёРІРµРґРµРЅРёРµ СЃС‚СЂСѓРєС‚СѓСЂС‹ РјРµС‚РѕРє РєР°СЂС‚С‹ Рё РІР»РѕР¶РµРЅРёР№ Р·Р°РґР°С‡."""
        self._ensure_marker_attachment_columns()
        self._ensure_marker_parent_path_column()
        self._ensure_marker_image_column()
        self._ensure_map_marker_foreign_keys()
        self._ensure_task_attachment_foreign_keys()

    def _migration_v3_collection_schema(self, _connection: sqlite3.Connection) -> None:
        """РњРёРіСЂР°С†РёСЏ v3: РїСЂРёРІРµРґРµРЅРёРµ С‚Р°Р±Р»РёС† РєРѕР»Р»РµРєС†РёР№ Рё СЃРІСЏР·Р°РЅРЅС‹С… РєРѕР»РѕРЅРѕРє."""
        self._ensure_collection_category_table()
        self._ensure_collection_item_category_column()
        self._ensure_collection_item_extra_columns()
        self._ensure_collection_entry_columns()

    def _ensure_task_project_column(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ project_id, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "project_id" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER REFERENCES projects(id);")

    def _ensure_project_extended_columns(self) -> None:
        """Р вЂќР С•Р В±Р В°Р Р†Р В»РЎРЏР ВµРЎвЂљ РЎР‚Р В°РЎРѓРЎв‚¬Р С‘РЎР‚Р ВµР Р…Р Р…РЎвЂ№Р Вµ Р С”Р С•Р В»Р С•Р Р…Р С”Р С‘ Р С—РЎР‚Р С•Р ВµР С”РЎвЂљР С•Р Р†, Р ВµРЎРѓР В»Р С‘ Р С•Р Р…Р С‘ Р С•РЎвЂљРЎРѓРЎС“РЎвЂљРЎРѓРЎвЂљР Р†РЎС“РЎР‹РЎвЂљ."""
        columns = self._conn.execute("PRAGMA table_info(projects);").fetchall()
        names = {row["name"] for row in columns}
        additions = {
            "parent_project_id": "ALTER TABLE projects ADD COLUMN parent_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;",
            "sort_order": "ALTER TABLE projects ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;",
            "default_task_priority": "ALTER TABLE projects ADD COLUMN default_task_priority TEXT NOT NULL DEFAULT '';",
            "force_recurrence_kind": "ALTER TABLE projects ADD COLUMN force_recurrence_kind TEXT NOT NULL DEFAULT '';",
            "linked_map_id": "ALTER TABLE projects ADD COLUMN linked_map_id INTEGER REFERENCES maps(id) ON DELETE SET NULL;",
            "linked_note_id": "ALTER TABLE projects ADD COLUMN linked_note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL;",
            "linked_object_id": "ALTER TABLE projects ADD COLUMN linked_object_id INTEGER REFERENCES objects(id) ON DELETE SET NULL;",
        }
        with self._conn:
            for column, ddl in additions.items():
                if column not in names:
                    self._conn.execute(ddl)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_parent ON projects(parent_project_id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_parent_order ON projects(parent_project_id, sort_order, id);"
            )
            self._normalize_project_sort_order()

    def _normalize_project_sort_order(self) -> None:
        """РќРѕСЂРјР°Р»РёР·СѓРµС‚ РїРѕСЂСЏРґРѕРє РїСЂРѕРµРєС‚РѕРІ РІРЅСѓС‚СЂРё РєР°Р¶РґРѕРіРѕ СЂРѕРґРёС‚РµР»СЏ."""
        rows = self._conn.execute(
            """
            SELECT id, parent_project_id, COALESCE(sort_order, 0) AS sort_order
            FROM projects
            ORDER BY parent_project_id, sort_order, id;
            """
        ).fetchall()
        grouped: dict[Optional[int], list[int]] = {}
        for row in rows:
            grouped.setdefault(row["parent_project_id"], []).append(int(row["id"]))
        for _, ids in grouped.items():
            for idx, project_id in enumerate(ids):
                self._conn.execute(
                    "UPDATE projects SET sort_order = ? WHERE id = ?;",
                    (idx, project_id),
                )

    def _next_project_sort_order(self, parent_project_id: Optional[int], exclude_id: Optional[int] = None) -> int:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃР»РµРґСѓСЋС‰РёР№ РёРЅРґРµРєСЃ СЃРѕСЂС‚РёСЂРѕРІРєРё РґР»СЏ РґРѕС‡РµСЂРЅРёС… РїСЂРѕРµРєС‚РѕРІ."""
        if exclude_id is None:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sort_order), -1) AS max_order
                FROM projects
                WHERE parent_project_id IS ?;
                """,
                (parent_project_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT COALESCE(MAX(sort_order), -1) AS max_order
                FROM projects
                WHERE parent_project_id IS ?
                  AND id != ?;
                """,
                (parent_project_id, exclude_id),
            ).fetchone()
        return int(row["max_order"]) + 1 if row is not None else 0

    def _ensure_task_description_column(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ description, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "description" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT '';")

    def _ensure_task_parent_column(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ parent_id, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "parent_id" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER REFERENCES tasks(id);")

    def _ensure_task_recurrence_columns(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєРё РїРµСЂРёРѕРґРёС‡РЅРѕСЃС‚Рё Р·Р°РґР°С‡Рё, РµСЃР»Рё РѕРЅРё РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "recurrence_kind" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN recurrence_kind TEXT NOT NULL DEFAULT '';")
            if "recurrence_interval" not in names:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN recurrence_interval INTEGER NOT NULL DEFAULT 1;"
                )

    def _ensure_task_marker_columns(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєРё РІРёР·СѓР°Р»СЊРЅРѕРіРѕ РјР°СЂРєРµСЂР° Р·Р°РґР°С‡Рё, РµСЃР»Рё РѕРЅРё РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "marker_color" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN marker_color TEXT NOT NULL DEFAULT '';")
            if "marker_theme" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN marker_theme TEXT NOT NULL DEFAULT '';")

    def _ensure_task_completion_delay_column(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ СЂР°СЃС…РѕР¶РґРµРЅРёСЏ РїРѕ РІСЂРµРјРµРЅРё РІС‹РїРѕР»РЅРµРЅРёСЏ, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "completion_delay_minutes" not in names:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN completion_delay_minutes INTEGER NOT NULL DEFAULT 0;"
                )

    def _ensure_task_gantt_columns(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєРё РѕС†РµРЅРѕРє Р“Р°РЅС‚Р°, РµСЃР»Рё РѕРЅРё РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "gantt_estimate_minutes" not in names:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0;"
                )
            if "gantt_forecasted" not in names:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN gantt_forecasted INTEGER NOT NULL DEFAULT 0;"
                )

    def _ensure_project_marker_columns(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєРё РІРёР·СѓР°Р»СЊРЅРѕРіРѕ РјР°СЂРєРµСЂР° РїСЂРѕРµРєС‚Р°, РµСЃР»Рё РѕРЅРё РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚."""
        columns = self._conn.execute("PRAGMA table_info(projects);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "marker_color" not in names:
                self._conn.execute("ALTER TABLE projects ADD COLUMN marker_color TEXT NOT NULL DEFAULT '';")
            if "marker_theme" not in names:
                self._conn.execute("ALTER TABLE projects ADD COLUMN marker_theme TEXT NOT NULL DEFAULT '';")

    def _ensure_priority_values(self) -> None:
        """РћР±РЅРѕРІР»СЏРµС‚ РѕРіСЂР°РЅРёС‡РµРЅРёСЏ РїСЂРёРѕСЂРёС‚РµС‚Р° РґРѕ Р°РєС‚СѓР°Р»СЊРЅРѕРіРѕ СЃРїРёСЃРєР° Р·РЅР°С‡РµРЅРёР№."""
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
        """РџСЂРѕРІРµСЂСЏРµС‚, С‡С‚Рѕ project_id РІ tasks СЃСЃС‹Р»Р°РµС‚СЃСЏ РЅР° С‚Р°Р±Р»РёС†Сѓ projects."""
        rows = self._conn.execute("PRAGMA foreign_key_list(tasks);").fetchall()
        project_refs = [row for row in rows if row["from"] == "project_id"]
        if not project_refs:
            return True
        return any(row["table"] != "projects" for row in project_refs)

    def _repair_task_project_fk(self) -> None:
        """РСЃРїСЂР°РІР»СЏРµС‚ РІРЅРµС€РЅРёРµ РєР»СЋС‡Рё tasks.project_id, РµСЃР»Рё РѕРЅРё СЃСЃС‹Р»Р°СЋС‚СЃСЏ РЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‰СѓСЋ С‚Р°Р±Р»РёС†Сѓ."""
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
        """РџСЂРѕРІРµСЂСЏРµС‚, С‡С‚Рѕ РІРЅРµС€РЅРёРµ РєР»СЋС‡Рё map_markers РЅРµ СЃСЃС‹Р»Р°СЋС‚СЃСЏ РЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‰РёРµ С‚Р°Р±Р»РёС†С‹."""
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
        """РСЃРїСЂР°РІР»СЏРµС‚ СѓСЃС‚Р°СЂРµРІС€РёРµ РІРЅРµС€РЅРёРµ РєР»СЋС‡Рё map_markers, РµСЃР»Рё С‚Р°Р±Р»РёС†Р°-РёСЃС‚РѕС‡РЅРёРє РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        if not self._map_marker_fk_needs_repair():
            return
        with self._conn:
            self._conn.execute("PRAGMA foreign_keys=OFF;")
            self._rebuild_map_markers_table()
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_map_markers_map ON map_markers(map_id);")

    def _task_attachment_fk_needs_repair(self) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, С‡С‚Рѕ РІРЅРµС€РЅРёРµ РєР»СЋС‡Рё task_attachments СЃСЃС‹Р»Р°СЋС‚СЃСЏ РЅР° tasks."""
        tables = {
            row["name"]
            for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        if "task_attachments" not in tables:
            return False
        rows = self._conn.execute("PRAGMA foreign_key_list(task_attachments);").fetchall()
        if not rows:
            return False
        return any(row["table"] not in tables or row["table"] != "tasks" for row in rows)

    def _ensure_task_attachment_foreign_keys(self) -> None:
        """РСЃРїСЂР°РІР»СЏРµС‚ СѓСЃС‚Р°СЂРµРІС€РёРµ РІРЅРµС€РЅРёРµ РєР»СЋС‡Рё task_attachments, РµСЃР»Рё С‚Р°Р±Р»РёС†Р°-РёСЃС‚РѕС‡РЅРёРє РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        if not self._task_attachment_fk_needs_repair():
            return
        with self._conn:
            self._conn.execute("PRAGMA foreign_keys=OFF;")
            self._rebuild_task_attachments_table()
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_task_attachments_task ON task_attachments(task_id);")

    def _ensure_collection_category_table(self) -> None:
        tables = {
            row["name"]
            for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        if "collection_category" not in tables:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS collection_category (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        parent_id INTEGER REFERENCES collection_category(id) ON DELETE SET NULL,
                        sort_index INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(title, parent_id)
                    );
                    """
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_collection_category_parent ON collection_category(parent_id);"
                )

    def _ensure_collection_item_category_column(self) -> None:
        columns = self._conn.execute("PRAGMA table_info(collection_items);").fetchall()
        names = {row["name"] for row in columns}
        if "category_id" not in names:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE collection_items ADD COLUMN category_id INTEGER REFERENCES collection_category(id) ON DELETE SET NULL;"
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_collection_items_category ON collection_items(category_id);"
                )

    def _ensure_collection_item_extra_columns(self) -> None:
        columns = self._conn.execute("PRAGMA table_info(collection_items);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "source_folder_path" not in names:
                self._conn.execute(
                    "ALTER TABLE collection_items ADD COLUMN source_folder_path TEXT NOT NULL DEFAULT '';"
                )
            if "import_options_json" not in names:
                self._conn.execute(
                    "ALTER TABLE collection_items ADD COLUMN import_options_json TEXT NOT NULL DEFAULT '';"
                )

    def _ensure_collection_entry_columns(self) -> None:
        columns = self._conn.execute("PRAGMA table_info(collection_item);").fetchall()
        if not columns:
            return
        names = {row["name"] for row in columns}
        with self._conn:
            if "is_missing" not in names:
                self._conn.execute(
                    "ALTER TABLE collection_item ADD COLUMN is_missing INTEGER NOT NULL DEFAULT 0 CHECK (is_missing IN (0, 1));"
                )

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
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        return "РћС‚Р»РѕР¶РµРЅРЅР°СЏ" in (row["sql"] or "")

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
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'РћС‚Р»РѕР¶РµРЅРЅР°СЏ')),
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                completion_delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK (completion_delay_minutes >= 0),
                gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0 CHECK (gantt_estimate_minutes >= 0),
                gantt_forecasted INTEGER NOT NULL DEFAULT 0 CHECK (gantt_forecasted IN (0, 1)),
                project_id INTEGER REFERENCES projects(id),
                parent_id INTEGER REFERENCES tasks(id),
                recurrence_kind TEXT NOT NULL DEFAULT '',
                recurrence_interval INTEGER NOT NULL DEFAULT 1 CHECK (recurrence_interval >= 1),
                marker_color TEXT NOT NULL DEFAULT '',
                marker_theme TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.execute(
            """
            INSERT INTO tasks (
                id, title, description, day, time_text, priority, done, completion_delay_minutes, gantt_estimate_minutes,
                gantt_forecasted, project_id, parent_id, recurrence_kind, recurrence_interval, marker_color, marker_theme, created_at, updated_at
            )
            SELECT id, title, description, day, time_text, priority, done, COALESCE(completion_delay_minutes, 0),
                   COALESCE(gantt_estimate_minutes, 0), COALESCE(gantt_forecasted, 0), project_id, parent_id,
                   COALESCE(recurrence_kind, ''), COALESCE(recurrence_interval, 1),
                   COALESCE(marker_color, ''), COALESCE(marker_theme, ''), created_at, updated_at
            FROM tasks_old;
            """
        )
        self._conn.execute("DROP TABLE tasks_old;")
        self._rebuild_task_attachments_table()

    def _rebuild_projects_table(self) -> None:
        self._conn.execute("ALTER TABLE projects RENAME TO projects_old;")
        self._conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'РћС‚Р»РѕР¶РµРЅРЅР°СЏ')),
                archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
                parent_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                default_task_priority TEXT NOT NULL DEFAULT '',
                force_recurrence_kind TEXT NOT NULL DEFAULT '',
                linked_map_id INTEGER REFERENCES maps(id) ON DELETE SET NULL,
                linked_note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
                linked_object_id INTEGER REFERENCES objects(id) ON DELETE SET NULL,
                marker_color TEXT NOT NULL DEFAULT '',
                marker_theme TEXT NOT NULL DEFAULT ''
            );
            """
        )
        old_columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(projects_old);").fetchall()
        }

        def _source(column: str, fallback: str) -> str:
            return column if column in old_columns else fallback

        self._conn.execute(
            f"""
            INSERT INTO projects (
                id,
                area,
                title,
                updated,
                priority,
                archived,
                parent_project_id,
                sort_order,
                default_task_priority,
                force_recurrence_kind,
                linked_map_id,
                linked_note_id,
                linked_object_id,
                marker_color,
                marker_theme
            )
            SELECT
                id,
                area,
                title,
                updated,
                priority,
                archived,
                {_source("parent_project_id", "NULL")},
                COALESCE({_source("sort_order", "0")}, 0),
                COALESCE({_source("default_task_priority", "''")}, ''),
                COALESCE({_source("force_recurrence_kind", "''")}, ''),
                {_source("linked_map_id", "NULL")},
                {_source("linked_note_id", "NULL")},
                {_source("linked_object_id", "NULL")},
                COALESCE({_source("marker_color", "''")}, ''),
                COALESCE({_source("marker_theme", "''")}, '')
            FROM projects_old;
            """
        )
        self._conn.execute("DROP TABLE projects_old;")
        self._normalize_project_sort_order()

    def _ensure_priority_indexes(self) -> None:
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_day ON tasks(day);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_parent ON projects(parent_project_id);")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_projects_parent_order ON projects(parent_project_id, sort_order, id);"
        )

    def _rebuild_task_attachments_table(self) -> None:
        columns = self._conn.execute("PRAGMA table_info(task_attachments);").fetchall()
        names = {row["name"] for row in columns}
        if not names:
            return
        self._conn.execute("ALTER TABLE task_attachments RENAME TO task_attachments_old;")
        self._conn.execute(
            """
            CREATE TABLE task_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                ref_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(task_id, kind, ref_id)
            );
            """
        )
        rows = self._conn.execute(
            "SELECT id, task_id, kind, ref_id, created_at FROM task_attachments_old;"
        ).fetchall()
        for row in rows:
            self._conn.execute(
                """
                INSERT INTO task_attachments (id, task_id, kind, ref_id, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (row["id"], row["task_id"], row["kind"], row["ref_id"], row["created_at"]),
            )
        self._conn.execute("DROP TABLE task_attachments_old;")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_task_attachments_task ON task_attachments(task_id);")

    def _ensure_map_tiles_path_column(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ tiles_path, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(maps);").fetchall()
        names = {row["name"] for row in columns}
        if "tiles_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE maps ADD COLUMN tiles_path TEXT NOT NULL DEFAULT '';")

    def _ensure_marker_attachment_columns(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РЅРѕРІС‹Рµ РєРѕР»РѕРЅРєРё РґР»СЏ РІР»РѕР¶РµРЅРёР№ РјР°СЂРєРµСЂР° РєР°СЂС‚С‹."""
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
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ РїСЂРµРІСЊСЋ РґР»СЏ РјР°СЂРєРµСЂРѕРІ, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(map_markers);").fetchall()
        names = {row["name"] for row in columns}
        if "image_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE map_markers ADD COLUMN image_path TEXT NOT NULL DEFAULT '';")

    def _ensure_marker_parent_path_column(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РєРѕР»РѕРЅРєСѓ СЂРѕРґРёС‚РµР»СЊСЃРєРѕРіРѕ РєР°С‚Р°Р»РѕРіР° РґР»СЏ РјР°СЂРєРµСЂРѕРІ, РµСЃР»Рё РѕРЅР° РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚."""
        columns = self._conn.execute("PRAGMA table_info(map_markers);").fetchall()
        names = {row["name"] for row in columns}
        if "parent_path" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE map_markers ADD COLUMN parent_path TEXT NOT NULL DEFAULT '';")

    def _seed_defaults(self) -> None:
        """Р”РѕР±Р°РІР»СЏРµС‚ РґРµРјРѕРЅСЃС‚СЂР°С†РёРѕРЅРЅС‹Рµ РґР°РЅРЅС‹Рµ, РµСЃР»Рё Р±Р°Р·Р° РїСѓСЃС‚Р°СЏ."""
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
            (days[0], "14:00", "Wiki в†’ Picture", "High", 0),
            (days[1], "15:00", "РџРѕРґСѓРјР°С‚СЊ РЅР°Рґ DragAndDrop РґР»СЏ СЃРїРёСЃРєР° Р·Р°РґР°С‡ РІ СЂРµР¶РёРјРµ РїР»Р°РЅ", "Medium", 0),
            (days[1], "16:00", "Р‘РёР»РµС‚С‹ РџР”Р”", "Low", 0),
            (days[1], "17:00", "РџСЂРѕСЃРјРѕС‚СЂРµС‚СЊ FAV", "Medium", 0),
            (days[1], "19:00", "РџСЂРѕСЃРјРѕС‚СЂРµС‚СЊ Р·Р°РїРёСЃРё РІРѕ РІСЃРµС… РєР°РЅР°Р»Р°С… РР·Р±СЂР°РЅРЅРѕРіРѕ", "Medium", 0),
            (days[2], "20:00", "SimCity Societies в†’ KitBash в†’ Р—РґР°РЅРёСЏ СѓСЃР°РґСЊР±С‹. Р—РґР°РЅРёРµ С€РєРѕР»С‹. РњРЅРѕРіРѕСЌС‚Р°Р¶РєР°вЂ¦", "High", 0),
            (days[3], "22:00", "Stygian В· Reign of the Old Ones", "High", 0),
            (days[3], "23:00", "The Council", "High", 1),
        ]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
            ("SPACE", "РЎРёРЅС…СЂРѕРЅРёР·Р°С†РёСЏ FastAPI + S3", "05.01.2026", "Medium", 0),
            ("TACMap", "Р РµРґР°РєС‚РѕСЂ СЃР»РѕС‘РІ / РјР°СЂРєРµСЂРѕРІ", "03.01.2026", "High", 0),
            ("MakerTask", "ProjectsWorkspace UI (РїСЂРѕС‚РѕС‚РёРї)", "02.10.2025", "Medium", 0),
            ("MakerTask", "Drag&Drop РїР»Р°РЅРёСЂРѕРІС‰РёРєР°", "01.10.2025", "High", 1),
            ("Wiki", "Cities: Skylines в†’ DokuWiki", "22.07.2025", "Low", 0),
            ("Misc", "РЎР±РѕСЂ СЂРµС„РµСЂРµРЅСЃРѕРІ / moodboard", "01.01.2026", "Low", 0),
        ]
        with self._conn:
            for idx, (area, title, updated, priority, archived) in enumerate(examples):
                self._conn.execute(
                    """
                    INSERT INTO projects (area, title, updated, priority, archived, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (area, title, parse_project_date(updated).isoformat(), priority, archived, idx),
                )

    def _seed_maps(self) -> None:
        examples = [
            ("Northern Ridge", "РўРѕС‡РєРё РѕР±Р·РѕСЂР° Рё РјР°СЂС€СЂСѓС‚С‹ РїР°С‚СЂСѓР»РµР№.", "MindNavigator v2", "", 18, 24),
            ("Sector 12", "Р—РѕРЅС‹ РєРѕРЅС‚СЂРѕР»СЏ Рё РјРёРЅРЅС‹Рµ РїРѕР»СЏ.", "TACMap", "", 32, 32),
            ("Green Hills", "РђСЂС‚РёР»Р»РµСЂРёР№СЃРєРёРµ РїРѕР·РёС†РёРё Рё РЅР°Р±Р»СЋРґР°С‚РµР»Рё.", "Wiki", "", 12, 20),
        ]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        now = datetime.now(timezone.utc)
        examples = [
            (
                "РћРЅР±РѕСЂРґРёРЅРі РїСЂРѕРґСѓРєС‚Р°",
                "РљР»СЋС‡РµРІС‹Рµ С€Р°РіРё Р·Р°РїСѓСЃРєР°, СЃРїРёСЃРѕРє СЂРёСЃРєРѕРІ Рё СЃРїРёСЃРѕРє Р±Р»РѕРєРµСЂРѕРІ РґР»СЏ РїРµСЂРІРѕР№ РІРµСЂСЃРёРё...",
                ["product", "launch", "priority"],
                now - timedelta(hours=2),
                "MindNavigator",
                True,
                True,
                False,
            ),
            (
                "РСЃСЃР»РµРґРѕРІР°РЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№",
                "РЎРІРѕРґРєР° РёРЅС‚РµСЂРІСЊСЋ: Р±РѕР»РµРІС‹Рµ С‚РѕС‡РєРё, РїСЂРёРІС‹С‡РєРё РІРµРґРµРЅРёСЏ Р·Р°РјРµС‚РѕРє, РѕР¶РёРґР°РЅРёСЏ РѕС‚ РїРѕРёСЃРєР°...",
                ["research", "ux"],
                now - timedelta(days=1, hours=3),
                "Discovery",
                False,
                False,
                False,
            ),
            (
                "РђСЂС…РёС‚РµРєС‚СѓСЂР° СЃРёРЅС…СЂРѕРЅРёР·Р°С†РёРё",
                "РљРѕРЅС‚СѓСЂС‹ API: FastAPI, SQLite, РѕС„С„Р»Р°Р№РЅ-РѕС‡РµСЂРµРґРё, С„РѕСЂРјР°С‚С‹ СЃРѕР±С‹С‚РёР№...",
                ["backend", "sync"],
                now - timedelta(days=2),
                "Platform",
                False,
                False,
                True,
            ),
            (
                "UI-СЂРµС„РµСЂРµРЅСЃС‹",
                "Obsidian + Notion + IDE: РєРѕРЅС‚СЂР°СЃС‚, РєР°СЂС‚РѕС‡РєРё, РјРёРЅРёРјР°Р»РёР·Рј, Р±С‹СЃС‚СЂС‹Рµ СЌРєС€РµРЅС‹...",
                ["ui", "references"],
                now - timedelta(days=3, hours=5),
                "Design",
                True,
                False,
                False,
            ),
            (
                "Р§РµРєР»РёСЃС‚ СЂРµР»РёР·Р°",
                "Checklist: С‚РµСЃС‚С‹, РґРѕРєСѓРјРµРЅС‚Р°С†РёСЏ, СЃРєСЂРёРЅС€РѕС‚С‹, СЂРµР»РёР·РЅС‹Рµ Р·Р°РјРµС‚РєРё...",
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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… Р·Р°РґР°С‡."""
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
                t.completion_delay_minutes,
                t.gantt_estimate_minutes,
                t.gantt_forecasted,
                t.project_id,
                t.marker_color,
                t.marker_theme,
                CASE
                    WHEN pp.id IS NOT NULL THEN COALESCE(pp.title, '') || ' / ' || COALESCE(p.title, '')
                    ELSE COALESCE(p.title, '')
                END AS project_title,
                COALESCE(p.area, '') AS project_area,
                t.parent_id,
                t.recurrence_kind,
                t.recurrence_interval
            FROM tasks t
            LEFT JOIN projects p ON p.id = t.project_id
            LEFT JOIN projects pp ON pp.id = p.parent_project_id;
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
                    completion_delay_minutes=max(0, int(row["completion_delay_minutes"] or 0)),
                    gantt_estimate_minutes=max(0, int(row["gantt_estimate_minutes"] or 0)),
                    gantt_forecasted=bool(row["gantt_forecasted"]),
                    project_id=row["project_id"],
                    project_title=row["project_title"] or "",
                    project_area=row["project_area"] or "",
                    parent_id=row["parent_id"],
                    recurrence_kind=row["recurrence_kind"] or "",
                    recurrence_interval=max(1, int(row["recurrence_interval"] or 1)),
                    marker_color=(row["marker_color"] or "").strip(),
                    marker_theme=(row["marker_theme"] or "").strip(),
                )
            )
        return tasks

    def _seed_objects(self) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        examples = [
            (
                "Р¦РµРЅС‚СЂР°Р»СЊРЅС‹Р№ РѕС„РёСЃ",
                "Р“РѕСЂРѕРґ / РђРґРјРёРЅРёСЃС‚СЂР°С‚РёРІРЅС‹Рµ",
                "Р‘РёР·РЅРµСЃ-С†РµРЅС‚СЂ",
                "Р’ СЌРєСЃРїР»СѓР°С‚Р°С†РёРё",
                "Р“Р»Р°РІРЅС‹Р№ РѕС„РёСЃ СЃ Р·РѕРЅР°РјРё РїСЂРёРµРјР° Рё РїРµСЂРµРіРѕРІРѕСЂРЅС‹РјРё.",
            ),
            (
                "РЎРєР»Р°РґСЃРєР°СЏ Р·РѕРЅР° РЎРµРІРµСЂ",
                "Р›РѕРіРёСЃС‚РёРєР°",
                "РЎРєР»Р°Рґ",
                "РџСЂРѕРµРєС‚РёСЂРѕРІР°РЅРёРµ",
                "РџР»РѕС‰Р°РґРєР° РїРѕРґ СЂР°СЃРїСЂРµРґРµР»РёС‚РµР»СЊРЅС‹Р№ С†РµРЅС‚СЂ Рё С‚РµС…РЅРѕР»РѕРіРёС‡РµСЃРєРёРµ Р±Р»РѕРєРё.",
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
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        marker_color: str = "",
        marker_theme: str = "",
    ) -> TaskData:
        """РЎРѕР·РґР°РµС‚ Р·Р°РґР°С‡Сѓ РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…."""
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        recurrence_kind = (recurrence_kind or "").strip().lower()
        recurrence_interval = max(1, int(recurrence_interval or 1))
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if not isinstance(day, date):
            raise ValueError("Р”Р°С‚Р° Р·Р°РґР°С‡Рё РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")

        project_title = ""
        project_area = ""
        project_links: List[Tuple[str, int]] = []
        if project_id is not None:
            row = self._conn.execute(
                """
                SELECT
                    p.area, p.title, pp.title AS parent_title, p.default_task_priority, p.force_recurrence_kind,
                    p.linked_map_id, p.linked_note_id, p.linked_object_id
                FROM projects p
                LEFT JOIN projects pp ON pp.id = p.parent_project_id
                WHERE p.id = ?;
                """,
                (project_id,),
            ).fetchone()
            if row:
                project_area = row["area"]
                project_title = f'{row["parent_title"]} / {row["title"]}' if row["parent_title"] else row["title"]
                forced_priority = (row["default_task_priority"] or "").strip()
                forced_recurrence = (row["force_recurrence_kind"] or "").strip().lower()
                if forced_priority:
                    priority = normalize_priority(forced_priority)
                if forced_recurrence in {"daily", "weekly", "monthly"}:
                    recurrence_kind = forced_recurrence
                    recurrence_interval = max(1, recurrence_interval)
                for kind, ref_id in (
                    ("map", row["linked_map_id"]),
                    ("note", row["linked_note_id"]),
                    ("object", row["linked_object_id"]),
                ):
                    if ref_id is not None:
                        project_links.append((kind, int(ref_id)))

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO tasks (
                    title, description, day, time_text, priority, done, project_id, parent_id,
                    recurrence_kind, recurrence_interval, marker_color, marker_theme, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    description,
                    day.isoformat(),
                    time_text,
                    priority,
                    project_id,
                    parent_id,
                    recurrence_kind,
                    recurrence_interval,
                    marker_color,
                    marker_theme,
                    now,
                    now,
                ),
            )
        for kind, ref_id in project_links:
            self.add_task_attachment(cur.lastrowid, kind, ref_id)
        return TaskData(
            id=cur.lastrowid,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
            done=False,
            project_id=project_id,
            project_title=project_title,
            project_area=project_area,
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            completion_delay_minutes=0,
            gantt_estimate_minutes=0,
            gantt_forecasted=False,
            marker_color=marker_color,
            marker_theme=marker_theme,
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
        recurrence_kind: str = "",
        recurrence_interval: int = 1,
        marker_color: str = "",
        marker_theme: str = "",
    ) -> TaskData:
        """РћР±РЅРѕРІР»СЏРµС‚ Р·Р°РґР°С‡Сѓ."""
        prev_row = self._conn.execute(
            "SELECT priority FROM tasks WHERE id = ?;",
            (task_id,),
        ).fetchone()
        prev_priority = prev_row["priority"] if prev_row else priority
        title = validate_title(title)
        description = (description or "").strip()
        time_text = validate_time_text(time_text)
        priority = normalize_priority(priority)
        recurrence_kind = (recurrence_kind or "").strip().lower()
        recurrence_interval = max(1, int(recurrence_interval or 1))
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if not isinstance(day, date):
            raise ValueError("Р”Р°С‚Р° Р·Р°РґР°С‡Рё РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")

        project_title = ""
        project_area = ""
        project_links: List[Tuple[str, int]] = []
        if project_id is not None:
            row = self._conn.execute(
                """
                SELECT p.area, p.title, pp.title AS parent_title, p.default_task_priority, p.force_recurrence_kind
                FROM projects p
                LEFT JOIN projects pp ON pp.id = p.parent_project_id
                WHERE p.id = ?;
                """,
                (project_id,),
            ).fetchone()
            if row:
                project_area = row["area"]
                project_title = f'{row["parent_title"]} / {row["title"]}' if row["parent_title"] else row["title"]
                forced_priority = (row["default_task_priority"] or "").strip()
                forced_recurrence = (row["force_recurrence_kind"] or "").strip().lower()
                if forced_priority:
                    priority = normalize_priority(forced_priority)
                if forced_recurrence in {"daily", "weekly", "monthly"}:
                    recurrence_kind = forced_recurrence
                    recurrence_interval = max(1, recurrence_interval)
            links_row = self._conn.execute(
                """
                SELECT linked_map_id, linked_note_id, linked_object_id
                FROM projects
                WHERE id = ?;
                """,
                (project_id,),
            ).fetchone()
            if links_row:
                for kind, ref_id in (
                    ("map", links_row["linked_map_id"]),
                    ("note", links_row["linked_note_id"]),
                    ("object", links_row["linked_object_id"]),
                ):
                    if ref_id is not None:
                        project_links.append((kind, int(ref_id)))

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, day = ?, time_text = ?, priority = ?, done = ?, project_id = ?, parent_id = ?,
                    recurrence_kind = ?, recurrence_interval = ?, marker_color = ?, marker_theme = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    description,
                    day.isoformat(),
                    time_text,
                    priority,
                    int(done),
                    project_id,
                    parent_id,
                    recurrence_kind,
                    recurrence_interval,
                    marker_color,
                    marker_theme,
                    now,
                    task_id,
                ),
            )
            cascade_priority = None
            if priority == "РћС‚Р»РѕР¶РµРЅРЅР°СЏ" and prev_priority != "РћС‚Р»РѕР¶РµРЅРЅР°СЏ":
                cascade_priority = priority
            elif prev_priority == "РћС‚Р»РѕР¶РµРЅРЅР°СЏ" and priority != "РћС‚Р»РѕР¶РµРЅРЅР°СЏ":
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
        for kind, ref_id in project_links:
            self.add_task_attachment(task_id, kind, ref_id)
        return TaskData(
            id=task_id,
            day=day,
            time_text=time_text,
            title=title,
            description=description,
            priority=priority,
            done=bool(done),
            project_id=project_id,
            project_title=project_title,
            project_area=project_area,
            parent_id=parent_id,
            recurrence_kind=recurrence_kind,
            recurrence_interval=recurrence_interval,
            completion_delay_minutes=0,
            gantt_estimate_minutes=0,
            gantt_forecasted=False,
            marker_color=marker_color,
            marker_theme=marker_theme,
        )

    def set_task_done(self, task_id: int, done: bool) -> None:
        """РћР±РЅРѕРІР»СЏРµС‚ СЃС‚Р°С‚СѓСЃ РІС‹РїРѕР»РЅРµРЅРёСЏ Р·Р°РґР°С‡Рё."""
        row = self._conn.execute(
            """
            SELECT
                id, title, description, day, time_text, priority, done, project_id, parent_id,
                recurrence_kind, recurrence_interval, marker_color, marker_theme
            FROM tasks
            WHERE id = ?;
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            return
        prev_done = bool(row["done"])
        recurrence_kind = (row["recurrence_kind"] or "").strip().lower()
        recurrence_interval = max(1, int(row["recurrence_interval"] or 1))
        now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
        completed_local = datetime.now()
        planned_day = date.fromisoformat(row["day"])
        planned_time_text = (row["time_text"] or "").strip()
        try:
            if planned_time_text:
                planned_dt = datetime.strptime(
                    f"{planned_day.isoformat()} {planned_time_text}",
                    "%Y-%m-%d %H:%M",
                )
            else:
                planned_dt = datetime.combine(planned_day, datetime.min.time())
        except ValueError:
            planned_dt = datetime.combine(planned_day, datetime.min.time())
        completion_delay_minutes = 0
        if done:
            delta_minutes = int((completed_local - planned_dt).total_seconds() // 60)
            if delta_minutes > 0:
                completion_delay_minutes = delta_minutes
        with self._conn:
            if done:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET done = ?, day = ?, time_text = ?, completion_delay_minutes = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        int(done),
                        completed_local.date().isoformat(),
                        completed_local.strftime("%H:%M"),
                        completion_delay_minutes,
                        now_utc,
                        task_id,
                    ),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET done = ?, completion_delay_minutes = 0, updated_at = ?
                    WHERE id = ?;
                    """,
                    (int(done), now_utc, task_id),
                )
            if done and not prev_done and recurrence_kind:
                current_day = planned_day
                next_day = self._next_recurrence_day(current_day, recurrence_kind, recurrence_interval)
                self._conn.execute(
                    """
                    INSERT INTO tasks (
                        title, description, day, time_text, priority, done, project_id, parent_id,
                        recurrence_kind, recurrence_interval, marker_color, marker_theme, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        row["title"],
                        row["description"] or "",
                        next_day.isoformat(),
                        row["time_text"] or "",
                        row["priority"],
                        row["project_id"],
                        row["parent_id"],
                        recurrence_kind,
                        recurrence_interval,
                        row["marker_color"] or "",
                        row["marker_theme"] or "",
                        now_utc,
                        now_utc,
                    ),
                )

    def set_task_gantt_estimate(self, task_id: int, minutes: int, forecasted: bool = True) -> None:
        """РЎРѕС…СЂР°РЅСЏРµС‚ РѕС†РµРЅРєСѓ РІСЂРµРјРµРЅРё Р·Р°РґР°С‡Рё РґР»СЏ СЂРµР¶РёРјР° РґРёР°РіСЂР°РјРјС‹ Р“Р°РЅС‚Р°."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        safe_minutes = max(0, int(minutes or 0))
        with self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET gantt_estimate_minutes = ?, gantt_forecasted = ?, updated_at = ?
                WHERE id = ?;
                """,
                (safe_minutes, int(bool(forecasted)), now, task_id),
            )

    def _next_recurrence_day(self, base_day: date, recurrence_kind: str, recurrence_interval: int) -> date:
        interval = max(1, int(recurrence_interval or 1))
        if recurrence_kind == "daily":
            return base_day + timedelta(days=interval)
        if recurrence_kind == "weekly":
            return base_day + timedelta(days=7 * interval)
        if recurrence_kind == "monthly":
            return self._add_months(base_day, interval)
        return base_day

    @staticmethod
    def _add_months(base_day: date, months: int) -> date:
        month0 = base_day.month - 1 + max(1, months)
        year = base_day.year + month0 // 12
        month = month0 % 12 + 1
        if month == 2:
            leap = (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0)
            max_day = 29 if leap else 28
        elif month in {4, 6, 9, 11}:
            max_day = 30
        else:
            max_day = 31
        day = min(base_day.day, max_day)
        return date(year, month, day)

    def delete_task(self, task_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ Р·Р°РґР°С‡Сѓ РїРѕ id."""
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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІР»РѕР¶РµРЅРёР№ Р·Р°РґР°С‡Рё."""
        task_id = int(task_id)
        rows = self._conn.execute(
            """
            SELECT id, task_id, kind, ref_id, created_at
            FROM task_attachments
            WHERE task_id = ?
            ORDER BY created_at ASC;
            """,
            (task_id,),
        ).fetchall()
        return [TaskAttachmentData.from_row(row) for row in rows]

    def add_task_attachment(self, task_id: int, kind: str, ref_id: int) -> TaskAttachmentData:
        """Р”РѕР±Р°РІР»СЏРµС‚ РІР»РѕР¶РµРЅРёРµ Рє Р·Р°РґР°С‡Рµ."""
        task_id = int(task_id)
        if task_id <= 0:
            raise ValueError("РРґРµРЅС‚РёС„РёРєР°С‚РѕСЂ Р·Р°РґР°С‡Рё РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј.")
        ref_id = int(ref_id)
        if ref_id <= 0:
            raise ValueError("РРґРµРЅС‚РёС„РёРєР°С‚РѕСЂ РІР»РѕР¶РµРЅРЅРѕРіРѕ СЌР»РµРјРµРЅС‚Р° РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј.")
        kind = TaskAttachmentData.normalize_kind(kind)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        return TaskAttachmentData.from_row(row)

    def delete_task_attachment(self, attachment_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ РІР»РѕР¶РµРЅРёРµ Р·Р°РґР°С‡Рё."""
        with self._conn:
            self._conn.execute("DELETE FROM task_attachments WHERE id = ?;", (attachment_id,))

    def fetch_projects(self) -> List[ProjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РїСЂРѕРµРєС‚РѕРІ."""
        rows = self._conn.execute(
            """
            SELECT
                id, area, title, updated, priority, archived,
                parent_project_id, default_task_priority, force_recurrence_kind,
                linked_map_id, linked_note_id, linked_object_id,
                marker_color, marker_theme,
                COALESCE(sort_order, 0) AS sort_order
            FROM projects
            ORDER BY parent_project_id, sort_order, id;
            """
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
                    parent_project_id=row["parent_project_id"],
                    default_task_priority=row["default_task_priority"] or "",
                    force_recurrence_kind=(row["force_recurrence_kind"] or "").strip().lower(),
                    linked_map_id=row["linked_map_id"],
                    linked_note_id=row["linked_note_id"],
                    linked_object_id=row["linked_object_id"],
                    sort_order=int(row["sort_order"] or 0),
                    marker_color=(row["marker_color"] or "").strip(),
                    marker_theme=(row["marker_theme"] or "").strip(),
                )
            )
        return projects

    def create_project(
        self,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool = False,
        parent_project_id: Optional[int] = None,
        sort_order: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
    ) -> ProjectData:
        """РЎРѕР·РґР°РµС‚ РїСЂРѕРµРєС‚ РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…."""
        area = validate_area(area)
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РїСЂРѕРµРєС‚Р°")
        priority = normalize_priority(priority)
        default_task_priority = normalize_priority(default_task_priority) if default_task_priority else ""
        force_recurrence_kind = (force_recurrence_kind or "").strip().lower()
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if force_recurrence_kind not in {"", "daily", "weekly", "monthly"}:
            raise ValueError("РќРµРєРѕСЂСЂРµРєС‚РЅР°СЏ РїРµСЂРёРѕРґРёС‡РЅРѕСЃС‚СЊ РїСЂРѕРµРєС‚Р°.")
        if not isinstance(updated, date):
            raise ValueError("Р”Р°С‚Р° РїСЂРѕРµРєС‚Р° РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")

        if sort_order is None:
            sort_order = self._next_project_sort_order(parent_project_id)
        sort_order = max(0, int(sort_order))

        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO projects (
                    area, title, updated, priority, archived,
                    parent_project_id, sort_order, default_task_priority, force_recurrence_kind,
                    linked_map_id, linked_note_id, linked_object_id, marker_color, marker_theme
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    area,
                    title,
                    updated.isoformat(),
                    priority,
                    int(archived),
                    parent_project_id,
                    sort_order,
                    default_task_priority,
                    force_recurrence_kind,
                    linked_map_id,
                    linked_note_id,
                    linked_object_id,
                    marker_color,
                    marker_theme,
                ),
            )
        return ProjectData(
            cur.lastrowid,
            area,
            title,
            updated,
            priority,
            bool(archived),
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            sort_order=sort_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
        )


    def update_project(
        self,
        project_id: int,
        area: str,
        title: str,
        updated: date,
        priority: str,
        archived: bool,
        parent_project_id: Optional[int] = None,
        sort_order: Optional[int] = None,
        default_task_priority: str = "",
        force_recurrence_kind: str = "",
        linked_map_id: Optional[int] = None,
        linked_note_id: Optional[int] = None,
        linked_object_id: Optional[int] = None,
        marker_color: str = "",
        marker_theme: str = "",
    ) -> ProjectData:
        """РћР±РЅРѕРІР»СЏРµС‚ РґР°РЅРЅС‹Рµ РїСЂРѕРµРєС‚Р°."""
        area = validate_area(area)
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РїСЂРѕРµРєС‚Р°")
        priority = normalize_priority(priority)
        default_task_priority = normalize_priority(default_task_priority) if default_task_priority else ""
        force_recurrence_kind = (force_recurrence_kind or "").strip().lower()
        marker_color = (marker_color or "").strip()
        marker_theme = (marker_theme or "").strip().lower()
        if force_recurrence_kind not in {"", "daily", "weekly", "monthly"}:
            raise ValueError("РќРµРєРѕСЂСЂРµРєС‚РЅР°СЏ РїРµСЂРёРѕРґРёС‡РЅРѕСЃС‚СЊ РїСЂРѕРµРєС‚Р°.")
        if not isinstance(updated, date):
            raise ValueError("Р”Р°С‚Р° РїСЂРѕРµРєС‚Р° РЅРµРєРѕСЂСЂРµРєС‚РЅР°.")
        current_row = self._conn.execute(
            "SELECT parent_project_id, COALESCE(sort_order, 0) AS sort_order FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        if parent_project_id == project_id:
            parent_project_id = None
        if parent_project_id is not None:
            cursor = parent_project_id
            seen: set[int] = set()
            while cursor is not None and cursor not in seen:
                if cursor == project_id:
                    raise ValueError("Р¦РёРєР»РёС‡РµСЃРєР°СЏ СЃРІСЏР·СЊ РїСЂРѕРµРєС‚РѕРІ РЅРµ РґРѕРїСѓСЃРєР°РµС‚СЃСЏ.")
                seen.add(cursor)
                row = self._conn.execute(
                    "SELECT parent_project_id FROM projects WHERE id = ?;",
                    (cursor,),
                ).fetchone()
                cursor = row["parent_project_id"] if row is not None else None
        if sort_order is None:
            if current_row is None:
                sort_order = 0
            elif current_row["parent_project_id"] == parent_project_id:
                sort_order = int(current_row["sort_order"] or 0)
            else:
                sort_order = self._next_project_sort_order(parent_project_id, exclude_id=project_id)
        sort_order = max(0, int(sort_order))

        with self._conn:
            self._conn.execute(
                """
                UPDATE projects
                SET area = ?, title = ?, updated = ?, priority = ?, archived = ?,
                    parent_project_id = ?, sort_order = ?, default_task_priority = ?, force_recurrence_kind = ?,
                    linked_map_id = ?, linked_note_id = ?, linked_object_id = ?, marker_color = ?, marker_theme = ?
                WHERE id = ?;
                """,
                (
                    area,
                    title,
                    updated.isoformat(),
                    priority,
                    int(archived),
                    parent_project_id,
                    sort_order,
                    default_task_priority,
                    force_recurrence_kind,
                    linked_map_id,
                    linked_note_id,
                    linked_object_id,
                    marker_color,
                    marker_theme,
                    project_id,
                ),
            )
        return ProjectData(
            project_id,
            area,
            title,
            updated,
            priority,
            bool(archived),
            parent_project_id=parent_project_id,
            default_task_priority=default_task_priority,
            force_recurrence_kind=force_recurrence_kind,
            linked_map_id=linked_map_id,
            linked_note_id=linked_note_id,
            linked_object_id=linked_object_id,
            sort_order=sort_order,
            marker_color=marker_color,
            marker_theme=marker_theme,
        )

    def fetch_project_tree(self) -> List[ProjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСЂРѕРµРєС‚С‹ РІ РїРѕСЂСЏРґРєРµ РѕР±С…РѕРґР° РїРѕ parent/sort_order."""
        return self.fetch_projects()

    def fetch_project_children(self, parent_project_id: Optional[int]) -> List[ProjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РґРѕС‡РµСЂРЅРёРµ РїСЂРѕРµРєС‚С‹ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ СЂРѕРґРёС‚РµР»СЏ."""
        rows = self._conn.execute(
            """
            SELECT
                id, area, title, updated, priority, archived,
                parent_project_id, default_task_priority, force_recurrence_kind,
                linked_map_id, linked_note_id, linked_object_id,
                marker_color, marker_theme,
                COALESCE(sort_order, 0) AS sort_order
            FROM projects
            WHERE parent_project_id IS ?
            ORDER BY sort_order, id;
            """,
            (parent_project_id,),
        ).fetchall()
        children: List[ProjectData] = []
        for row in rows:
            children.append(
                ProjectData(
                    id=row["id"],
                    area=row["area"],
                    title=row["title"],
                    updated=date.fromisoformat(row["updated"]),
                    priority=row["priority"],
                    archived=bool(row["archived"]),
                    parent_project_id=row["parent_project_id"],
                    default_task_priority=row["default_task_priority"] or "",
                    force_recurrence_kind=(row["force_recurrence_kind"] or "").strip().lower(),
                    linked_map_id=row["linked_map_id"],
                    linked_note_id=row["linked_note_id"],
                    linked_object_id=row["linked_object_id"],
                    sort_order=int(row["sort_order"] or 0),
                    marker_color=(row["marker_color"] or "").strip(),
                    marker_theme=(row["marker_theme"] or "").strip(),
                )
            )
        return children

    def _reindex_project_group(self, parent_project_id: Optional[int]) -> None:
        """РџРµСЂРµСЃРѕР±РёСЂР°РµС‚ РЅРµРїСЂРµСЂС‹РІРЅС‹Р№ sort_order РґР»СЏ РіСЂСѓРїРїС‹ РґРѕС‡РµСЂРЅРёС… РїСЂРѕРµРєС‚РѕРІ."""
        rows = self._conn.execute(
            """
            SELECT id
            FROM projects
            WHERE parent_project_id IS ?
            ORDER BY COALESCE(sort_order, 0), id;
            """,
            (parent_project_id,),
        ).fetchall()
        for idx, row in enumerate(rows):
            self._conn.execute(
                "UPDATE projects SET sort_order = ? WHERE id = ?;",
                (idx, row["id"]),
            )

    def move_project(self, project_id: int, new_parent_project_id: Optional[int], new_sort_order: Optional[int] = None) -> None:
        """РџРµСЂРµРјРµС‰Р°РµС‚ РїСЂРѕРµРєС‚ РІ РЅРѕРІСѓСЋ РІРµС‚РєСѓ Рё/РёР»Рё РїРѕР·РёС†РёСЋ СЃСЂРµРґРё siblings."""
        if new_parent_project_id == project_id:
            raise ValueError("Р¦РёРєР»РёС‡РµСЃРєР°СЏ СЃРІСЏР·СЊ РїСЂРѕРµРєС‚РѕРІ РЅРµ РґРѕРїСѓСЃРєР°РµС‚СЃСЏ.")

        row = self._conn.execute(
            """
            SELECT parent_project_id, COALESCE(sort_order, 0) AS sort_order
            FROM projects
            WHERE id = ?;
            """,
            (project_id,),
        ).fetchone()
        if row is None:
            raise ValueError("РџСЂРѕРµРєС‚ РЅРµ РЅР°Р№РґРµРЅ.")
        old_parent = row["parent_project_id"]

        if new_parent_project_id is not None:
            cursor = new_parent_project_id
            seen: set[int] = set()
            while cursor is not None and cursor not in seen:
                if cursor == project_id:
                    raise ValueError("Р¦РёРєР»РёС‡РµСЃРєР°СЏ СЃРІСЏР·СЊ РїСЂРѕРµРєС‚РѕРІ РЅРµ РґРѕРїСѓСЃРєР°РµС‚СЃСЏ.")
                seen.add(cursor)
                parent_row = self._conn.execute(
                    "SELECT parent_project_id FROM projects WHERE id = ?;",
                    (cursor,),
                ).fetchone()
                if parent_row is None:
                    raise ValueError("РќРѕРІС‹Р№ СЂРѕРґРёС‚РµР»СЊСЃРєРёР№ РїСЂРѕРµРєС‚ РЅРµ РЅР°Р№РґРµРЅ.")
                cursor = parent_row["parent_project_id"]

        siblings_count_row = self._conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM projects
            WHERE parent_project_id IS ?
              AND id != ?;
            """,
            (new_parent_project_id, project_id),
        ).fetchone()
        siblings_count = int(siblings_count_row["cnt"] if siblings_count_row is not None else 0)
        if new_sort_order is None:
            new_sort_order = siblings_count
        else:
            new_sort_order = max(0, min(int(new_sort_order), siblings_count))

        with self._conn:
            self._conn.execute(
                """
                UPDATE projects
                SET parent_project_id = ?, sort_order = ?
                WHERE id = ?;
                """,
                (new_parent_project_id, new_sort_order, project_id),
            )
            self._reindex_project_group(old_parent)
            self._reindex_project_group(new_parent_project_id)

    def reorder_project(self, project_id: int, new_sort_order: int) -> None:
        """РњРµРЅСЏРµС‚ РїРѕСЂСЏРґРѕРє РїСЂРѕРµРєС‚Р° СЃСЂРµРґРё siblings Р±РµР· СЃРјРµРЅС‹ СЂРѕРґРёС‚РµР»СЏ."""
        row = self._conn.execute(
            "SELECT parent_project_id FROM projects WHERE id = ?;",
            (project_id,),
        ).fetchone()
        if row is None:
            raise ValueError("РџСЂРѕРµРєС‚ РЅРµ РЅР°Р№РґРµРЅ.")
        parent_project_id = row["parent_project_id"]
        self.move_project(project_id, parent_project_id, new_sort_order=new_sort_order)

    def delete_project(self, project_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ РїСЂРѕРµРєС‚ РїРѕ id."""
        with self._conn:
            self._conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))

    def set_project_archived(self, project_id: int, archived: bool) -> None:
        """РћР±РЅРѕРІР»СЏРµС‚ СЃС‚Р°С‚СѓСЃ Р°СЂС…РёРІРёСЂРѕРІР°РЅРёСЏ РїСЂРѕРµРєС‚Р°."""
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET archived = ? WHERE id = ?;",
                (int(archived), project_id),
            )

    def set_projects_archived_for_area(self, area: str, archived: bool) -> None:
        """РђСЂС…РёРІРёСЂСѓРµС‚ РІСЃРµ РїСЂРѕРµРєС‚С‹ РІ РѕР±Р»Р°СЃС‚Рё."""
        area = validate_area(area)
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET archived = ? WHERE area = ?;",
                (int(archived), area),
            )

    def delete_projects_by_area(self, area: str) -> None:
        """РЈРґР°Р»СЏРµС‚ РІСЃРµ РїСЂРѕРµРєС‚С‹ РІ РѕР±Р»Р°СЃС‚Рё."""
        area = validate_area(area)
        with self._conn:
            self._conn.execute("DELETE FROM projects WHERE area = ?;", (area,))

    def rename_project_area(self, area: str, new_area: str) -> None:
        """РџРµСЂРµРёРјРµРЅРѕРІС‹РІР°РµС‚ РѕР±Р»Р°СЃС‚СЊ РїСЂРѕРµРєС‚РѕРІ."""
        area = validate_area(area)
        new_area = validate_area(new_area)
        with self._conn:
            self._conn.execute(
                "UPDATE projects SET area = ? WHERE area = ?;",
                (new_area, area),
            )

    def project_areas(self) -> List[str]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РѕС‚СЃРѕСЂС‚РёСЂРѕРІР°РЅРЅС‹Р№ СЃРїРёСЃРѕРє РѕР±Р»Р°СЃС‚РµР№ РїСЂРѕРµРєС‚Р°."""
        rows = self._conn.execute("SELECT DISTINCT area FROM projects ORDER BY area;").fetchall()
        return [row["area"] for row in rows]

    def fetch_maps(self) -> List[MapData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РєР°СЂС‚."""
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
        """РЎРѕР·РґР°РµС‚ РєР°СЂС‚Сѓ."""
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РєР°СЂС‚С‹")
        description = (description or "").strip()
        project = (project or "").strip()
        tiles_path = (tiles_path or "").strip()
        if tiles_h <= 0 or tiles_w <= 0:
            raise ValueError("Р Р°Р·РјРµСЂ СЃРµС‚РєРё РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ Р±РѕР»СЊС€Рµ РЅСѓР»СЏ.")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РћР±РЅРѕРІР»СЏРµС‚ СЃРІРѕР№СЃС‚РІР° РєР°СЂС‚С‹."""
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РєР°СЂС‚С‹")
        description = (description or "").strip()
        project = (project or "").strip()
        tiles_path = (tiles_path or "").strip()
        if tiles_h <= 0 or tiles_w <= 0:
            raise ValueError("Р Р°Р·РјРµСЂ СЃРµС‚РєРё РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ Р±РѕР»СЊС€Рµ РЅСѓР»СЏ.")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РјРµС‚РѕРє РєР°СЂС‚С‹."""
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
        """РЎРѕР·РґР°РµС‚ РёР»Рё РѕР±РЅРѕРІР»СЏРµС‚ РјРµС‚РєСѓ РєР°СЂС‚С‹."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РЈРґР°Р»СЏРµС‚ РјРµС‚РєСѓ РєР°СЂС‚С‹."""
        with self._conn:
            self._conn.execute("DELETE FROM map_markers WHERE id = ?;", (marker_id,))

    def fetch_map_overlays(self, map_id: Optional[int] = None) -> List[MapOverlayData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РіРµРѕРјРµС‚СЂРёР№ РєР°СЂС‚С‹ (РѕР±Р»Р°СЃС‚Рё/РїСѓС‚Рё)."""
        if map_id is None:
            rows = self._conn.execute(
                """
                SELECT id, map_id, kind, points, color, title, created_at, updated_at
                FROM map_overlays;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, map_id, kind, points, color, title, created_at, updated_at
                FROM map_overlays
                WHERE map_id = ?;
                """,
                (map_id,),
            ).fetchall()
        overlays: List[MapOverlayData] = []
        for row in rows:
            parsed = []
            try:
                raw_points = json.loads(row["points"] or "[]")
            except json.JSONDecodeError:
                raw_points = []
            for pair in raw_points:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    continue
                try:
                    parsed.append((float(pair[0]), float(pair[1])))
                except (TypeError, ValueError):
                    continue
            overlays.append(
                MapOverlayData(
                    id=row["id"],
                    map_id=row["map_id"],
                    kind=row["kind"],
                    points=parsed,
                    color=row["color"] or "#6cb5ff",
                    title=row["title"] or "",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return overlays

    def create_map_overlay(
        self,
        map_id: int,
        kind: str,
        points: List[Tuple[float, float]],
        color: str,
        title: str = "",
    ) -> MapOverlayData:
        """РЎРѕР·РґР°РµС‚ РіРµРѕРјРµС‚СЂРёСЋ РєР°СЂС‚С‹ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ СЃРѕС…СЂР°РЅРµРЅРЅСѓСЋ Р·Р°РїРёСЃСЊ."""
        overlay_kind = (kind or "").strip().lower()
        if overlay_kind not in {"region", "path"}:
            raise ValueError("РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С‚РёРї РіРµРѕРјРµС‚СЂРёРё РєР°СЂС‚С‹.")
        normalized: List[Tuple[float, float]] = []
        for pair in points or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                normalized.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                continue
        min_points = 3 if overlay_kind == "region" else 2
        if len(normalized) < min_points:
            raise ValueError("РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ С‚РѕС‡РµРє РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ РіРµРѕРјРµС‚СЂРёРё.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        color_value = (color or "").strip() or "#6cb5ff"
        title_value = (title or "").strip()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO map_overlays (map_id, kind, points, color, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    map_id,
                    overlay_kind,
                    json.dumps([[x, y] for x, y in normalized], ensure_ascii=False),
                    color_value,
                    title_value,
                    now,
                    now,
                ),
            )
        return MapOverlayData(
            id=cur.lastrowid,
            map_id=map_id,
            kind=overlay_kind,
            points=normalized,
            color=color_value,
            title=title_value,
            created_at=now,
            updated_at=now,
        )

    def update_map_overlay(
        self,
        overlay_id: int,
        kind: str,
        points: List[Tuple[float, float]],
        color: str,
        title: str = "",
    ) -> MapOverlayData:
        """РћР±РЅРѕРІР»СЏРµС‚ РіРµРѕРјРµС‚СЂРёСЋ РєР°СЂС‚С‹ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ Р°РєС‚СѓР°Р»СЊРЅСѓСЋ Р·Р°РїРёСЃСЊ."""
        overlay_kind = (kind or "").strip().lower()
        if overlay_kind not in {"region", "path"}:
            raise ValueError("РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С‚РёРї РіРµРѕРјРµС‚СЂРёРё РєР°СЂС‚С‹.")
        normalized: List[Tuple[float, float]] = []
        for pair in points or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                normalized.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                continue
        min_points = 3 if overlay_kind == "region" else 2
        if len(normalized) < min_points:
            raise ValueError("РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ С‚РѕС‡РµРє РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ РіРµРѕРјРµС‚СЂРёРё.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        color_value = (color or "").strip() or "#6cb5ff"
        title_value = (title or "").strip()
        with self._conn:
            self._conn.execute(
                """
                UPDATE map_overlays
                SET kind = ?, points = ?, color = ?, title = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    overlay_kind,
                    json.dumps([[x, y] for x, y in normalized], ensure_ascii=False),
                    color_value,
                    title_value,
                    now,
                    overlay_id,
                ),
            )
        row = self._conn.execute(
            """
            SELECT id, map_id, kind, points, color, title, created_at, updated_at
            FROM map_overlays
            WHERE id = ?;
            """,
            (overlay_id,),
        ).fetchone()
        if not row:
            raise ValueError("Р“РµРѕРјРµС‚СЂРёСЏ РєР°СЂС‚С‹ РЅРµ РЅР°Р№РґРµРЅР°.")
        parsed = []
        try:
            raw_points = json.loads(row["points"] or "[]")
        except json.JSONDecodeError:
            raw_points = []
        for pair in raw_points:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                parsed.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                continue
        return MapOverlayData(
            id=row["id"],
            map_id=row["map_id"],
            kind=row["kind"],
            points=parsed,
            color=row["color"] or "#6cb5ff",
            title=row["title"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete_map_overlay(self, overlay_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ РіРµРѕРјРµС‚СЂРёСЋ РєР°СЂС‚С‹."""
        with self._conn:
            self._conn.execute("DELETE FROM map_overlays WHERE id = ?;", (overlay_id,))

    def fetch_notes(self) -> List[NoteData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… Р·Р°РјРµС‚РѕРє."""
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
        """РЎРѕР·РґР°РµС‚ Р·Р°РјРµС‚РєСѓ РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…."""
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ Р·Р°РјРµС‚РєРё")
        preview = (preview or "").strip()
        project = (project or "").strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РћР±РЅРѕРІР»СЏРµС‚ РґР°РЅРЅС‹Рµ Р·Р°РјРµС‚РєРё."""
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ Р·Р°РјРµС‚РєРё")
        preview = (preview or "").strip()
        tags = [tag.strip() for tag in tags if tag.strip()]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РёРґРµР№ СЃ СѓС‡РµС‚РѕРј С„РёР»СЊС‚СЂРѕРІ."""
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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РёРґРµСЋ РїРѕ ID."""
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
        """РЎРѕР·РґР°РµС‚ РёРґРµСЋ РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…."""
        title = (title or "").strip() or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ"
        summary = (summary or "").strip()
        body_md = (body_md or "").strip()
        idea_type = (idea_type or "other").strip() or "other"
        status = (status or "inbox").strip() or "inbox"
        value_score = int(value_score or 3)
        effort_score = int(effort_score or 3)
        source = (source or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РћР±РЅРѕРІР»СЏРµС‚ РёРґРµСЋ."""
        title = (title or "").strip() or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ"
        summary = (summary or "").strip()
        body_md = (body_md or "").strip()
        idea_type = (idea_type or "other").strip() or "other"
        status = (status or "inbox").strip() or "inbox"
        value_score = int(value_score or 3)
        effort_score = int(effort_score or 3)
        source = (source or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РђСЂС…РёРІРёСЂСѓРµС‚ РёР»Рё РІРѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ РёРґРµСЋ."""
        archived_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if archived else None
        with self._conn:
            self._conn.execute(
                "UPDATE ideas SET archived_at = ?, updated_at = ? WHERE id = ?;",
                (archived_at, datetime.now(timezone.utc).isoformat(timespec="seconds"), idea_id),
            )

    def delete_idea(self, idea_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ РёРґРµСЋ."""
        with self._conn:
            self._conn.execute("DELETE FROM ideas WHERE id = ?;", (idea_id,))

    def fetch_idea_relations(self, idea_id: int) -> List[IdeaRelationData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє СЃРІСЏР·РµР№ РёРґРµРё."""
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
        """РЎРѕР·РґР°РµС‚ СЃРІСЏР·СЊ РёРґРµРё СЃ СЃСѓС‰РЅРѕСЃС‚СЊСЋ."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO idea_relations (idea_id, entity_type, entity_id, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (idea_id, entity_type, entity_id, now),
            )

    def toggle_note_favorite(self, note_id: int) -> NoteData:
        """РџРµСЂРµРєР»СЋС‡Р°РµС‚ РёР·Р±СЂР°РЅРЅРѕРµ Сѓ Р·Р°РјРµС‚РєРё."""
        row = self._conn.execute(
            """
            SELECT title, preview, tags, project, favorite, attachment, locked
            FROM notes
            WHERE id = ?;
            """,
            (note_id,),
        ).fetchone()
        if not row:
            raise ValueError("Р—Р°РјРµС‚РєР° РЅРµ РЅР°Р№РґРµРЅР°.")
        favorite = not bool(row["favorite"])
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РЈРґР°Р»СЏРµС‚ Р·Р°РјРµС‚РєСѓ."""
        with self._conn:
            self._conn.execute("DELETE FROM notes WHERE id = ?;", (note_id,))

    def fetch_objects(self) -> List[ObjectData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹С… РѕР±СЉРµРєС‚РѕРІ."""
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
        """РЎРѕР·РґР°РµС‚ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РѕР±СЉРµРєС‚."""
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РѕР±СЉРµРєС‚Р°")
        catalog = (catalog or "").strip()
        object_type = (object_type or "").strip()
        status = (status or "").strip()
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РћР±РЅРѕРІР»СЏРµС‚ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РѕР±СЉРµРєС‚."""
        title = validate_title(title, field_name="РќР°Р·РІР°РЅРёРµ РѕР±СЉРµРєС‚Р°")
        catalog = (catalog or "").strip()
        object_type = (object_type or "").strip()
        status = (status or "").strip()
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РЈРґР°Р»СЏРµС‚ Р°СЂС…РёС‚РµРєС‚СѓСЂРЅС‹Р№ РѕР±СЉРµРєС‚."""
        with self._conn:
            self._conn.execute("DELETE FROM objects WHERE id = ?;", (object_id,))

    def create_object_from_folder_path(self, folder_path: str) -> ObjectData:
        """РЎРѕР·РґР°РµС‚ РѕР±СЉРµРєС‚ РЅР° РѕСЃРЅРѕРІРµ РїСѓС‚Рё Рє РїР°РїРєРµ."""
        path = (folder_path or "").strip().strip("/")
        if not path:
            raise ValueError("РџСѓС‚СЊ Рє РїР°РїРєРµ РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        parts = [part for part in path.split("/") if part]
        title = parts[-1] if parts else "РќРѕРІС‹Р№ РѕР±СЉРµРєС‚"
        catalog = " / ".join(parts[:-1])
        description = f"РћР±СЉРµРєС‚ СЃРѕР·РґР°РЅ РёР· РїР°РїРєРё: {path}"
        return self.create_object(title, catalog, "", "", description)

    def fetch_object_images(self, object_id: int) -> List[ObjectImageData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РёР·РѕР±СЂР°Р¶РµРЅРёР№ РѕР±СЉРµРєС‚Р°."""
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
        """Р”РѕР±Р°РІР»СЏРµС‚ РёР·РѕР±СЂР°Р¶РµРЅРёРµ Рє РѕР±СЉРµРєС‚Сѓ."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("РџСѓС‚СЊ Рє РёР·РѕР±СЂР°Р¶РµРЅРёСЋ РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РћР±РЅРѕРІР»СЏРµС‚ РѕРїРёСЃР°РЅРёРµ РёР·РѕР±СЂР°Р¶РµРЅРёСЏ РѕР±СЉРµРєС‚Р°."""
        description = (description or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
        """РЈРґР°Р»СЏРµС‚ РёР·РѕР±СЂР°Р¶РµРЅРёРµ РѕР±СЉРµРєС‚Р°."""
        with self._conn:
            self._conn.execute("DELETE FROM object_images WHERE id = ?;", (image_id,))

    @staticmethod
    def _normalize_collection_entity_type(entity_type: str) -> str:
        value = (entity_type or "").strip().lower() or "other"
        if value not in COLLECTION_ENTITY_TYPES:
            raise ValueError(
                "РўРёРї РєРѕР»Р»РµРєС†РёРё РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РѕРґРЅРёРј РёР·: building, city, film, game, character, other."
            )
        return value

    def fetch_collection_items(
        self,
        search_text: str = "",
        topic: Optional[str] = None,
        entity_type: Optional[str] = None,
        category_ids: Optional[Iterable[int]] = None,
    ) -> List[CollectionItemData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЌР»РµРјРµРЅС‚С‹ СЂРµР¶РёРјР° РєРѕР»Р»РµРєС†РёР№."""
        clauses: list[str] = []
        params: list[object] = []
        search_text = (search_text or "").strip().lower()
        topic = (topic or "").strip()
        if search_text:
            clauses.append(
                "(lower(title) LIKE ? OR lower(topic) LIKE ? OR lower(description) LIKE ? OR lower(source_url) LIKE ?)"
            )
            like = f"%{search_text}%"
            params.extend([like, like, like, like])
        if topic:
            clauses.append("topic = ?")
            params.append(topic)
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(self._normalize_collection_entity_type(entity_type))
        if category_ids is not None:
            category_list = [int(value) for value in category_ids if value is not None]
            if not category_list:
                return []
            placeholders = ", ".join("?" for _ in category_list)
            clauses.append(f"category_id IN ({placeholders})")
            params.extend(category_list)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT id, title, category_id, entity_type, topic, image_url, source_url, description,
                   source_folder_path, import_options_json, created_at, updated_at
            FROM collection_items
            {where_sql}
            ORDER BY updated_at DESC, title COLLATE NOCASE ASC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [
            CollectionItemData(
                row["id"],
                row["title"],
                row["category_id"],
                row["entity_type"],
                row["topic"] or "",
                row["image_url"] or "",
                row["source_url"] or "",
                row["description"] or "",
                row["source_folder_path"] or "",
                row["import_options_json"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def fetch_collection_source_folders(self) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT id, title, source_folder_path
            FROM collection_items
            WHERE trim(source_folder_path) <> '';
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_collection_topics(self) -> List[str]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє С‚РµРј РєРѕР»Р»РµРєС†РёР№."""
        rows = self._conn.execute(
            """
            SELECT DISTINCT topic
            FROM collection_items
            WHERE trim(topic) <> ''
            ORDER BY topic COLLATE NOCASE ASC;
            """
        ).fetchall()
        return [row["topic"] for row in rows]

    def create_collection_item(
        self,
        *,
        title: str,
        entity_type: str,
        category_id: Optional[int] = None,
        topic: str = "",
        image_url: str = "",
        source_url: str = "",
        description: str = "",
        source_folder_path: str = "",
        import_options_json: str = "",
    ) -> CollectionItemData:
        """РЎРѕР·РґР°РµС‚ СЌР»РµРјРµРЅС‚ РєРѕР»Р»РµРєС†РёРё."""
        title = validate_title(title)
        entity_type = self._normalize_collection_entity_type(entity_type)
        topic = (topic or "").strip()
        image_url = (image_url or "").strip()
        source_url = (source_url or "").strip()
        description = (description or "").strip()
        source_folder_path = (source_folder_path or "").strip()
        import_options_json = (import_options_json or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO collection_items
                (title, category_id, entity_type, topic, image_url, source_url, description,
                 source_folder_path, import_options_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    title,
                    category_id,
                    entity_type,
                    topic,
                    image_url,
                    source_url,
                    description,
                    source_folder_path,
                    import_options_json,
                    now,
                    now,
                ),
            )
        return CollectionItemData(
            cur.lastrowid,
            title,
            category_id,
            entity_type,
            topic,
            image_url,
            source_url,
            description,
            source_folder_path,
            import_options_json,
            now,
            now,
        )

    def update_collection_item(
        self,
        item_id: int,
        *,
        title: str,
        entity_type: str,
        category_id: Optional[int] = None,
        topic: str = "",
        image_url: str = "",
        source_url: str = "",
        description: str = "",
        source_folder_path: Optional[str] = None,
        import_options_json: Optional[str] = None,
    ) -> CollectionItemData:
        """РћР±РЅРѕРІР»СЏРµС‚ СЌР»РµРјРµРЅС‚ РєРѕР»Р»РµРєС†РёРё."""
        title = validate_title(title)
        entity_type = self._normalize_collection_entity_type(entity_type)
        topic = (topic or "").strip()
        image_url = (image_url or "").strip()
        source_url = (source_url or "").strip()
        description = (description or "").strip()
        if source_folder_path is None or import_options_json is None:
            existing = self._conn.execute(
                """
                SELECT source_folder_path, import_options_json
                FROM collection_items
                WHERE id = ?;
                """,
                (item_id,),
            ).fetchone()
            if existing is None:
                raise ValueError("Р В­Р В»Р ВµР СР ВµР Р…РЎвЂљ Р С”Р С•Р В»Р В»Р ВµР С”РЎвЂ Р С‘Р С‘ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р….")
            if source_folder_path is None:
                source_folder_path = existing["source_folder_path"] or ""
            if import_options_json is None:
                import_options_json = existing["import_options_json"] or ""
        source_folder_path = (source_folder_path or "").strip()
        import_options_json = (import_options_json or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE collection_items
                SET title = ?, category_id = ?, entity_type = ?, topic = ?, image_url = ?, source_url = ?,
                    description = ?, source_folder_path = ?, import_options_json = ?, updated_at = ?
                WHERE id = ?;
                """,
                (
                    title,
                    category_id,
                    entity_type,
                    topic,
                    image_url,
                    source_url,
                    description,
                    source_folder_path,
                    import_options_json,
                    now,
                    item_id,
                ),
            )
        row = self._conn.execute(
            """
            SELECT id, title, category_id, entity_type, topic, image_url, source_url, description,
                   source_folder_path, import_options_json, created_at, updated_at
            FROM collection_items
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р­Р»РµРјРµРЅС‚ РєРѕР»Р»РµРєС†РёРё РЅРµ РЅР°Р№РґРµРЅ.")
        return CollectionItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["entity_type"],
            row["topic"] or "",
            row["image_url"] or "",
            row["source_url"] or "",
            row["description"] or "",
            row["source_folder_path"] or "",
            row["import_options_json"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def delete_collection_item(self, item_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ СЌР»РµРјРµРЅС‚ РєРѕР»Р»РµРєС†РёРё."""
        with self._conn:
            self._conn.execute("DELETE FROM collection_items WHERE id = ?;", (item_id,))

    def create_collection_category(
        self,
        title: str,
        parent_id: Optional[int] = None,
        sort_index: int = 0,
    ) -> CollectionCategoryData:
        title = validate_title(title, field_name="Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO collection_category (title, parent_id, sort_index, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (title, parent_id, int(sort_index), now, now),
            )
        return CollectionCategoryData(cur.lastrowid, title, parent_id, int(sort_index), now, now)

    def fetch_collection_categories(self) -> List[CollectionCategoryData]:
        rows = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            ORDER BY sort_index ASC, title COLLATE NOCASE ASC, id ASC;
            """
        ).fetchall()
        return [
            CollectionCategoryData(
                row["id"],
                row["title"],
                row["parent_id"],
                row["sort_index"] or 0,
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def list_collection_category_tree(self) -> List[CollectionCategoryData]:
        return self.fetch_collection_categories()

    def ensure_collection_category_path(
        self,
        path: str,
        base_parent_id: Optional[int] = None,
    ) -> Optional[int]:
        parts = [part.strip() for part in (path or "").split("/") if part.strip()]
        if not parts:
            return base_parent_id
        parent_id = base_parent_id
        for title in parts:
            if parent_id is None:
                row = self._conn.execute(
                    """
                    SELECT id
                    FROM collection_category
                    WHERE title = ? AND parent_id IS NULL;
                    """,
                    (title,),
                ).fetchone()
            else:
                row = self._conn.execute(
                    """
                    SELECT id
                    FROM collection_category
                    WHERE title = ? AND parent_id = ?;
                    """,
                    (title, parent_id),
                ).fetchone()
            if row is None:
                category = self.create_collection_category(title, parent_id=parent_id)
                parent_id = category.id
            else:
                parent_id = row["id"]
        return parent_id

    def get_collection_category(self, category_id: int) -> Optional[CollectionCategoryData]:
        row = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return CollectionCategoryData(
            row["id"],
            row["title"],
            row["parent_id"],
            row["sort_index"] or 0,
            row["created_at"],
            row["updated_at"],
        )

    def update_collection_category_title(self, category_id: int, title: str) -> CollectionCategoryData:
        title = validate_title(title, field_name="Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE collection_category
                SET title = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, now, category_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…Р В°.")
        return CollectionCategoryData(
            row["id"],
            row["title"],
            row["parent_id"],
            row["sort_index"] or 0,
            row["created_at"],
            row["updated_at"],
        )

    def move_collection_category(self, category_id: int, parent_id: Optional[int]) -> CollectionCategoryData:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE collection_category
                SET parent_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (parent_id, now, category_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, parent_id, sort_index, created_at, updated_at
            FROM collection_category
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…Р В°.")
        return CollectionCategoryData(
            row["id"],
            row["title"],
            row["parent_id"],
            row["sort_index"] or 0,
            row["created_at"],
            row["updated_at"],
        )

    def delete_collection_category(
        self,
        category_id: int,
        *,
        move_children_to_root: bool = False,
        move_items_to_root: bool = False,
    ) -> None:
        children_count = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM collection_category WHERE parent_id = ?;",
            (category_id,),
        ).fetchone()["cnt"]
        items_count = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM collection_items WHERE category_id = ?;",
            (category_id,),
        ).fetchone()["cnt"]
        if children_count and not move_children_to_root:
            raise ValueError("РљР°С‚РµРіРѕСЂРёСЏ СЃРѕРґРµСЂР¶РёС‚ РїРѕРґРєР°С‚РµРіРѕСЂРёРё.")
        if items_count and not move_items_to_root:
            raise ValueError("РљР°С‚РµРіРѕСЂРёСЏ СЃРѕРґРµСЂР¶РёС‚ РєРѕР»Р»РµРєС†РёРё.")
        with self._conn:
            if move_children_to_root:
                self._conn.execute(
                    "UPDATE collection_category SET parent_id = NULL WHERE parent_id = ?;",
                    (category_id,),
                )
            if move_items_to_root:
                self._conn.execute(
                    "UPDATE collection_items SET category_id = NULL WHERE category_id = ?;",
                    (category_id,),
                )
            self._conn.execute("DELETE FROM collection_category WHERE id = ?;", (category_id,))

    def fetch_collection_relations(self, item_id: Optional[int] = None) -> List[CollectionRelationData]:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРІСЏР·Рё СЌР»РµРјРµРЅС‚РѕРІ РєРѕР»Р»РµРєС†РёРё."""
        if item_id is None:
            rows = self._conn.execute(
                """
                SELECT id, left_item_id, right_item_id, relation_kind, created_at
                FROM collection_relations
                ORDER BY created_at DESC, id DESC;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, left_item_id, right_item_id, relation_kind, created_at
                FROM collection_relations
                WHERE left_item_id = ? OR right_item_id = ?
                ORDER BY created_at DESC, id DESC;
                """,
                (item_id, item_id),
            ).fetchall()
        return [
            CollectionRelationData(
                row["id"],
                row["left_item_id"],
                row["right_item_id"],
                row["relation_kind"] or "=",
                row["created_at"],
            )
            for row in rows
        ]

    def create_collection_relation(
        self,
        left_item_id: int,
        right_item_id: int,
        relation_kind: str = "=",
    ) -> CollectionRelationData:
        """РЎРѕР·РґР°РµС‚ РїРµСЂРµРєСЂРµСЃС‚РЅСѓСЋ СЃРІСЏР·СЊ РјРµР¶РґСѓ СЌР»РµРјРµРЅС‚Р°РјРё РєРѕР»Р»РµРєС†РёРё."""
        if left_item_id == right_item_id:
            raise ValueError("РќРµР»СЊР·СЏ СЃРІСЏР·Р°С‚СЊ СЌР»РµРјРµРЅС‚ СЃР°Рј СЃ СЃРѕР±РѕР№.")
        left_id, right_id = sorted((int(left_item_id), int(right_item_id)))
        relation_kind = (relation_kind or "=").strip() or "="
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO collection_relations
                (left_item_id, right_item_id, relation_kind, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (left_id, right_id, relation_kind, now),
            )
        row = self._conn.execute(
            """
            SELECT id, left_item_id, right_item_id, relation_kind, created_at
            FROM collection_relations
            WHERE left_item_id = ? AND right_item_id = ? AND relation_kind = ?;
            """,
            (left_id, right_id, relation_kind),
        ).fetchone()
        if row is None:
            raise ValueError("РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР·РґР°С‚СЊ СЃРІСЏР·СЊ РєРѕР»Р»РµРєС†РёРё.")
        return CollectionRelationData(
            row["id"],
            row["left_item_id"],
            row["right_item_id"],
            row["relation_kind"] or "=",
            row["created_at"],
        )

    def delete_collection_relation(self, relation_id: int) -> None:
        """РЈРґР°Р»СЏРµС‚ СЃРІСЏР·СЊ РєРѕР»Р»РµРєС†РёРё."""
        with self._conn:
            self._conn.execute("DELETE FROM collection_relations WHERE id = ?;", (relation_id,))

    def create_collection_entries(
        self,
        collection_id: int,
        entries: Iterable[dict],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = []
        for entry in entries:
            payload.append(
                (
                    collection_id,
                    (entry.get("source_path") or "").strip(),
                    (entry.get("rel_path") or "").strip(),
                    (entry.get("title") or "").strip(),
                    (entry.get("ext") or "").strip(),
                    (entry.get("mime") or "").strip(),
                    int(entry.get("size_bytes") or 0),
                    (entry.get("meta_json") or "").strip(),
                    int(bool(entry.get("is_missing") or 0)),
                    now,
                    now,
                )
            )
        if not payload:
            return
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO collection_item
                (collection_id, source_path, rel_path, title, ext, mime, size_bytes, meta_json, is_missing, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                payload,
            )

    def fetch_collection_entries(self, collection_id: int) -> List[CollectionEntryData]:
        rows = self._conn.execute(
            """
            SELECT id, collection_id, source_path, rel_path, title, ext, mime, size_bytes, meta_json, is_missing,
                   created_at, updated_at
            FROM collection_item
            WHERE collection_id = ?
            ORDER BY rel_path COLLATE NOCASE ASC, id ASC;
            """,
            (collection_id,),
        ).fetchall()
        return [
            CollectionEntryData(
                row["id"],
                row["collection_id"],
                row["source_path"],
                row["rel_path"],
                row["title"],
                row["ext"] or "",
                row["mime"] or "",
                row["size_bytes"] or 0,
                row["meta_json"] or "",
                bool(row["is_missing"]),
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def sync_collection_entries(
        self,
        collection_id: int,
        entries: Iterable[dict],
    ) -> None:
        existing_rows = self._conn.execute(
            """
            SELECT id, rel_path
            FROM collection_item
            WHERE collection_id = ?;
            """,
            (collection_id,),
        ).fetchall()
        existing_by_rel = {row["rel_path"]: row["id"] for row in existing_rows}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        incoming_rel = set()
        with self._conn:
            for entry in entries:
                rel_path = (entry.get("rel_path") or "").strip()
                if not rel_path:
                    continue
                incoming_rel.add(rel_path)
                if rel_path in existing_by_rel:
                    self._conn.execute(
                        """
                        UPDATE collection_item
                        SET source_path = ?, title = ?, ext = ?, mime = ?, size_bytes = ?, meta_json = ?,
                            is_missing = 0, updated_at = ?
                        WHERE id = ?;
                        """,
                        (
                            (entry.get("source_path") or "").strip(),
                            (entry.get("title") or "").strip(),
                            (entry.get("ext") or "").strip(),
                            (entry.get("mime") or "").strip(),
                            int(entry.get("size_bytes") or 0),
                            (entry.get("meta_json") or "").strip(),
                            now,
                            existing_by_rel[rel_path],
                        ),
                    )
                else:
                    self._conn.execute(
                        """
                        INSERT INTO collection_item
                        (collection_id, source_path, rel_path, title, ext, mime, size_bytes, meta_json, is_missing, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
                        """,
                        (
                            collection_id,
                            (entry.get("source_path") or "").strip(),
                            rel_path,
                            (entry.get("title") or "").strip(),
                            (entry.get("ext") or "").strip(),
                            (entry.get("mime") or "").strip(),
                            int(entry.get("size_bytes") or 0),
                            (entry.get("meta_json") or "").strip(),
                            now,
                            now,
                        ),
                    )
            missing_rel = set(existing_by_rel.keys()) - incoming_rel
            for rel_path in missing_rel:
                self._conn.execute(
                    """
                    UPDATE collection_item
                    SET is_missing = 1, updated_at = ?
                    WHERE id = ?;
                    """,
                    (now, existing_by_rel[rel_path]),
                )

    # --- Shop data ---
    def create_shop_category(self, title: str, parent_id: Optional[int] = None) -> ShopCategoryData:
        title = validate_title(title, field_name="РљР°С‚РµРіРѕСЂРёСЏ")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shop_category (title, parent_id)
                VALUES (?, ?);
                """,
                (title, parent_id),
            )
        return ShopCategoryData(cur.lastrowid, title, parent_id)

    def fetch_shop_categories(self) -> List[ShopCategoryData]:
        rows = self._conn.execute(
            """
            SELECT id, title, parent_id
            FROM shop_category
            ORDER BY title COLLATE NOCASE ASC, id ASC;
            """
        ).fetchall()
        return [
            ShopCategoryData(
                row["id"],
                row["title"],
                row["parent_id"],
            )
            for row in rows
        ]

    def get_shop_category(self, category_id: int) -> Optional[ShopCategoryData]:
        row = self._conn.execute(
            "SELECT id, title, parent_id FROM shop_category WHERE id = ?;",
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return ShopCategoryData(row["id"], row["title"], row["parent_id"])

    def update_shop_category_title(self, category_id: int, title: str) -> ShopCategoryData:
        title = validate_title(title, field_name="Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ")
        with self._conn:
            self._conn.execute(
                """
                UPDATE shop_category
                SET title = ?
                WHERE id = ?;
                """,
                (title, category_id),
            )
        row = self._conn.execute(
            "SELECT id, title, parent_id FROM shop_category WHERE id = ?;",
            (category_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р С™Р В°РЎвЂљР ВµР С–Р С•РЎР‚Р С‘РЎРЏ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р…Р В°.")
        return ShopCategoryData(row["id"], row["title"], row["parent_id"])

    def delete_shop_category(self, category_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_category WHERE id = ?;", (category_id,))

    def get_shop_item(self, item_id: int) -> Optional[ShopItemData]:
        row = self._conn.execute(
            """
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ShopItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["user_notes"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def update_shop_item_category(
        self,
        item_id: int,
        category_id: Optional[int],
    ) -> ShopItemData:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE shop_item
                SET category_id = ?, updated_at = ?
                WHERE id = ?;
                """,
                (category_id, now, item_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Р СћР С•Р Р†Р В°РЎР‚ Р Р…Р Вµ Р Р…Р В°Р в„–Р Т‘Р ВµР Р….")
        return ShopItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["user_notes"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def fetch_shop_sources(self, item_id: int) -> List[ShopSourceData]:
        rows = self._conn.execute(
            """
            SELECT id, item_id, shop_code, url, sku, currency, price, in_stock, stock_text, parsed_at, raw_json
            FROM shop_source
            WHERE item_id = ?
            ORDER BY parsed_at DESC, id DESC;
            """,
            (item_id,),
        ).fetchall()
        return [
            ShopSourceData(
                row["id"],
                row["item_id"],
                row["shop_code"] or "",
                row["url"] or "",
                row["sku"] or "",
                row["currency"] or "",
                row["price"],
                bool(row["in_stock"]),
                row["stock_text"] or "",
                row["parsed_at"] or "",
                row["raw_json"] or "",
            )
            for row in rows
        ]

    def fetch_shop_sources_for_items(self, item_ids: List[int]) -> List[ShopSourceData]:
        if not item_ids:
            return []
        placeholders = ",".join("?" for _ in item_ids)
        rows = self._conn.execute(
            f"""
            SELECT id, item_id, shop_code, url, sku, currency, price, in_stock, stock_text, parsed_at, raw_json
            FROM shop_source
            WHERE item_id IN ({placeholders})
            ORDER BY item_id ASC, parsed_at DESC, id DESC;
            """,
            tuple(item_ids),
        ).fetchall()
        return [
            ShopSourceData(
                row["id"],
                row["item_id"],
                row["shop_code"] or "",
                row["url"] or "",
                row["sku"] or "",
                row["currency"] or "",
                row["price"],
                bool(row["in_stock"]),
                row["stock_text"] or "",
                row["parsed_at"] or "",
                row["raw_json"] or "",
            )
            for row in rows
        ]

    def delete_shop_source(self, source_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_source WHERE id = ?;", (source_id,))

    def delete_shop_item(self, item_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_item WHERE id = ?;", (item_id,))

    def fetch_shop_item_properties(self, item_id: int) -> List[ShopItemPropertyData]:
        rows = self._conn.execute(
            """
            SELECT id, item_id, name, value, unit, normalized_key
            FROM shop_item_property
            WHERE item_id = ?
            ORDER BY normalized_key COLLATE NOCASE ASC, id ASC;
            """,
            (item_id,),
        ).fetchall()
        return [
            ShopItemPropertyData(
                row["id"],
                row["item_id"],
                row["name"] or "",
                row["value"] or "",
                row["unit"] or "",
                row["normalized_key"] or "",
            )
            for row in rows
        ]

    def fetch_shop_source_properties(self, source_id: int) -> List[ShopSourcePropertyData]:
        rows = self._conn.execute(
            """
            SELECT id, source_id, name, value, unit, normalized_key
            FROM shop_source_property
            WHERE source_id = ?
            ORDER BY normalized_key COLLATE NOCASE ASC, id ASC;
            """,
            (source_id,),
        ).fetchall()
        return [
            ShopSourcePropertyData(
                row["id"],
                row["source_id"],
                row["name"] or "",
                row["value"] or "",
                row["unit"] or "",
                row["normalized_key"] or "",
            )
            for row in rows
        ]

    def replace_shop_source_properties(
        self,
        source_id: int,
        properties: List[ShopSourcePropertyData],
    ) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_source_property WHERE source_id = ?;", (source_id,))
            for prop in properties:
                self._conn.execute(
                    """
                    INSERT INTO shop_source_property (source_id, name, value, unit, normalized_key)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        source_id,
                        prop.name,
                        prop.value,
                        prop.unit,
                        prop.normalized_key,
                    ),
                )

    def upsert_shop_item_property(
        self,
        *,
        item_id: int,
        name: str,
        value: str,
        unit: str = "",
        normalized_key: str = "",
    ) -> ShopItemPropertyData:
        name = (name or "").strip()
        value = (value or "").strip()
        unit = (unit or "").strip()
        normalized_key = (normalized_key or "").strip()
        with self._conn:
            row = self._conn.execute(
                """
                SELECT id FROM shop_item_property
                WHERE item_id = ? AND normalized_key = ?;
                """,
                (item_id, normalized_key),
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    """
                    INSERT INTO shop_item_property (item_id, name, value, unit, normalized_key)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (item_id, name, value, unit, normalized_key),
                )
                prop_id = cur.lastrowid
            else:
                prop_id = row["id"]
                self._conn.execute(
                    """
                    UPDATE shop_item_property
                    SET name = ?, value = ?, unit = ?, normalized_key = ?
                    WHERE id = ?;
                    """,
                    (name, value, unit, normalized_key, prop_id),
                )
        return ShopItemPropertyData(prop_id, item_id, name, value, unit, normalized_key)

    def delete_shop_item_property(self, property_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_item_property WHERE id = ?;", (property_id,))

    def add_shop_compare_item(self, item_id: int, category_id: Optional[int]) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO shop_compare_set (category_id, item_id)
                VALUES (?, ?);
                """,
                (category_id, item_id),
            )

    def remove_shop_compare_item(self, item_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM shop_compare_set WHERE item_id = ?;", (item_id,))

    def fetch_shop_compare_items(self, category_id: Optional[int]) -> List[ShopItemData]:
        if category_id is None:
            rows = self._conn.execute(
                """
                SELECT i.id, i.title, i.category_id, i.user_notes, i.created_at, i.updated_at
                FROM shop_compare_set c
                JOIN shop_item i ON i.id = c.item_id
                ORDER BY i.title COLLATE NOCASE ASC, i.id ASC;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT i.id, i.title, i.category_id, i.user_notes, i.created_at, i.updated_at
                FROM shop_compare_set c
                JOIN shop_item i ON i.id = c.item_id
                WHERE c.category_id = ?
                ORDER BY i.title COLLATE NOCASE ASC, i.id ASC;
                """,
                (category_id,),
            ).fetchall()
        return [
            ShopItemData(
                row["id"],
                row["title"],
                row["category_id"],
                row["user_notes"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def fetch_wishlists(self) -> List[WishlistData]:
        rows = self._conn.execute(
            """
            SELECT id, title, notes
            FROM wishlist
            ORDER BY title COLLATE NOCASE ASC, id ASC;
            """
        ).fetchall()
        return [WishlistData(row["id"], row["title"], row["notes"] or "") for row in rows]

    def create_wishlist(self, title: str, notes: str = "") -> WishlistData:
        title = validate_title(title, field_name="РЎРїРёСЃРѕРє")
        notes = (notes or "").strip()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO wishlist (title, notes)
                VALUES (?, ?);
                """,
                (title, notes),
            )
        return WishlistData(cur.lastrowid, title, notes)

    def update_wishlist(self, wishlist_id: int, title: str, notes: str = "") -> WishlistData:
        title = validate_title(title, field_name="РЎРїРёСЃРѕРє")
        notes = (notes or "").strip()
        with self._conn:
            self._conn.execute(
                """
                UPDATE wishlist
                SET title = ?, notes = ?
                WHERE id = ?;
                """,
                (title, notes, wishlist_id),
            )
        return WishlistData(wishlist_id, title, notes)

    def delete_wishlist(self, wishlist_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM wishlist WHERE id = ?;", (wishlist_id,))

    def fetch_wishlist_items(self, wishlist_id: int) -> List[WishlistItemData]:
        rows = self._conn.execute(
            """
            SELECT wishlist_id, item_id, qty, priority, target_price, chosen_source_id
            FROM wishlist_item
            WHERE wishlist_id = ?
            ORDER BY priority ASC, item_id ASC;
            """,
            (wishlist_id,),
        ).fetchall()
        return [
            WishlistItemData(
                row["wishlist_id"],
                row["item_id"],
                row["qty"],
                row["priority"],
                row["target_price"],
                row["chosen_source_id"],
            )
            for row in rows
        ]

    def upsert_wishlist_item(
        self,
        *,
        wishlist_id: int,
        item_id: int,
        qty: int = 1,
        priority: int = 3,
        target_price: Optional[float] = None,
        chosen_source_id: Optional[int] = None,
    ) -> WishlistItemData:
        qty = max(1, int(qty))
        priority = max(1, min(5, int(priority)))
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO wishlist_item
                (wishlist_id, item_id, qty, priority, target_price, chosen_source_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(wishlist_id, item_id) DO UPDATE SET
                    qty = excluded.qty,
                    priority = excluded.priority,
                    target_price = excluded.target_price,
                    chosen_source_id = excluded.chosen_source_id;
                """,
                (wishlist_id, item_id, qty, priority, target_price, chosen_source_id),
            )
        return WishlistItemData(wishlist_id, item_id, qty, priority, target_price, chosen_source_id)

    def delete_wishlist_item(self, wishlist_id: int, item_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM wishlist_item WHERE wishlist_id = ? AND item_id = ?;",
                (wishlist_id, item_id),
            )

    def export_purchases_data(self) -> dict:
        def rows_to_dicts(query: str):
            rows = self._conn.execute(query).fetchall()
            return [dict(row) for row in rows]

        return {
            "categories": rows_to_dicts("SELECT * FROM shop_category;"),
            "items": rows_to_dicts("SELECT * FROM shop_item;"),
            "sources": rows_to_dicts("SELECT * FROM shop_source;"),
            "price_history": rows_to_dicts("SELECT * FROM shop_price_history;"),
            "item_properties": rows_to_dicts("SELECT * FROM shop_item_property;"),
            "source_properties": rows_to_dicts("SELECT * FROM shop_source_property;"),
            "wishlists": rows_to_dicts("SELECT * FROM wishlist;"),
            "wishlist_items": rows_to_dicts("SELECT * FROM wishlist_item;"),
            "compare_set": rows_to_dicts("SELECT * FROM shop_compare_set;"),
        }

    def import_purchases_data(self, payload: dict) -> None:
        categories = payload.get("categories") or []
        items = payload.get("items") or []
        sources = payload.get("sources") or []
        price_history = payload.get("price_history") or []
        item_props = payload.get("item_properties") or []
        source_props = payload.get("source_properties") or []
        wishlists = payload.get("wishlists") or []
        wishlist_items = payload.get("wishlist_items") or []
        compare_set = payload.get("compare_set") or []

        existing_categories = {(c.title, c.parent_id): c.id for c in self.fetch_shop_categories()}
        category_map: dict[int, Optional[int]] = {}
        for cat in categories:
            key = (cat.get("title"), cat.get("parent_id"))
            if key in existing_categories:
                category_map[cat["id"]] = existing_categories[key]
                continue
            created = self.create_shop_category(cat.get("title") or "Р‘РµР· РєР°С‚РµРіРѕСЂРёРё", cat.get("parent_id"))
            category_map[cat["id"]] = created.id

        source_by_url = {s.url: s for s in self.fetch_shop_sources_for_items([item.id for item in self.fetch_shop_items()])}
        item_sources: dict[int, list[dict]] = {}
        for src in sources:
            item_sources.setdefault(src["item_id"], []).append(src)

        item_map: dict[int, int] = {}
        for item in items:
            existing_item_id = None
            for src in item_sources.get(item["id"], []):
                if src.get("url") in source_by_url:
                    existing_item_id = source_by_url[src["url"]].item_id
                    break
            if existing_item_id is not None:
                item_map[item["id"]] = existing_item_id
                continue
            created = self.create_shop_item(
                item.get("title") or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ",
                category_id=category_map.get(item.get("category_id")),
                user_notes=item.get("user_notes") or "",
            )
            item_map[item["id"]] = created.id

        source_map: dict[int, int] = {}
        for src in sources:
            url = src.get("url") or ""
            if url in source_by_url:
                source_map[src["id"]] = source_by_url[url].id
                continue
            source = self.upsert_shop_source(
                item_id=item_map.get(src.get("item_id")),
                shop_code=src.get("shop_code") or "",
                url=url,
                sku=src.get("sku") or "",
                currency=src.get("currency") or "",
                price=src.get("price"),
                in_stock=bool(src.get("in_stock")),
                stock_text=src.get("stock_text") or "",
                parsed_at=src.get("parsed_at") or "",
                raw_json=src.get("raw_json") or "",
            )
            source_map[src["id"]] = source.id

        for row in price_history:
            new_source_id = source_map.get(row.get("source_id"))
            if new_source_id is None:
                continue
            self.add_shop_price_history(
                source_id=new_source_id,
                price=row.get("price"),
                currency=row.get("currency") or "",
                in_stock=bool(row.get("in_stock")),
                captured_at=row.get("captured_at") or "",
            )

        for prop in item_props:
            new_item_id = item_map.get(prop.get("item_id"))
            if new_item_id is None:
                continue
            self.upsert_shop_item_property(
                item_id=new_item_id,
                name=prop.get("name") or "",
                value=prop.get("value") or "",
                unit=prop.get("unit") or "",
                normalized_key=prop.get("normalized_key") or "",
            )

        source_props_grouped: dict[int, list[ShopSourcePropertyData]] = {}
        for prop in source_props:
            new_source_id = source_map.get(prop.get("source_id"))
            if new_source_id is None:
                continue
            source_props_grouped.setdefault(new_source_id, []).append(
                ShopSourcePropertyData(
                    id=0,
                    source_id=new_source_id,
                    name=prop.get("name") or "",
                    value=prop.get("value") or "",
                    unit=prop.get("unit") or "",
                    normalized_key=prop.get("normalized_key") or "",
                )
            )
        for source_id, props in source_props_grouped.items():
            self.replace_shop_source_properties(source_id, props)

        wishlist_map: dict[int, int] = {}
        existing_wishlists = {w.title: w.id for w in self.fetch_wishlists()}
        for wl in wishlists:
            title = wl.get("title") or "РЎРїРёСЃРѕРє"
            if title in existing_wishlists:
                wishlist_map[wl["id"]] = existing_wishlists[title]
                continue
            created = self.create_wishlist(title, wl.get("notes") or "")
            wishlist_map[wl["id"]] = created.id

        for wi in wishlist_items:
            new_wishlist_id = wishlist_map.get(wi.get("wishlist_id"))
            new_item_id = item_map.get(wi.get("item_id"))
            if new_wishlist_id is None or new_item_id is None:
                continue
            self.upsert_wishlist_item(
                wishlist_id=new_wishlist_id,
                item_id=new_item_id,
                qty=wi.get("qty") or 1,
                priority=wi.get("priority") or 3,
                target_price=wi.get("target_price"),
                chosen_source_id=source_map.get(wi.get("chosen_source_id")),
            )

        for entry in compare_set:
            new_item_id = item_map.get(entry.get("item_id"))
            new_category_id = category_map.get(entry.get("category_id"))
            if new_item_id is None:
                continue
            self.add_shop_compare_item(new_item_id, new_category_id)

    def create_shop_item(
        self,
        title: str,
        *,
        category_id: Optional[int] = None,
        user_notes: str = "",
    ) -> ShopItemData:
        title = (title or "").strip() or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ"
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rstrip()
        user_notes = (user_notes or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shop_item (title, category_id, user_notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (title, category_id, user_notes, now, now),
            )
        return ShopItemData(cur.lastrowid, title, category_id, user_notes, now, now)

    def update_shop_item(
        self,
        item_id: int,
        *,
        title: str,
        category_id: Optional[int],
        user_notes: str,
    ) -> ShopItemData:
        title = (title or "").strip() or "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ"
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rstrip()
        user_notes = (user_notes or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            self._conn.execute(
                """
                UPDATE shop_item
                SET title = ?, category_id = ?, user_notes = ?, updated_at = ?
                WHERE id = ?;
                """,
                (title, category_id, user_notes, now, item_id),
            )
        row = self._conn.execute(
            """
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            WHERE id = ?;
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            raise ValueError("РўРѕРІР°СЂ РЅРµ РЅР°Р№РґРµРЅ.")
        return ShopItemData(
            row["id"],
            row["title"],
            row["category_id"],
            row["user_notes"] or "",
            row["created_at"],
            row["updated_at"],
        )

    def upsert_shop_source(
        self,
        *,
        item_id: int,
        shop_code: str,
        url: str,
        sku: str = "",
        currency: str = "",
        price: Optional[float] = None,
        in_stock: bool = False,
        stock_text: str = "",
        parsed_at: str = "",
        raw_json: str = "",
    ) -> ShopSourceData:
        shop_code = (shop_code or "").strip()
        url = (url or "").strip()
        if not url:
            raise ValueError("URL РёСЃС‚РѕС‡РЅРёРєР° РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        sku = (sku or "").strip()
        currency = (currency or "").strip()
        stock_text = (stock_text or "").strip()
        parsed_at = (parsed_at or "").strip()
        raw_json = (raw_json or "").strip()
        with self._conn:
            row = self._conn.execute(
                "SELECT id FROM shop_source WHERE url = ?;",
                (url,),
            ).fetchone()
            if row is None:
                cur = self._conn.execute(
                    """
                    INSERT INTO shop_source
                    (item_id, shop_code, url, sku, currency, price, in_stock, stock_text, parsed_at, raw_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item_id,
                        shop_code,
                        url,
                        sku,
                        currency,
                        price,
                        int(bool(in_stock)),
                        stock_text,
                        parsed_at,
                        raw_json,
                    ),
                )
                source_id = cur.lastrowid
            else:
                source_id = row["id"]
                self._conn.execute(
                    """
                    UPDATE shop_source
                    SET item_id = ?, shop_code = ?, sku = ?, currency = ?, price = ?, in_stock = ?,
                        stock_text = ?, parsed_at = ?, raw_json = ?
                    WHERE id = ?;
                    """,
                    (
                        item_id,
                        shop_code,
                        sku,
                        currency,
                        price,
                        int(bool(in_stock)),
                        stock_text,
                        parsed_at,
                        raw_json,
                        source_id,
                    ),
                )
        return ShopSourceData(
            source_id,
            item_id,
            shop_code,
            url,
            sku,
            currency,
            price,
            bool(in_stock),
            stock_text,
            parsed_at,
            raw_json,
        )

    def add_shop_price_history(
        self,
        *,
        source_id: int,
        price: Optional[float],
        currency: str,
        in_stock: bool,
        captured_at: str,
    ) -> ShopPriceHistoryData:
        currency = (currency or "").strip()
        captured_at = (captured_at or "").strip()
        if not captured_at:
            captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO shop_price_history
                (source_id, price, currency, in_stock, captured_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (source_id, price, currency, int(bool(in_stock)), captured_at),
            )
        return ShopPriceHistoryData(cur.lastrowid, source_id, price, currency, bool(in_stock), captured_at)

    def fetch_shop_price_history(self, source_id: int, days: int) -> List[ShopPriceHistoryData]:
        rows = self._conn.execute(
            """
            SELECT id, source_id, price, currency, in_stock, captured_at
            FROM shop_price_history
            WHERE source_id = ? AND captured_at >= datetime('now', ?)
            ORDER BY captured_at ASC;
            """,
            (source_id, f"-{int(days)} days"),
        ).fetchall()
        return [
            ShopPriceHistoryData(
                row["id"],
                row["source_id"],
                row["price"],
                row["currency"] or "",
                bool(row["in_stock"]),
                row["captured_at"],
            )
            for row in rows
        ]

    def add_shop_parse_log(
        self,
        *,
        source_id: Optional[int],
        shop_code: str,
        url: str,
        status_code: Optional[int],
        content_type: str,
        fetched_at: str,
        raw_snippet: str,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO shop_parse_log
                (source_id, shop_code, url, status_code, content_type, fetched_at, raw_snippet)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    source_id,
                    shop_code,
                    url,
                    status_code,
                    content_type,
                    fetched_at,
                    raw_snippet,
                ),
            )

    def fetch_shop_parse_logs(self, source_id: Optional[int] = None) -> List[dict]:
        if source_id is None:
            rows = self._conn.execute(
                """
                SELECT id, source_id, shop_code, url, status_code, content_type, fetched_at, raw_snippet
                FROM shop_parse_log
                ORDER BY fetched_at DESC, id DESC;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, source_id, shop_code, url, status_code, content_type, fetched_at, raw_snippet
                FROM shop_parse_log
                WHERE source_id = ?
                ORDER BY fetched_at DESC, id DESC;
                """,
                (source_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_shop_items(self, search_text: str = "") -> List[ShopItemData]:
        search_text = (search_text or "").strip().lower()
        params: list[object] = []
        where_sql = ""
        if search_text:
            where_sql = "WHERE lower(title) LIKE ?"
            params.append(f"%{search_text}%")
        rows = self._conn.execute(
            f"""
            SELECT id, title, category_id, user_notes, created_at, updated_at
            FROM shop_item
            {where_sql}
            ORDER BY updated_at DESC, title COLLATE NOCASE ASC, id DESC;
            """,
            tuple(params),
        ).fetchall()
        return [
            ShopItemData(
                row["id"],
                row["title"],
                row["category_id"],
                row["user_notes"] or "",
                row["created_at"],
                row["updated_at"],
            )
            for row in rows
        ]

    def fetch_shop_items_with_stats(
        self,
        *,
        search_text: str = "",
        category_id: Optional[int] = None,
    ) -> List[dict]:
        search_text = (search_text or "").strip().lower()
        params: list[object] = []
        clauses: list[str] = []
        if search_text:
            clauses.append("lower(i.title) LIKE ?")
            params.append(f"%{search_text}%")
        if category_id is not None:
            clauses.append("i.category_id = ?")
            params.append(category_id)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT
                i.id,
                i.title,
                i.category_id,
                c.title AS category_title,
                i.created_at,
                i.updated_at,
                (
                    SELECT MIN(s.price)
                    FROM shop_source s
                    WHERE s.item_id = i.id AND s.in_stock = 1 AND s.price IS NOT NULL
                ) AS best_price,
                (
                    SELECT MIN(s.price)
                    FROM shop_source s
                    WHERE s.item_id = i.id AND s.price IS NOT NULL
                ) AS best_price_any,
                (
                    SELECT COUNT(*) FROM shop_source s WHERE s.item_id = i.id
                ) AS sources_count,
                (
                    SELECT MAX(s.parsed_at) FROM shop_source s WHERE s.item_id = i.id
                ) AS last_parsed_at
            FROM shop_item i
            LEFT JOIN shop_category c ON c.id = i.category_id
            {where_sql}
            ORDER BY i.updated_at DESC, i.title COLLATE NOCASE ASC, i.id DESC;
            """,
            tuple(params),
        ).fetchall()
        result = []
        for row in rows:
            best_price = row["best_price"]
            if best_price is None:
                best_price = row["best_price_any"]
            result.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "category_id": row["category_id"],
                    "category_title": row["category_title"] or "",
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "best_price": best_price,
                    "sources_count": row["sources_count"] or 0,
                    "last_parsed_at": row["last_parsed_at"] or "",
                }
            )
        return result

    def fetch_item_min_price_last_days(self, item_id: int, days: int) -> Optional[float]:
        row = self._conn.execute(
            """
            SELECT MIN(p.price) AS min_price
            FROM shop_price_history p
            JOIN shop_source s ON s.id = p.source_id
            WHERE s.item_id = ? AND p.price IS NOT NULL AND p.captured_at >= datetime('now', ?);
            """,
            (item_id, f"-{int(days)} days"),
        ).fetchone()
        if row is None:
            return None
        return row["min_price"]

    def get_setting(self, key: str, default: str = "") -> str:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ Р·РЅР°С‡РµРЅРёРµ РЅР°СЃС‚СЂРѕР№РєРё."""
        key = (key or "").strip()
        if not key:
            raise ValueError("РљР»СЋС‡ РЅР°СЃС‚СЂРѕР№РєРё РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        cur = self._conn.execute("SELECT value FROM settings WHERE key = ?;", (key,))
        row = cur.fetchone()
        if not row:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        """РЎРѕС…СЂР°РЅСЏРµС‚ Р·РЅР°С‡РµРЅРёРµ РЅР°СЃС‚СЂРѕР№РєРё."""
        key = (key or "").strip()
        if not key:
            raise ValueError("РљР»СЋС‡ РЅР°СЃС‚СЂРѕР№РєРё РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
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
        """РЎРѕР·РґР°РµС‚ РёР»Рё РѕР±РЅРѕРІР»СЏРµС‚ Р·Р°РїРёСЃСЊ Рѕ С„Р°Р№Р»Рµ РѕР±Р»Р°РєР°."""
        rel_path = (rel_path or "").strip()
        if not rel_path:
            raise ValueError("РџСѓС‚СЊ С„Р°Р№Р»Р° РЅРµ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        name = (name or "").strip()
        checksum = (checksum or "").strip()
        if not name or not checksum:
            raise ValueError("РРјСЏ С„Р°Р№Р»Р° Рё РєРѕРЅС‚СЂРѕР»СЊРЅР°СЏ СЃСѓРјРјР° РѕР±СЏР·Р°С‚РµР»СЊРЅС‹.")
        description = (description or "").strip()
        hash_value = (hash_value or "").strip()
        size = max(0, int(size))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

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
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє С„Р°Р№Р»РѕРІ РѕР±Р»Р°РєР°."""
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
        """РЈРґР°Р»СЏРµС‚ Р·Р°РїРёСЃРё Рѕ С„Р°Р№Р»Р°С…, РєРѕС‚РѕСЂС‹С… РЅРµС‚ РІ РѕР±Р»Р°С‡РЅРѕРј РєР°С‚Р°Р»РѕРіРµ."""
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
        """РџРµСЂРµРёРЅРґРµРєСЃРёСЂСѓРµС‚ С‚Р°Р±Р»РёС†С‹ Р±Р°Р·С‹ РґР°РЅРЅС‹С…."""
        with self._conn:
            self._conn.execute("REINDEX;")

    def backup_to(self, destination_path: Path) -> Path:
        """РЎРѕР·РґР°РµС‚ РєРѕРЅСЃРёСЃС‚РµРЅС‚РЅСѓСЋ РєРѕРїРёСЋ Р±Р°Р·С‹ РґР°РЅРЅС‹С… РІ СѓРєР°Р·Р°РЅРЅС‹Р№ С„Р°Р№Р»."""
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
        """Р—Р°РєСЂС‹РІР°РµС‚ СЃРѕРµРґРёРЅРµРЅРёРµ СЃ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С…."""
        if self._closed:
            return
        self._conn.close()
        self._closed = True


@lru_cache(maxsize=1)
def get_database() -> Database:
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ singleton Р±Р°Р·С‹ РґР°РЅРЅС‹С…."""
    return Database()


def reset_database(path: Optional[Path] = None) -> Database:
    """РЎР±СЂР°СЃС‹РІР°РµС‚ singleton Р±Р°Р·С‹ РґР°РЅРЅС‹С… Рё РІРѕР·РІСЂР°С‰Р°РµС‚ РЅРѕРІРѕРµ РїРѕРґРєР»СЋС‡РµРЅРёРµ."""
    if get_database.cache_info().currsize == 1:
        db = get_database()
        try:
            db.close()
        except sqlite3.Error:
            pass
    get_database.cache_clear()
    if path is not None:
        return Database(path=path)
    return get_database()


