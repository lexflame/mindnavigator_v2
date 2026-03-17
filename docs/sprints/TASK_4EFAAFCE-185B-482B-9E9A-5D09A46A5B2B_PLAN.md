# Task Plan: TASK_4EFAAFCE-185B-482B-9E9A-5D09A46A5B2B

## Title
Add a global DASH metric "Resultativity" that compares the recent task-completion impulse against the previous period.

## Scope
1. Define a compact DASH metric based on completed tasks over the trailing two-day window versus the preceding two-day window.
2. Integrate the metric into the existing DASH summary without changing the current charts or broader workspace flow.
3. Add focused regression coverage for the new summary content and edge-case ratio formatting.

## Dependencies
1. `mindnavigator/workspaces/tasks/tasks_workspace.py` owns DASH summary refresh logic.
2. Task completion dates are derived from the existing `tasks.day` update performed in `set_task_done()`.
3. Regression coverage belongs in `tests/test_tasks_workspace_mn202.py`.

## Validation
1. `python -m compileall mindnavigator main.py`
2. `PYTHONPATH=. pytest tests/test_tasks_workspace_mn202.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_dash_resultativity`

## Rollback Notes
1. Remove the DASH resultativity helper and restore the previous two-line summary text.
2. Remove the focused regression case that checks the new metric formatting if the feature is reverted.

## Delivery Record
- Branch: `sprint/tasks-dash-resultativity`
- Validation:
  - `python -m compileall mindnavigator main.py`
  - `PYTHONPATH=. pytest tests/test_tasks_workspace_mn202.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_dash_resultativity`

## Delivery Record
- Branch: `sprint/tasks-dash-resultativity`
- Validation:
  - `python -m compileall mindnavigator main.py`
  - `PYTHONPATH=. pytest tests/test_tasks_workspace_mn202.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_dash_resultativity`
