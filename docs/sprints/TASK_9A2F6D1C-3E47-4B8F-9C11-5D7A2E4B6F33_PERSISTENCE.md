# Persistence Notes: TASK_9A2F6D1C-3E47-4B8F-9C11-5D7A2E4B6F33

## Title
Persistence, ordering, and reload consistency for project tree.

## Implemented
1. Ordering consistency for all sibling groups:
- Unified project list sorting by `sort_order` for both root and nested siblings.
- Removed special root-only area/priority sort that broke persisted DnD order after reload.

2. Persistence compatibility:
- Kept existing DB move flow (`move_project`) as atomic parent/order update with sibling reindex.
- UI now reflects persisted order deterministically on reload and mode switches.

3. Reload behavior:
- After drag operations and repopulation, moved project remains selected.
- Expand/collapse state remains preserved via `_collapsed_project_ids`.

## Validation
1. `python -m compileall mindnavigator/ui/projects_nav.py` passed.
