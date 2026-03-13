# TASK_B8E7A3F2-6E1A-46CB-9F72-3D7A2E9B4C43 Plan

## Scope
- Add Dossier create/edit/details dialogs with kind-aware common fields and typed metadata inputs for `book`, `film`, `game`, and `writer`.
- Wire the dialogs into the existing Dossier workspace for create, edit, preview/details, and save flows.
- Keep the implementation additive to the Dossier package and focused tests without broad main-window refactors.

## Dependencies
- `docs/sprints/10_SPRINT.md`
- Wave 1 storage API and metadata validation in `mindnavigator/storage/`
- Wave 2 Dossier workspace shell in `mindnavigator/workspaces/dossier/`

## Implementation Notes
- Reuse one shared dialog form engine for kind switching and typed metadata field mapping, then wrap it in create/edit/details surfaces.
- Keep storage writes on the existing `create_dossier()` and `update_dossier()` APIs so validation stays centralized.
- Preserve the Wave 2 list model and delegate; only enrich preview formatting and editor entry points where necessary.

## Validation
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests/test_dossier_workspace.py tests/test_dossier_dialogs.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_dossier_p3`

## Rollback
- Revert dossier dialog files, workspace hooks, and focused tests.
- Leave storage and Wave 2 workspace registration intact.
