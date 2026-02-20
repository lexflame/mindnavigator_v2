# Architecture Notes: TASK_3F1B7D6E-2F8C-4C19-8D6A-B7E21A4D3C91

## Title
Storage model and migration design for nested projects.

## Implemented Model Changes
1. Project ordering for hierarchy/DnD:
- Added `sort_order` to `projects` schema.
- Added `sort_order` to `ProjectData`.

2. Indexing for parent + order queries:
- Added `idx_projects_parent_order (parent_project_id, sort_order, id)`.
- Kept `idx_projects_parent` for parent filtering.

3. API updates:
- `fetch_projects()` now returns deterministic order by `(parent_project_id, sort_order, id)`.
- `create_project()` accepts optional `sort_order`; if omitted, appends to sibling tail.
- `update_project()` accepts optional `sort_order`; when reparenting without explicit order, moves to sibling tail.

## Migration Strategy
1. Additive migration:
- `ALTER TABLE projects ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0`.

2. Data normalization:
- Added `_normalize_project_sort_order()` to reindex each sibling group into contiguous order.
- Applied after ensuring project extended columns.

3. Backward compatibility:
- Existing projects remain valid with default `sort_order = 0`.
- Normalization provides stable deterministic order for legacy flat data.

## Integrity Rules
1. Parent relation:
- Existing cycle-prevention check is preserved in `update_project()`.

2. Ordering:
- Added `_next_project_sort_order()` helper for append behavior in create/reparent flows.
- `sort_order` clamped to non-negative integer.

## Validation
1. Syntax check:
- `python -m compileall mindnavigator/storage.py` passed.
