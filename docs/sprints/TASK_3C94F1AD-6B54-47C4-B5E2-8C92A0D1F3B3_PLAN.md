# TASK_3C94F1AD-6B54-47C4-B5E2-8C92A0D1F3B3 Plan

## Scope
- Move `mindnavigator/collections_importer.py` and `mindnavigator/csv_transfer.py` into `mindnavigator/transfer/collections/`.
- Preserve legacy import paths through compatibility re-exports at the old top-level module locations.
- Keep collection import scanning, file classification, and CSV import/export behavior unchanged.
- Update `docs/diagramm/CLASS.md` for the new transfer collections module layout.

## Dependencies
- `mindnavigator/workspaces/collections/_shared.py`
- `mindnavigator/workspaces/files/_shared.py`
- `mindnavigator/workspaces/tasks/_shared.py`
- `mindnavigator/workspaces/projects/_shared.py`
- `mindnavigator/workspaces/notes/_shared.py`
- `mindnavigator/workspaces/ideas/_shared.py`
- `mindnavigator/workspaces/objects/_shared.py`
- `tests/test_csv_transfer.py`
- `tests/test_collections_workspace_mn207.py`

## Validation
- `python -m compileall mindnavigator main.py`
- `pytest tests/test_csv_transfer.py tests/test_collections_transfer_split.py tests/test_collections_workspace_mn207.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp`
- Add a runtime import smoke if the moved modules are imported through multiple workspaces.

## Rollback Notes
- Remove `mindnavigator/transfer/collections/`.
- Restore the original implementations in `mindnavigator/collections_importer.py` and `mindnavigator/csv_transfer.py`.
- Revert diagram updates and any adjusted imports if compatibility issues appear.
