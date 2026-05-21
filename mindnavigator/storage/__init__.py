"""Storage package facade preserving the historical mindnavigator.storage API."""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ._shared import (
    DEFERRED_PRIORITY,
    LEGACY_DEFERRED_PRIORITY,
    PRIORITIES,
    BOARD_COLUMN_DEFERRED,
    BOARD_COLUMN_QUEUE,
    BOARD_COLUMN_IN_PROGRESS,
    BOARD_COLUMN_COMPLETED,
    BOARD_COLUMNS,
    MAX_TITLE_LEN,
    MAX_AREA_LEN,
    COLLECTION_ENTITY_TYPES,
    CHARACTER_ENTITY_KINDS,
    APP_CONFIG_FILE,
    APP_CONFIG_DB_PATH_KEY,
    APP_CONFIG_DB_PATHS_KEY,
    SQLITE_BUSY_TIMEOUT_MS,
    _app_base_dir,
    _app_config_path,
    _read_app_config,
    _write_app_config,
    _configure_connection_pragmas,
    get_configured_db_path,
    get_configured_db_paths,
    add_configured_db_path,
    remove_configured_db_path,
    set_configured_db_path,
    set_configured_db_paths,
    default_db_path,
    is_network_database_path,
    validate_title,
    validate_area,
    normalize_priority,
    normalize_board_column,
    validate_time_text,
    parse_project_date,
    format_project_date,
)
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
from .idea_category_data import IdeaCategoryData
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
from .concept_board_data import ConceptBoardData
from .concept_board_column_data import ConceptBoardColumnData
from .concept_board_item_data import ConceptBoardItemData
from .concept_board_version_data import ConceptBoardVersionData
from .concept_board_solution_data import ConceptBoardSolutionData
from .concept_board_link_data import ConceptBoardLinkData
from .database import Database


@lru_cache(maxsize=1)
def get_database() -> Database:
    return Database()


def reset_database(path: Optional[Path] = None) -> Database:
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


__all__ = [name for name in globals() if not name.startswith("_")]
