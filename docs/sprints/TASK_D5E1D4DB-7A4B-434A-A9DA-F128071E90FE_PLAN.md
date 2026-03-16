# Task Plan: TASK_D5E1D4DB-7A4B-434A-A9DA-F128071E90FE

## Title
Fix task-list marker theme backgrounds to span the full row width without covering row controls.

## Scope
1. Correct the task-row marker-theme asset path so themed backgrounds load from the project-level `assets/badge/` catalog.
2. Rework task-row marker-theme painting to use the full row width as a soft background layer while keeping `marker_color` as the base tint.
3. Preserve readability and interaction for row controls, selected rows, and flash overlays, and add focused regression coverage for the asset load and full-width overlay geometry.

## Dependencies
1. `mindnavigator/workspaces/tasks/tasks_item_delegate.py` owns the row paint path and overlay asset lookup.
2. Existing `assets/badge/*.png` theme images remain the visual source for `marker_theme`.
3. Regression coverage lives in `tests/test_tasks_marker_refresh.py` and `tests/test_tasks_workspace_mn202.py`.

## Validation
1. `python -m compileall mindnavigator main.py`
2. `PYTHONPATH=. pytest tests/test_tasks_marker_refresh.py tests/test_tasks_workspace_mn202.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_marker_theme_fullwidth`

## Rollback Notes
1. Revert the delegate paint changes and restore the prior narrow right-side overlay behavior.
2. Remove the focused regression tests that validate the full-width overlay path if the UI change is rolled back.
