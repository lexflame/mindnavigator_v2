# TASK_91E7B2F0-1FCE-4E8E-9C6D-54B5A2E7D404 Plan

## Scope
- Move `mindnavigator/main_window.py` and `mindnavigator/windowing.py` into `mindnavigator/window/collections/`.
- Preserve legacy import paths through compatibility re-exports at the old top-level module locations.
- Keep startup, tray behavior, workspace visibility settings, and custom resize behavior unchanged.
- Update `docs/diagramm/CLASS.md` for the new window collections module layout.

## Dependencies
- `mindnavigator/__main__.py`
- `tests/test_tray_task_navigation.py`
- `tests/test_workspace_visibility_settings.py`
- `mindnavigator/ui/titlebar.py`

## Validation
- `python -m compileall mindnavigator main.py`
- `pytest tests/test_window_transfer_split.py tests/test_tray_task_navigation.py tests/test_workspace_visibility_settings.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_task4`
- Add runtime import smoke for `mindnavigator.__main__`, `mindnavigator.main_window`, and `mindnavigator.windowing`.

## Rollback Notes
- Remove `mindnavigator/window/collections/`.
- Restore the original implementations in `mindnavigator/main_window.py` and `mindnavigator/windowing.py`.
- Revert diagram updates and any adjusted imports if startup or monkeypatch compatibility issues appear.
