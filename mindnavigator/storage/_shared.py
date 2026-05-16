"""Shared constants, helpers, and imports for storage mixins."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

from mindnavigator.spaceenity.db_migrations import MigrationStep, apply_migrations
from .task_data import TaskData
from .project_data import ProjectData
from .map_data import MapData
from .map_marker_data import MapMarkerData
from .map_overlay_data import MapOverlayData
from .task_attachment_data import TaskAttachmentData
from .dossier_data import DossierData
from .dossier_link_data import DossierLinkData
from .cloud_file_data import CloudFileData
from .note_data import NoteData
from .idea_data import IdeaData
from .idea_image_data import IdeaImageData
from .idea_relation_data import IdeaRelationData
from .object_data import ObjectData
from .object_image_data import ObjectImageData
from .character_data import CharacterData
from .character_link_data import CharacterLinkData
from .collection_item_data import CollectionItemData
from .collection_category_data import CollectionCategoryData
from .collection_relation_data import CollectionRelationData
from .collection_entry_data import CollectionEntryData
from .shop_category_data import ShopCategoryData
from .shop_item_data import ShopItemData
from .shop_source_data import ShopSourceData
from .shop_price_history_data import ShopPriceHistoryData
from .shop_item_property_data import ShopItemPropertyData
from .shop_source_property_data import ShopSourcePropertyData
from .wishlist_data import WishlistData
from .wishlist_item_data import WishlistItemData
from .mutaboard_data import MutaBoardData
from .mutaboard_column_data import MutaBoardColumnData
from .mutaboard_item_data import MutaBoardItemData

DEFERRED_PRIORITY = "Отложенная"
LEGACY_DEFERRED_PRIORITY = "\u0420\u045b\u0421\u201a\u0420\u00bb\u0420\u0455\u0420\u00b6\u0420\u00b5\u0420\u0405\u0420\u0405\u0420\u00b0\u0421\u040f"
PRIORITIES = ("Low", "Medium", "High", DEFERRED_PRIORITY)
BOARD_COLUMN_DEFERRED = "deferred"
BOARD_COLUMN_QUEUE = "queue"
BOARD_COLUMN_IN_PROGRESS = "in_progress"
BOARD_COLUMN_COMPLETED = "completed"
BOARD_COLUMNS = (
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_QUEUE,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_COMPLETED,
)
MAX_TITLE_LEN = 160
MAX_AREA_LEN = 80
COLLECTION_ENTITY_TYPES = ("building", "city", "film", "game", "character", "other")
CHARACTER_ENTITY_KINDS = (
    "task",
    "project",
    "note",
    "idea",
    "object",
    "map",
    "marker",
    "file",
    "collection_item",
    "collection_category",
    "shop_category",
    "shop_item",
    "shop_source",
    "wishlist",
)
APP_CONFIG_FILE = "app_config.json"
APP_CONFIG_DB_PATH_KEY = "db_path"
SQLITE_BUSY_TIMEOUT_MS = 10000

_PACKAGE_MODULE_NAME = "mindnavigator.storage"


def _package_override(name: str, current: Any) -> Any:
    module = sys.modules.get(_PACKAGE_MODULE_NAME)
    if module is None:
        return current
    override = getattr(module, name, None)
    if override is None or override is current:
        return current
    return override


def _app_base_dir() -> Path:
    override = _package_override("_app_base_dir", _app_base_dir)
    if override is not _app_base_dir:
        return override()
    base = Path.home() / ".mindnavigator"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _app_config_path() -> Path:
    override = _package_override("_app_config_path", _app_config_path)
    if override is not _app_config_path:
        return override()
    return _app_base_dir() / APP_CONFIG_FILE


def _read_app_config() -> dict:
    override = _package_override("_read_app_config", _read_app_config)
    if override is not _read_app_config:
        return override()
    config_path = _app_config_path()
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_app_config(config: dict) -> None:
    override = _package_override("_write_app_config", _write_app_config)
    if override is not _write_app_config:
        override(config)
        return
    config_path = _app_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get_configured_db_path() -> Optional[Path]:
    config = _read_app_config()
    raw_path = str(config.get(APP_CONFIG_DB_PATH_KEY, "")).strip()
    if not raw_path:
        return None
    return Path(raw_path)


def set_configured_db_path(path: Optional[Path | str]) -> Optional[Path]:
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
    configured = get_configured_db_path()
    if configured is not None:
        configured.parent.mkdir(parents=True, exist_ok=True)
        return configured
    return _app_base_dir() / "mindnavigator.db"


def is_network_database_path(path: Path) -> bool:
    normalized_path = str(path).strip()
    return normalized_path.startswith("\\\\") or normalized_path.startswith("//")


def _configure_connection_pragmas(connection: sqlite3.Connection, path: Path) -> None:
    network_check = _package_override("is_network_database_path", is_network_database_path)
    journal_mode = "DELETE" if network_check(path) else "WAL"
    connection.execute(f"PRAGMA journal_mode={journal_mode};")
    connection.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA foreign_keys=ON;")


def validate_title(title: str, field_name: str = "Название") -> str:
    title = (title or "").strip()
    if not title:
        raise ValueError(f"{field_name} не должно быть пустым.")
    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f"{field_name} слишком длинное (до {MAX_TITLE_LEN} символов).")
    return title


def validate_area(area: str) -> str:
    area = (area or "").strip()
    if not area:
        raise ValueError("Область проекта не должна быть пустой.")
    if len(area) > MAX_AREA_LEN:
        raise ValueError(f"Область проекта слишком длинная (до {MAX_AREA_LEN} символов).")
    return area


def normalize_priority(priority: str) -> str:
    priority = str(priority or "").strip() or "Medium"
    if priority == LEGACY_DEFERRED_PRIORITY:
        return DEFERRED_PRIORITY
    if priority == "4":
        return DEFERRED_PRIORITY
    if priority == "3":
        return "High"
    if priority == "2":
        return "Medium"
    if priority == "1":
        return "Low"
    if priority.lower() == "deferred":
        return DEFERRED_PRIORITY
    if priority not in PRIORITIES:
        raise ValueError("Приоритет должен быть Low, Medium, High или Отложенная.")
    return priority


def normalize_board_column(board_column: str, priority: str = "Medium") -> str:
    normalized_priority = normalize_priority(priority)
    normalized = str(board_column or "").strip().lower()
    if normalized_priority == DEFERRED_PRIORITY:
        return BOARD_COLUMN_DEFERRED
    if normalized not in BOARD_COLUMNS:
        return BOARD_COLUMN_QUEUE
    if normalized == BOARD_COLUMN_DEFERRED:
        return BOARD_COLUMN_QUEUE
    return normalized


def validate_time_text(time_text: str) -> str:
    time_text = (time_text or "").strip()
    if not time_text:
        return ""
    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError as exc:
        raise ValueError("Время должно быть в формате HH:MM.") from exc
    return time_text


def parse_project_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise ValueError("Дата проекта должна быть в формате dd.mm.yyyy.") from exc


def format_project_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


__all__ = [name for name in globals() if not name.startswith("__")]
