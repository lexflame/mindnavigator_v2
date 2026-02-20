# Test Notes: TASK_4D8B1A6F-2E93-4C7A-A5D1-8F3E6B2C9A44

## Title
Automated tests for tree and Drag&Drop logic.

## Implemented
1. Added `tests/test_project_tree_storage.py` with coverage for:
- Root-level reorder behavior via `move_project`.
- Reparent behavior across different parents.
- Cycle prevention (`ValueError` on invalid ancestry).
- Reindex correctness for old and new sibling groups.

2. Test isolation:
- Local sqlite database per test run in `.pytest_tmp`.
- Automatic cleanup of test database file after each test.

## Validation
1. `python -m pytest tests/test_project_tree_storage.py -q -p no:cacheprovider` -> `4 passed`.
