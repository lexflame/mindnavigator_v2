-- MindNavigator: ideas workspace tables (SQLite)
-- You can adapt names/columns to existing conventions.

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY,
    project_id TEXT NULL,

    title TEXT NOT NULL DEFAULT '',
    summary TEXT NULL,
    body_md TEXT NOT NULL DEFAULT '',

    type TEXT NOT NULL DEFAULT 'other',
    status TEXT NOT NULL DEFAULT 'inbox',

    value_score INTEGER NOT NULL DEFAULT 3 CHECK(value_score BETWEEN 1 AND 5),
    effort_score INTEGER NOT NULL DEFAULT 3 CHECK(effort_score BETWEEN 1 AND 5),

    source TEXT NULL,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    archived_at TEXT NULL,

    -- If you already have projects table with id TEXT, keep FK; otherwise remove FK block.
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

-- Simple link list for references
CREATE TABLE IF NOT EXISTS idea_links (
    id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(idea_id) REFERENCES ideas(id) ON DELETE CASCADE
);

-- Tags: either join to your global tags table, or store plain text here
CREATE TABLE IF NOT EXISTS idea_tags (
    id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL,
    tag_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(idea_id, tag_text),
    FOREIGN KEY(idea_id) REFERENCES ideas(id) ON DELETE CASCADE
);

-- Relations to other entities (tasks/notes/maps/objects/files)
CREATE TABLE IF NOT EXISTS idea_relations (
    id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL,
    entity_type TEXT NOT NULL, -- 'task'|'note'|'object'|'map_marker'|'file' etc
    entity_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(idea_id, entity_type, entity_id),
    FOREIGN KEY(idea_id) REFERENCES ideas(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ideas_project_id ON ideas(project_id);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
CREATE INDEX IF NOT EXISTS idx_ideas_type ON ideas(type);
CREATE INDEX IF NOT EXISTS idx_ideas_updated_at ON ideas(updated_at);
CREATE INDEX IF NOT EXISTS idx_ideas_archived_at ON ideas(archived_at);

CREATE INDEX IF NOT EXISTS idx_idea_links_idea_id ON idea_links(idea_id);
CREATE INDEX IF NOT EXISTS idx_idea_tags_idea_id ON idea_tags(idea_id);
CREATE INDEX IF NOT EXISTS idx_idea_relations_idea_id ON idea_relations(idea_id);

-- Optional: trigger to update updated_at
CREATE TRIGGER IF NOT EXISTS trg_ideas_updated_at
AFTER UPDATE ON ideas
FOR EACH ROW
BEGIN
    UPDATE ideas SET updated_at = datetime('now') WHERE id = NEW.id;
END;
