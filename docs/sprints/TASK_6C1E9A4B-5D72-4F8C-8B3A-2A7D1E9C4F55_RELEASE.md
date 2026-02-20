# Release Readiness: TASK_6C1E9A4B-5D72-4F8C-8B3A-2A7D1E9C4F55

## Title
Build and release readiness for nested projects and project Drag&Drop.

## Verification Checklist
1. Compile checks:
- `python -m compileall mindnavigator/storage.py mindnavigator/ui/projects_nav.py`

2. Targeted test checks:
- `python -m pytest tests/test_project_tree_storage.py tests/test_dragdrop_model.py tests/test_dragdrop_controller.py tests/test_dragdrop_policy.py tests/test_dragdrop_integration.py -q -p no:cacheprovider`
- Result: `27 passed`.

3. Known warnings:
- Deprecation warnings from `datetime.utcnow()` in `mindnavigator/storage.py` (non-blocking for this sprint scope).

## Outcome
Sprint 4 feature set is in releasable state for nested projects and project Drag&Drop behavior.
