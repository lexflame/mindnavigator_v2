# TASK_E1A7C5D3-2F66-4E3F-8A11-5D8B3C6E7F76 Plan

## Scope
- Finalize Sprint 10 with closure documentation, broader validation, and any last regression gap that directly affects the new Dossier mode.
- Keep code changes narrowly limited to sprint-closure testing and docs; avoid reopening Dossier feature scope.
- Confirm that all Sprint 10 partitions remain green under a broader repository validation run.

## Dependencies
- Completed Waves 1-5 on `sprint/10_dossier_mode-p1` through `sprint/10_dossier_mode-p5`.
- Existing Dossier regression suites for storage, dialogs, workspace behavior, migrations, and visibility wiring.
- Sprint 10 planning doc and task history as the source of truth for release notes.

## Implementation Notes
- Add one regression that covers persisted Wave 5 filter/group state if that seam is not already protected.
- Append Sprint 10 release notes and validation outcomes to `docs/sprints/10_SPRINT.md`.
- Run the broader repo validation command once the closure doc/test patch is in place.

## Validation
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests/test_db_migrations.py tests/test_dossier_storage.py tests/test_dossier_workspace.py tests/test_dossier_dialogs.py tests/test_workspace_visibility_settings.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_dossier_p6_focus`
- `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp_dossier_p6_full`

## Rollback
- Revert only Sprint 10 closure docs/history updates and the final regression addition.
- Preserve already validated Dossier feature partitions unless the broader validation exposes a concrete regression that needs a separate fix task.
