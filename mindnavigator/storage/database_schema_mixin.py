"""DatabaseSchemaMixin for storage database operations."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class DatabaseSchemaMixin:
    def _init_db(self) -> None:
        """Инициализирует схему и параметры SQLite."""
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
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT '',
                    actual_minutes INTEGER NOT NULL DEFAULT 0 CHECK (actual_minutes >= 0),
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
                    status TEXT NOT NULL DEFAULT 'inbox',
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
                CREATE TABLE IF NOT EXISTS idea_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                    rel_path TEXT NOT NULL,
                    caption TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(idea_id, rel_path)
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
                CREATE TABLE IF NOT EXISTS mutaboards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    capture_text TEXT NOT NULL DEFAULT '',
                    planning_text TEXT NOT NULL DEFAULT '',
                    links_text TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_columns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL
                        CHECK (kind IN ('task', 'idea', 'image', 'map', 'marker', 'note', 'project', 'object')),
                    title TEXT NOT NULL DEFAULT '',
                    position INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    entity_kind TEXT NOT NULL
                        CHECK (entity_kind IN ('task', 'idea', 'image', 'map', 'marker', 'note', 'project', 'object')),
                    entity_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(mutaboard_id, entity_kind, entity_id)
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
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_images_idea_id ON idea_images(idea_id);")
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
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mutaboards_updated_at ON mutaboards(updated_at);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_columns_board_position ON mutaboard_columns(mutaboard_id, position, id);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_items_board_kind ON mutaboard_items(mutaboard_id, entity_kind, entity_id);"
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
        self._ensure_priority_values()
        self._ensure_project_extended_columns()
        self._ensure_project_marker_columns()
        self._ensure_task_execution_columns()
        self._ensure_dossier_schema()
        self._ensure_idea_image_schema()
        self._ensure_idea_category_schema()
        self._seed_default_idea_categories()
        self._ensure_mutaboard_schema()
        self._seed_defaults()

    def _run_schema_migrations(self) -> None:
        """Применяет версионированные миграции схемы SQLite."""
        steps = [
            MigrationStep(1, "core_task_project_schema", self._migration_v1_core_task_project_schema),
            MigrationStep(2, "map_marker_and_attachment_schema", self._migration_v2_map_marker_and_attachment_schema),
            MigrationStep(3, "collection_schema", self._migration_v3_collection_schema),
            MigrationStep(4, "task_board_schema", self._migration_v4_task_board_schema),
            MigrationStep(5, "dossier_schema", self._migration_v5_dossier_schema),
            MigrationStep(6, "task_plan_schema", self._migration_v6_task_plan_schema),
            MigrationStep(7, "task_execution_schema", self._migration_v7_task_execution_schema),
            MigrationStep(8, "idea_image_schema", self._migration_v8_idea_image_schema),
            MigrationStep(9, "mutaboard_schema", self._migration_v9_mutaboard_schema),
            MigrationStep(10, "idea_category_schema", self._migration_v10_idea_category_schema),
            MigrationStep(11, "concept_board_schema", self._migration_v11_concept_board_schema),
        ]
        apply_migrations(self._conn, steps)
        self._ensure_task_board_column()

    def apply_schema_updates(self) -> int:
        """Применяет все доступные миграции схемы и возвращает user_version."""
        self._run_schema_migrations()
        self._ensure_priority_values()
        self._ensure_project_extended_columns()
        self._ensure_project_marker_columns()
        self._ensure_task_plan_columns()
        self._ensure_task_execution_columns()
        self._ensure_dossier_schema()
        self._ensure_idea_image_schema()
        self._ensure_idea_category_schema()
        self._seed_default_idea_categories()
        self._ensure_mutaboard_schema()
        self._ensure_concept_board_schema()
        row = self._conn.execute("PRAGMA user_version;").fetchone()
        return int(row[0]) if row else 0

    def _migration_v1_core_task_project_schema(self, _connection: sqlite3.Connection) -> None:
        """Миграция v1: выравнивание базовых колонок задач/проектов и индексов."""
        self._ensure_task_project_column()
        self._ensure_project_extended_columns()
        self._ensure_task_description_column()
        self._ensure_task_parent_column()
        self._ensure_task_recurrence_columns()
        self._ensure_task_plan_columns()
        self._ensure_task_marker_columns()
        self._ensure_task_completion_delay_column()
        self._ensure_task_gantt_columns()
        self._ensure_task_execution_columns()
        self._ensure_priority_values()
        self._ensure_map_tiles_path_column()
        self._ensure_project_marker_columns()

    def _migration_v2_map_marker_and_attachment_schema(self, _connection: sqlite3.Connection) -> None:
        """Миграция v2: приведение структуры меток карты и вложений задач."""
        self._ensure_marker_attachment_columns()
        self._ensure_marker_parent_path_column()
        self._ensure_marker_image_column()
        self._ensure_map_marker_foreign_keys()
        self._ensure_task_attachment_foreign_keys()

    def _migration_v3_collection_schema(self, _connection: sqlite3.Connection) -> None:
        """Миграция v3: приведение таблиц коллекций и связанных колонок."""
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

    def _migration_v7_task_execution_schema(self, _connection: sqlite3.Connection) -> None:
        """Adds execution tracking columns for plan-task progression."""
        self._ensure_task_execution_columns()

    def _migration_v8_idea_image_schema(self, _connection: sqlite3.Connection) -> None:
        """Adds storage for idea images and captions."""
        self._ensure_idea_image_schema()

    def _migration_v9_mutaboard_schema(self, _connection: sqlite3.Connection) -> None:
        """Adds storage for persistent mutaboards, columns, and attached items."""
        self._ensure_mutaboard_schema()

    def _migration_v11_concept_board_schema(self, _connection: sqlite3.Connection) -> None:
        """Expands mutaboard storage for persisted concept versions, solutions, and typed links."""
        self._ensure_concept_board_schema()

    def _migration_v10_idea_category_schema(self, _connection: sqlite3.Connection) -> None:
        """Adds editable idea categories and removes the fixed status CHECK."""
        self._ensure_idea_category_schema()
        self._seed_default_idea_categories()
        self._rebuild_ideas_table()

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

    def _ensure_idea_image_schema(self) -> None:
        """Ensures storage for idea images and captions exists."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idea_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                    rel_path TEXT NOT NULL,
                    caption TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(idea_id, rel_path)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_images_idea_id ON idea_images(idea_id);")

    def _ensure_idea_category_schema(self) -> None:
        """Ensures storage for editable idea categories exists."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idea_categories (
                    code TEXT PRIMARY KEY,
                    title TEXT NOT NULL COLLATE NOCASE,
                    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
                    sort_index INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(title)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_categories_sort ON idea_categories(sort_index, title);")

    def _ensure_mutaboard_schema(self) -> None:
        """Ensures persistent mutaboard tables and indexes exist."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    capture_text TEXT NOT NULL DEFAULT '',
                    planning_text TEXT NOT NULL DEFAULT '',
                    links_text TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_columns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL
                        CHECK (kind IN ('task', 'idea', 'image', 'map', 'marker', 'note', 'project', 'object', 'version', 'solution', 'file', 'link')),
                    title TEXT NOT NULL DEFAULT '',
                    position INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    entity_kind TEXT NOT NULL
                        CHECK (entity_kind IN ('task', 'idea', 'image', 'map', 'marker', 'note', 'project', 'object', 'version', 'solution', 'file', 'link')),
                    entity_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(mutaboard_id, entity_kind, entity_id)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mutaboards_updated_at ON mutaboards(updated_at);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_columns_board_position ON mutaboard_columns(mutaboard_id, position, id);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_items_board_kind ON mutaboard_items(mutaboard_id, entity_kind, entity_id);"
            )

    def _ensure_concept_board_schema(self) -> None:
        """Ensures extended concept board storage exists and legacy mutaboard constraints are upgraded."""
        self._rebuild_mutaboard_kind_table_if_needed(
            "mutaboard_columns",
            """
            CREATE TABLE mutaboard_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                kind TEXT NOT NULL
                    CHECK (kind IN ('task', 'idea', 'image', 'map', 'marker', 'note', 'project', 'object', 'version', 'solution', 'file', 'link')),
                title TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """,
            ("id", "mutaboard_id", "kind", "title", "position", "created_at", "updated_at"),
            (
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_columns_board_position ON mutaboard_columns(mutaboard_id, position, id);",
            ),
        )
        self._rebuild_mutaboard_kind_table_if_needed(
            "mutaboard_items",
            """
            CREATE TABLE mutaboard_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                entity_kind TEXT NOT NULL
                    CHECK (entity_kind IN ('task', 'idea', 'image', 'map', 'marker', 'note', 'project', 'object', 'version', 'solution', 'file', 'link')),
                entity_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(mutaboard_id, entity_kind, entity_id)
            );
            """,
            ("id", "mutaboard_id", "entity_kind", "entity_id", "created_at"),
            (
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_items_board_kind ON mutaboard_items(mutaboard_id, entity_kind, entity_id);",
            ),
        )
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    why_yes TEXT NOT NULL DEFAULT '',
                    why_no TEXT NOT NULL DEFAULT '',
                    checks_text TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    why_selected TEXT NOT NULL DEFAULT '',
                    rejected_text TEXT NOT NULL DEFAULT '',
                    next_steps_text TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft',
                    selected_version_id INTEGER REFERENCES mutaboard_versions(id) ON DELETE SET NULL,
                    decided_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mutaboard_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutaboard_id INTEGER NOT NULL REFERENCES mutaboards(id) ON DELETE CASCADE,
                    source_kind TEXT NOT NULL,
                    source_id INTEGER NOT NULL,
                    target_kind TEXT NOT NULL,
                    target_id INTEGER NOT NULL,
                    link_type TEXT NOT NULL DEFAULT 'relates_to',
                    created_at TEXT NOT NULL,
                    UNIQUE(mutaboard_id, source_kind, source_id, target_kind, target_id, link_type)
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mutaboard_versions_board ON mutaboard_versions(mutaboard_id, updated_at, id);")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mutaboard_solutions_board ON mutaboard_solutions(mutaboard_id, updated_at, id);")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_links_board_source ON mutaboard_links(mutaboard_id, source_kind, source_id, link_type, id);"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mutaboard_links_board_target ON mutaboard_links(mutaboard_id, target_kind, target_id, link_type, id);"
            )

    def _rebuild_mutaboard_kind_table_if_needed(
        self,
        table_name: str,
        create_sql: str,
        columns: tuple[str, ...],
        index_sql: tuple[str, ...],
    ) -> None:
        row = self._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?;",
            (table_name,),
        ).fetchone()
        if row is None:
            with self._conn:
                self._conn.execute(create_sql)
                for statement in index_sql:
                    self._conn.execute(statement)
            return
        sql = str(row["sql"] or "").lower()
        if all(token in sql for token in ("version", "solution", "file", "link")):
            return
        legacy_table = f"{table_name}_legacy_upgrade"
        column_list = ", ".join(columns)
        with self._conn:
            self._conn.execute(f"ALTER TABLE {table_name} RENAME TO {legacy_table};")
            self._conn.execute(create_sql)
            self._conn.execute(
                f"INSERT INTO {table_name} ({column_list}) SELECT {column_list} FROM {legacy_table};"
            )
            self._conn.execute(f"DROP TABLE {legacy_table};")
            for statement in index_sql:
                self._conn.execute(statement)

    def _ensure_task_project_column(self) -> None:
        """Добавляет колонку project_id, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "project_id" not in names:
            with self._conn:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER REFERENCES projects(id);")

    def _ensure_project_extended_columns(self) -> None:
        """Добавляет расширенные колонки проектов, если они отсутствуют."""
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
        """Нормализует порядок проектов внутри каждого родителя."""
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
        """Возвращает следующий индекс сортировки для дочерних проектов."""
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

    def _ensure_task_recurrence_columns(self) -> None:
        """Добавляет колонки периодичности задачи, если они отсутствуют."""
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
        """Добавляет колонки визуального маркера задачи, если они отсутствуют."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "marker_color" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN marker_color TEXT NOT NULL DEFAULT '';")
            if "marker_theme" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN marker_theme TEXT NOT NULL DEFAULT '';")

    def _ensure_task_completion_delay_column(self) -> None:
        """Добавляет колонку расхождения по времени выполнения, если она отсутствует."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        if "completion_delay_minutes" not in names:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE tasks ADD COLUMN completion_delay_minutes INTEGER NOT NULL DEFAULT 0;"
                )

    def _ensure_task_gantt_columns(self) -> None:
        """Добавляет колонки оценок Ганта, если они отсутствуют."""
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

    def _ensure_task_execution_columns(self) -> None:
        """Adds execution tracking columns for plan-item timing if they are absent."""
        columns = self._conn.execute("PRAGMA table_info(tasks);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "started_at" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN started_at TEXT NOT NULL DEFAULT '';")
            if "finished_at" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN finished_at TEXT NOT NULL DEFAULT '';")
            if "actual_minutes" not in names:
                self._conn.execute("ALTER TABLE tasks ADD COLUMN actual_minutes INTEGER NOT NULL DEFAULT 0;")

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
        """Добавляет колонки визуального маркера проекта, если они отсутствуют."""
        columns = self._conn.execute("PRAGMA table_info(projects);").fetchall()
        names = {row["name"] for row in columns}
        with self._conn:
            if "marker_color" not in names:
                self._conn.execute("ALTER TABLE projects ADD COLUMN marker_color TEXT NOT NULL DEFAULT '';")
            if "marker_theme" not in names:
                self._conn.execute("ALTER TABLE projects ADD COLUMN marker_theme TEXT NOT NULL DEFAULT '';")

    def _ensure_priority_values(self) -> None:
        """Обновляет ограничения приоритета до актуального списка значений."""
        if (
            self._priority_constraint_is_current("tasks")
            and self._priority_constraint_is_current("projects")
            and not self._task_project_fk_needs_repair()
            and not self._idea_project_fk_needs_repair()
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
            if projects_rebuilt or self._idea_project_fk_needs_repair():
                self._rebuild_ideas_table()
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

    def _idea_project_fk_needs_repair(self) -> bool:
        """Проверяет, что project_id в ideas ссылается на таблицу projects."""
        tables = {
            row["name"]
            for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        if "ideas" not in tables:
            return False
        rows = self._conn.execute("PRAGMA foreign_key_list(ideas);").fetchall()
        project_refs = [row for row in rows if row["from"] == "project_id"]
        if not project_refs:
            return True
        return any(row["table"] != "projects" for row in project_refs)

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

    def _task_attachment_fk_needs_repair(self) -> bool:
        """Проверяет, что внешние ключи task_attachments ссылаются на tasks."""
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
        """Исправляет устаревшие внешние ключи task_attachments, если таблица-источник отсутствует."""
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

    def _seed_default_idea_categories(self) -> None:
        """Ensures built-in idea categories exist."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        defaults = [
            ("inbox", "Inbox", 1),
            ("work", "Work", 2),
            ("ripe", "Ripe", 3),
            ("done", "Done", 4),
            ("archived", "Archived", 5),
        ]
        with self._conn:
            for code, title, sort_index in defaults:
                self._conn.execute(
                    """
                    INSERT INTO idea_categories (code, title, is_system, sort_index, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        is_system = 1,
                        sort_index = excluded.sort_index,
                        updated_at = excluded.updated_at;
                    """,
                    (code, title, sort_index, now, now),
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
                started_at TEXT NOT NULL DEFAULT '',
                finished_at TEXT NOT NULL DEFAULT '',
                actual_minutes INTEGER NOT NULL DEFAULT 0 CHECK (actual_minutes >= 0),
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
                gantt_forecasted, started_at, finished_at, actual_minutes, project_id, parent_id, recurrence_kind, recurrence_interval, is_plan_task, plan_order, marker_color, marker_theme, created_at, updated_at
            )
            SELECT id, title, {_source("description", "''")}, day, time_text, {self._priority_normalize_sql("priority")},
                   CASE
                       WHEN {self._priority_normalize_sql("priority")} = '{DEFERRED_PRIORITY}' THEN '{BOARD_COLUMN_DEFERRED}'
                       WHEN COALESCE({_source("board_column", "''")}, '') IN ('{BOARD_COLUMN_QUEUE}', '{BOARD_COLUMN_IN_PROGRESS}', '{BOARD_COLUMN_COMPLETED}') THEN {_source("board_column", "''")}
                       ELSE '{BOARD_COLUMN_QUEUE}'
                   END,
                   done, COALESCE({_source("completion_delay_minutes", "0")}, 0),
                   COALESCE({_source("gantt_estimate_minutes", "0")}, 0), COALESCE({_source("gantt_forecasted", "0")}, 0),
                   COALESCE({_source("started_at", "''")}, ''), COALESCE({_source("finished_at", "''")}, ''), COALESCE({_source("actual_minutes", "0")}, 0),
                   {_source("project_id", "NULL")}, {_source("parent_id", "NULL")},
                   COALESCE({_source("recurrence_kind", "''")}, ''), COALESCE({_source("recurrence_interval", "1")}, 1),
                   COALESCE({_source("is_plan_task", "0")}, 0), COALESCE({_source("plan_order", "0")}, 0),
                   COALESCE({_source("marker_color", "''")}, ''), COALESCE({_source("marker_theme", "''")}, ''), created_at, updated_at
            FROM tasks_old;
            """
        )
        self._conn.execute("DROP TABLE tasks_old;")
        self._rebuild_task_attachments_table()
        self._normalize_task_plan_order()

    def _rebuild_ideas_table(self) -> None:
        self._recover_rebuild_source_table("ideas")
        self._conn.execute("PRAGMA foreign_keys=OFF;")
        self._conn.execute("ALTER TABLE ideas RENAME TO ideas_old;")
        idea_columns = self._conn.execute("PRAGMA table_info(ideas_old);").fetchall()
        idea_column_names = {row["name"] for row in idea_columns}

        def _source(column_name: str, fallback_sql: str) -> str:
            return column_name if column_name in idea_column_names else fallback_sql

        self._conn.execute(
            """
            CREATE TABLE ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                body_md TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT 'other' CHECK (type IN ('feature', 'story', 'art', 'research', 'tech', 'other')),
                status TEXT NOT NULL DEFAULT 'inbox',
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
            f"""
            INSERT INTO ideas (
                id, project_id, title, summary, body_md, type, status,
                value_score, effort_score, source, created_at, updated_at, archived_at
            )
            SELECT
                id,
                {_source("project_id", "NULL")},
                COALESCE({_source("title", "''")}, ''),
                COALESCE({_source("summary", "''")}, ''),
                COALESCE({_source("body_md", "''")}, ''),
                COALESCE({_source("type", "'other'")}, 'other'),
                COALESCE({_source("status", "'inbox'")}, 'inbox'),
                COALESCE({_source("value_score", "3")}, 3),
                COALESCE({_source("effort_score", "3")}, 3),
                COALESCE({_source("source", "''")}, ''),
                created_at,
                updated_at,
                {_source("archived_at", "NULL")}
            FROM ideas_old;
            """
        )
        self._conn.execute("DROP TABLE ideas_old;")
        self._rebuild_idea_links_table()
        self._rebuild_idea_tags_table()
        self._rebuild_idea_relations_table()
        self._rebuild_idea_images_table()
        self._conn.execute("PRAGMA foreign_keys=ON;")

    def _rebuild_idea_links_table(self) -> None:
        if not self._recover_rebuild_source_table("idea_links", require_current=False):
            return
        columns = self._conn.execute("PRAGMA table_info(idea_links);").fetchall()
        names = {row["name"] for row in columns}
        if not names:
            return
        self._conn.execute("ALTER TABLE idea_links RENAME TO idea_links_old;")
        self._conn.execute(
            """
            CREATE TABLE idea_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                url TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(idea_id, url)
            );
            """
        )
        rows = self._conn.execute("SELECT id, idea_id, url, title, created_at FROM idea_links_old;").fetchall()
        for row in rows:
            self._conn.execute(
                """
                INSERT INTO idea_links (id, idea_id, url, title, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (row["id"], row["idea_id"], row["url"], row["title"], row["created_at"]),
            )
        self._conn.execute("DROP TABLE idea_links_old;")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_links_idea_id ON idea_links(idea_id);")

    def _rebuild_idea_tags_table(self) -> None:
        if not self._recover_rebuild_source_table("idea_tags", require_current=False):
            return
        columns = self._conn.execute("PRAGMA table_info(idea_tags);").fetchall()
        names = {row["name"] for row in columns}
        if not names:
            return
        self._conn.execute("ALTER TABLE idea_tags RENAME TO idea_tags_old;")
        self._conn.execute(
            """
            CREATE TABLE idea_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                tag_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(idea_id, tag_text)
            );
            """
        )
        rows = self._conn.execute("SELECT id, idea_id, tag_text, created_at FROM idea_tags_old;").fetchall()
        for row in rows:
            self._conn.execute(
                """
                INSERT INTO idea_tags (id, idea_id, tag_text, created_at)
                VALUES (?, ?, ?, ?);
                """,
                (row["id"], row["idea_id"], row["tag_text"], row["created_at"]),
            )
        self._conn.execute("DROP TABLE idea_tags_old;")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_tags_idea_id ON idea_tags(idea_id);")

    def _rebuild_idea_relations_table(self) -> None:
        if not self._recover_rebuild_source_table("idea_relations", require_current=False):
            return
        columns = self._conn.execute("PRAGMA table_info(idea_relations);").fetchall()
        names = {row["name"] for row in columns}
        if not names:
            return
        self._conn.execute("ALTER TABLE idea_relations RENAME TO idea_relations_old;")
        self._conn.execute(
            """
            CREATE TABLE idea_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(idea_id, entity_type, entity_id)
            );
            """
        )
        rows = self._conn.execute(
            "SELECT id, idea_id, entity_type, entity_id, created_at FROM idea_relations_old;"
        ).fetchall()
        for row in rows:
            self._conn.execute(
                """
                INSERT INTO idea_relations (id, idea_id, entity_type, entity_id, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (row["id"], row["idea_id"], row["entity_type"], row["entity_id"], row["created_at"]),
            )
        self._conn.execute("DROP TABLE idea_relations_old;")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_relations_idea_id ON idea_relations(idea_id);")

    def _rebuild_idea_images_table(self) -> None:
        if not self._recover_rebuild_source_table("idea_images", require_current=False):
            return
        columns = self._conn.execute("PRAGMA table_info(idea_images);").fetchall()
        names = {row["name"] for row in columns}
        if not names:
            return
        self._conn.execute("ALTER TABLE idea_images RENAME TO idea_images_old;")
        self._conn.execute(
            """
            CREATE TABLE idea_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idea_id INTEGER NOT NULL REFERENCES ideas(id) ON DELETE CASCADE,
                rel_path TEXT NOT NULL,
                caption TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(idea_id, rel_path)
            );
            """
        )
        rows = self._conn.execute(
            "SELECT id, idea_id, rel_path, caption, created_at, updated_at FROM idea_images_old;"
        ).fetchall()
        for row in rows:
            self._conn.execute(
                """
                INSERT INTO idea_images (id, idea_id, rel_path, caption, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    row["id"],
                    row["idea_id"],
                    row["rel_path"],
                    row["caption"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
        self._conn.execute("DROP TABLE idea_images_old;")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_idea_images_idea_id ON idea_images(idea_id);")

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
            ("SPACE", "Синхронизация FastAPI + S3", "05.01.2026", "Medium", 0),
            ("TACMap", "Редактор слоёв / маркеров", "03.01.2026", "High", 0),
            ("MakerTask", "ProjectsWorkspace UI (прототип)", "02.10.2025", "Medium", 0),
            ("MakerTask", "Drag&Drop планировщика", "01.10.2025", "High", 1),
            ("Wiki", "Cities: Skylines → DokuWiki", "22.07.2025", "Low", 0),
            ("Misc", "Сбор референсов / moodboard", "01.01.2026", "Low", 0),
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
            ("Northern Ridge", "Точки обзора и маршруты патрулей.", "MindNavigator v2", "", 18, 24),
            ("Sector 12", "Зоны контроля и минные поля.", "TACMap", "", 32, 32),
            ("Green Hills", "Артиллерийские позиции и наблюдатели.", "Wiki", "", 12, 20),
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

    def _seed_objects(self) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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

__all__ = ["DatabaseSchemaMixin"]
