# TASK_A27D5C68-2B8F-4AF7-8D42-6E4C3F9A5D55 Plan

## Scope
- Move `mindnavigator/constants.py`, `mindnavigator/db_migrations.py`, `mindnavigator/entity_api.py`, `mindnavigator/http_client.py`, `mindnavigator/i18n.py`, `mindnavigator/marker_types.py`, `mindnavigator/resources.py`, and `mindnavigator/update_service.py` into `mindnavigator/spaceenity/`.
- Preserve legacy import paths through compatibility re-exports at the old top-level module locations.
- Keep startup, migrations, entity API, i18n labels, marker assets, HTTP calls, and update-check behavior unchanged.
- Update `docs/diagramm/CLASS.md` for the new `spaceenity` module layout.

## Dependencies
- `mindnavigator/__main__.py`
- `mindnavigator/window/collections/main_window.py`
- `mindnavigator/workspaces/settings/settings_workspace.py`
- `mindnavigator/workspaces/maps/_shared.py`
- `mindnavigator/workspaces/purchases/_shared.py`
- `mindnavigator/ui/dialogs/map_label_edit_dialog.py`
- `mindnavigator/ui/dialogs/purchase_add_dialog.py`
- `mindnavigator/transfer/shop/shop_parsers.py`
- `tests/test_entity_api.py`
- `tests/test_db_migrations.py`
- `tests/test_i18n.py`
- `tests/test_update_service.py`

## Validation
- `python -m compileall mindnavigator main.py`
- `pytest tests/test_spaceenity_transfer_split.py tests/test_entity_api.py tests/test_db_migrations.py tests/test_i18n.py tests/test_update_service.py tests/test_tasks_marker_refresh.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_task5`
- Add runtime import smoke for `mindnavigator.__main__`, settings workspace, maps shared, and purchases shared imports resolving to `mindnavigator.spaceenity`.

## Rollback Notes
- Remove `mindnavigator/spaceenity/`.
- Restore the original implementations in the moved top-level modules.
- Revert diagram updates and adjusted imports if startup, migrations, or import compatibility regress.
