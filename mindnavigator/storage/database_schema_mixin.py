"""DatabaseSchemaMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseSchemaMixin:
    def _init_db(self) -> None:
        """РРЅРёС†РёР°Р»РёР·РёСЂСѓРµС‚ СЃС…РµРјСѓ Рё РїР°СЂР°РјРµС‚СЂС‹ SQLite."""
        with self._conn:
            _configure_connection_pragmas(self._conn, self.path)

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    day TEXT NOT NULL,
                    time_text TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
                    board_column TEXT NOT NULL DEFAULT 'queue' CHECK (board_column IN ('deferred', 'queue', 'in_progress', 'completed')),
                    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                    completion_delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK (completion_delay_minutes >= 0),
                    gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0 CHECK (gantt_estimate_minutes >= 0),
                    gantt_forecasted INTEGER NOT NULL DEFAULT 0 CHECK (gantt_forecasted IN (0, 1)),
                    project_id INTEGER REFERENCES projects(id),
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
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area TEXT NOT NULL,
                    title TEXT NOT NULL,
                    updated TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
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
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS character_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                    entity_kind TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(character_id, entity_kind, entity_id)
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dossiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK (kind IN ('book', 'film', 'game', 'writer')),
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'active', 'completed', 'on_hold', 'archived')),
                    rating INTEGER CHECK (rating IS NULL OR (rating BETWEEN 1 AND 10)),
                    source TEXT NOT NULL DEFAULT '',
                    cover_image TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dossier_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
                    entity_kind TEXT NOT NULL
                        CHECK (entity_kind IN ('task', 'map', 'marker', 'note', 'idea', 'object', 'character')),
                    entity_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(dossier_id, entity_kind, entity_id)
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
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_characters_updated ON characters(updated_at);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_character_links_character ON character_links(character_id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_character_links_target ON character_links(entity_kind, entity_id);"
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_kind ON dossiers(kind);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_status ON dossiers(status);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_updated_at ON dossiers(updated_at);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossier_links_dossier ON dossier_links(dossier_id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dossier_links_target ON dossier_links(entity_kind, entity_id);"
            )
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
        # Some deployed databases have user_version already advanced while a subset
        # of projects columns is still missing. Enforce critical project columns
        # unconditionally to keep startup queries backward compatible.
        self._ensure_project_extended_columns()
        self._ensure_project_marker_columns()
        self._ensure_dossier_schema()
        self._seed_defaults()

    def _run_schema_migrations(self) -> None:
        """РџСЂРёРјРµРЅСЏРµС‚ РІРµСЂСЃРёРѕРЅРёСЂРѕРІР°РЅРЅС‹Рµ РјРёРіСЂР°С†РёРё СЃС…РµРјС‹ SQLite."""
        steps = [
            MigrationStep(1, "core_task_project_schema", self._migration_v1_core_task_project_schema),
            MigrationStep(2, "map_marker_and_attachment_schema", self._migration_v2_map_marker_and_attachment_schema),
            MigrationStep(3, "collection_schema", self._migration_v3_collection_schema),
            MigrationStep(4, "task_board_schema", self._migration_v4_task_board_schema),
            MigrationStep(5, "dossier_schema", self._migration_v5_dossier_schema),
            MigrationStep(6, "task_plan_schema", self._migration_v6_task_plan_schema),
        ]
        apply_migrations(self._conn, steps)
        self._ensure_task_board_column()

    def apply_schema_updates(self) -> int:
        """РџСЂРёРјРµРЅСЏРµС‚ РІСЃРµ РґРѕСЃС‚СѓРїРЅС‹Рµ РјРёРіСЂР°С†РёРё СЃС…РµРјС‹ Рё РІРѕР·РІСЂР°С‰Р°РµС‚ user_version."""
        self._run_schema_migrations()
        self._ensure_project_extended_columns()
        self._ensure_project_marker_columns()
        self._ensure_task_plan_columns()
        self._ensure_dossier_schema()
        row = self._conn.execute("PRAGMA user_version;").fetchone()
        return int(row[0]) if row else 0

    def _migration_v1_core_task_project_schema(self, _connection: sqlite3.Connection) -> None:
        """РњРёРіСЂР°С†РёСЏ v1: РІС‹СЂР°РІРЅРёРІР°РЅРёРµ Р±Р°Р·РѕРІС‹С… РєРѕР»РѕРЅРѕРє Р·Р°РґР°С‡/РїСЂРѕРµРєС‚РѕРІ Рё РёРЅРґРµРєСЃРѕРІ."""
        self._ensure_task_project_column()
        self._ensure_project_extended_columns()
        self._ensure_task_description_column()
        self._ensure_task_parent_column()
        self._ensure_task_recurrence_columns()
        self._ensure_task_plan_columns()
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

    def _migration_v4_task_board_schema(self, _connection: sqlite3.Connection) -> None:
        """Добавляет колонку board_column для канбан-режима задач."""
        self._ensure_task_board_column()

    def _migration_v5_dossier_schema(self, _connection: sqlite3.Connection) -> None:
        """Добавляет схему хранения досье и кросс-сущностных ссылок."""
        self._ensure_dossier_schema()

    def _migration_v6_task_plan_schema(self, _connection: sqlite3.Connection) -> None:
        """Добавляет поля plan-задач и порядка пунктов плана."""
        self._ensure_task_plan_columns()

    def _ensure_dossier_schema(self) -> None:
        """Гарантирует наличие таблиц и индексов режима досье."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dossiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK (kind IN ('book', 'film', 'game', 'writer')),
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'active', 'completed', 'on_hold', 'archived')),
                    rating INTEGER CHECK (rating IS NULL OR (rating BETWEEN 1 AND 10)),
                    source TEXT NOT NULL DEFAULT '',
                    cover_image TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dossier_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
                    entity_kind TEXT NOT NULL
                        CHECK (entity_kind IN ('task', 'map', 'marker', 'note', 'idea', 'object', 'character')),
                    entity_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(dossier_id, entity_kind, entity_id)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_kind ON dossiers(kind);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_status ON dossiers(status);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossiers_updated_at ON dossiers(updated_at);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dossier_links_dossier ON dossier_links(dossier_id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dossier_links_target ON dossier_links(entity_kind, entity_id);"
            )

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
            "repository_catalog": "ALTER TABLE projects ADD COLUMN repository_catalog TEXT NOT NULL DEFAULT '';",
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

    def _ensure_task_plan_columns(self) -> None:
        """Добавляет поля признака plan-задачи и порядка внутри родителя."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "is_plan_task" not in names:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN is_plan_task INTEGER NOT NULL DEFAULT 0;"
                )
            if "plan_order" not in names:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN plan_order INTEGER NOT NULL DEFAULT 0;"
                )
            self._normalize_task_plan_order()

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

    def _ensure_task_board_column(self) -> None:
        """Добавляет колонку board_column для канбан-статуса задач."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "board_column" in names:
            return
        with self._conn:
            self._conn.execute("ALTER TABLE tasks ADD COLUMN board_column TEXT NOT NULL DEFAULT 'queue';")
            self._conn.execute(
                f"""
                UPDATE tasks
                SET board_column = CASE
                    WHEN {self._priority_normalize_sql('priority')} = '{DEFERRED_PRIORITY}' THEN '{BOARD_COLUMN_DEFERRED}'
                    ELSE '{BOARD_COLUMN_QUEUE}'
                END;
                """
            )

    def _normalize_task_plan_order(self) -> None:
        """Нормализует sibling-порядок задач для каждого parent_id."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "plan_order" not in names:
            return
        if "parent_id" in names:
            rows = self._conn.execute(
                """
                SELECT id, parent_id, COALESCE(plan_order, 0) AS plan_order
                FROM tasks
                ORDER BY parent_id, plan_order, id;
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, NULL AS parent_id, COALESCE(plan_order, 0) AS plan_order
                FROM tasks
                ORDER BY plan_order, id;
                """
            ).fetchall()
        grouped: dict[Optional[int], list[int]] = {}
        for row in rows:
            grouped.setdefault(row["parent_id"], []).append(int(row["id"]))
        for sibling_ids in grouped.values():
            for plan_order, task_id in enumerate(sibling_ids):
                self._conn.execute(
                    "UPDATE tasks SET plan_order = ? WHERE id = ?;",
                    (plan_order, task_id),
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
        return DEFERRED_PRIORITY in (row["sql"] or "")

    @staticmethod
    def _priority_normalize_sql(column_expr: str) -> str:
        return (
            "CASE "
            f"WHEN {column_expr} IN ('Low', 'Medium', 'High', '{DEFERRED_PRIORITY}') THEN {column_expr} "
            f"WHEN {column_expr} = '{LEGACY_DEFERRED_PRIORITY}' THEN '{DEFERRED_PRIORITY}' "
            f"WHEN CAST({column_expr} AS TEXT) = '1' THEN 'Low' "
            f"WHEN CAST({column_expr} AS TEXT) = '2' THEN 'Medium' "
            f"WHEN CAST({column_expr} AS TEXT) = '3' THEN 'High' "
            f"WHEN CAST({column_expr} AS TEXT) = '4' THEN '{DEFERRED_PRIORITY}' "
            f"WHEN lower(CAST({column_expr} AS TEXT)) = 'low' THEN 'Low' "
            f"WHEN lower(CAST({column_expr} AS TEXT)) = 'medium' THEN 'Medium' "
            f"WHEN lower(CAST({column_expr} AS TEXT)) = 'high' THEN 'High' "
            f"WHEN lower(CAST({column_expr} AS TEXT)) = 'deferred' THEN '{DEFERRED_PRIORITY}' "
            "ELSE 'Medium' END"
        )

    def _recover_rebuild_source_table(self, table_name: str, *, require_current: bool = True) -> bool:
        """Восстанавливает исходную таблицу, если остался хвост `<table>_old` после прерванной миграции."""
        old_name = f"{table_name}_old"
        old_objects = self._conn.execute(
            "SELECT type FROM sqlite_master WHERE name=?;",
            (old_name,),
        ).fetchall()
        for row in old_objects:
            obj_type = row["type"]
            if obj_type == "index":
                self._conn.execute(f'DROP INDEX IF EXISTS "{old_name}";')
            elif obj_type == "view":
                self._conn.execute(f'DROP VIEW IF EXISTS "{old_name}";')
            elif obj_type == "trigger":
                self._conn.execute(f'DROP TRIGGER IF EXISTS "{old_name}";')

        has_current = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,),
        ).fetchone() is not None
        has_old = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
            (old_name,),
        ).fetchone() is not None

        if has_old and has_current:
            self._conn.execute(f'DROP TABLE "{table_name}";')
            self._conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{table_name}";')
            has_current = True
            has_old = False
        elif has_old and not has_current:
            self._conn.execute(f'ALTER TABLE "{old_name}" RENAME TO "{table_name}";')
            has_current = True
            has_old = False

        if require_current and not has_current:
            raise sqlite3.OperationalError(f"Source table '{table_name}' is missing for rebuild.")

        return has_current and not has_old

    def _rebuild_tasks_table(self) -> None:
        self._recover_rebuild_source_table("tasks")
        self._conn.execute("ALTER TABLE tasks RENAME TO tasks_old;")
        task_columns = self._conn.execute("PRAGMA table_info(tasks_old);").fetchall()
        task_column_names = {row["name"] for row in task_columns}

        def _source(column_name: str, fallback_sql: str) -> str:
            return column_name if column_name in task_column_names else fallback_sql

        self._conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                day TEXT NOT NULL,
                time_text TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
                board_column TEXT NOT NULL DEFAULT 'queue' CHECK (board_column IN ('deferred', 'queue', 'in_progress', 'completed')),
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                completion_delay_minutes INTEGER NOT NULL DEFAULT 0 CHECK (completion_delay_minutes >= 0),
                gantt_estimate_minutes INTEGER NOT NULL DEFAULT 0 CHECK (gantt_estimate_minutes >= 0),
                gantt_forecasted INTEGER NOT NULL DEFAULT 0 CHECK (gantt_forecasted IN (0, 1)),
                project_id INTEGER REFERENCES projects(id),
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
        self._conn.execute(
            f"""
            INSERT INTO tasks (
                id, title, description, day, time_text, priority, board_column, done, completion_delay_minutes, gantt_estimate_minutes,
                gantt_forecasted, project_id, parent_id, recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme, created_at, updated_at
            )
            SELECT id, title, {_source("description", "''")}, day, time_text, {self._priority_normalize_sql("priority")},
                   CASE
                       WHEN {self._priority_normalize_sql("priority")} = '{DEFERRED_PRIORITY}' THEN '{BOARD_COLUMN_DEFERRED}'
                       WHEN COALESCE({_source("board_column", "''")}, '') IN ('{BOARD_COLUMN_QUEUE}', '{BOARD_COLUMN_IN_PROGRESS}', '{BOARD_COLUMN_COMPLETED}') THEN {_source("board_column", "''")}
                       ELSE '{BOARD_COLUMN_QUEUE}'
                   END,
                   done, COALESCE({_source("completion_delay_minutes", "0")}, 0),
                   COALESCE({_source("gantt_estimate_minutes", "0")}, 0), COALESCE({_source("gantt_forecasted", "0")}, 0), {_source("project_id", "NULL")}, {_source("parent_id", "NULL")},
                   COALESCE({_source("recurrence_kind", "''")}, ''), COALESCE({_source("recurrence_interval", "1")}, 1),
                   COALESCE({_source("is_plan_task", "0")}, 0), COALESCE({_source("plan_order", "0")}, 0),
                   COALESCE({_source("marker_color", "''")}, ''), COALESCE({_source("marker_theme", "''")}, ''), created_at, updated_at
            FROM tasks_old;
            """
        )
        self._conn.execute("DROP TABLE tasks_old;")
        self._rebuild_task_attachments_table()
        self._normalize_task_plan_order()

    def _rebuild_projects_table(self) -> None:
        self._recover_rebuild_source_table("projects")
        self._conn.execute("ALTER TABLE projects RENAME TO projects_old;")
        self._conn.execute(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                title TEXT NOT NULL,
                updated TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Отложенная')),
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
                repository_catalog,
                marker_color,
                marker_theme
            )
            SELECT
                id,
                area,
                title,
                updated,
                {self._priority_normalize_sql(_source("priority", "'Medium'"))},
                archived,
                {_source("parent_project_id", "NULL")},
                COALESCE({_source("sort_order", "0")}, 0),
                COALESCE({_source("default_task_priority", "''")}, ''),
                COALESCE({_source("force_recurrence_kind", "''")}, ''),
                {_source("linked_map_id", "NULL")},
                {_source("linked_note_id", "NULL")},
                {_source("linked_object_id", "NULL")},
                COALESCE({_source("repository_catalog", "''")}, ''),
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
        if not self._recover_rebuild_source_table("task_attachments", require_current=False):
            return
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

__all__ = ["DatabaseSchemaMixin"]
