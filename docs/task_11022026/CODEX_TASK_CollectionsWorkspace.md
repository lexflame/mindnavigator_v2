# CODEX TASK: Add Workspace: Коллекции (Images/Links + Cross-links)

## Goal
Implement a new workspace 'Коллекции' to collect thematic images/links and create cross-links such as building=film, city=game, etc.

## Definition of Done
- CollectionsWorkspace exists and opens via app navigation.
- User can create/edit items with kind/title/url/tags and link rows.
- Search and filters are wired (even if minimal).
- Export/import v1 exists or is stubbed safely.

---

## Step 1: Create data model for Collections
**Create:** `mindnavigator/core/models/collection_item.py`

Add a minimal model (dataclass or pydantic-like if used in repo):
- `id: str` (uuid)
- `title: str`
- `kind: str` one of `image|link|note|object` (string enum for now)
- `url: str | None`
- `tags: list[str]`
- `links: list[dict]` where each link is `{"type": "building=film", "target_id": "..."}` (keep flexible)
- `created_at`, `updated_at` (ISO string or datetime depending on project patterns)

**Modify:** DB layer if exists (SQLite): add migration skeleton or schema notes.

**Acceptance check:**
- Model imports without errors.
- Structure supports cross-links like `building=film`, `city=game`.


---

## Step 2: Add CollectionsWorkspace skeleton (BaseWorkspace-based)
**Create:** `mindnavigator/ui/workspaces/collections_workspace.py`

Implement `class CollectionsWorkspace(BaseWorkspace):`
- `workspace_id = "collections"`
- `workspace_title = "Коллекции"`
- `build_content()` returns main view (list/grid placeholder).
- `create_actions()` add `add/edit/delete/refresh/share/import/export` (actions can be disabled until implemented).
- `apply_query()` filters locally (placeholder) and updates view.
- `apply_filters()` supports `kind` and `tag` keys.

UI minimal content:
- A list (`QListWidget`/`QTableView`) showing title + kind + tags + updated_at.

**Acceptance check:**
- Workspace opens and shows header/search/status from BaseWorkspace.
- Typing in search calls `apply_query()` without errors.


---

## Step 3: Add cross-link editor UI (minimal)
**Modify:** `CollectionsWorkspace` content widgets (or a dialog `collection_item_dialog.py`)

Implement a minimal 'Links' editor area:
- Add link row: `type` (string) + `target` (string/id) + remove button.
- Store links in the item model (in-memory for now).

Rules:
- Do not block future normalization; keep JSON-friendly structure.

**Acceptance check:**
- User can add/remove link rows and saving keeps them in item data (in memory or persisted if storage exists).


---

## Step 4: Optional: Share/Export format v1
**Create:** `mindnavigator/core/serializers/collections_share_v1.py`

Implement JSON export/import for selected items:
- JSON contains items + links + tags.
- Version field: `schema: "collections_share_v1"`.

**Acceptance check:**
- Export produces valid JSON.
- Import restores items without crashing on unknown fields.


---

## Step 5: Quality gate
- Ensure imports are clean.
- Add TODO markers for persistence if not implemented.

**Acceptance check:**
- App launches and Collections mode is selectable (if workspace registry exists).
