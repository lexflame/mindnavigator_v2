# TASK_63A40D9E-6AE1-4D90-A5E6-0A35C45A6F8C

## Title
Fix the Settings backup layout overlap, publish the isolated delivery branch and PR, sync `main`, and document the shipped change.

## Scope
- Stabilize the `Резервное копирование` settings card so controls no longer overlap and all controls remain reachable.
- Keep the fix isolated on a dedicated branch with its own commit and remote publication.
- Open a dedicated PR for the branch and complete the standard delivery flow back into `main`.
- Record the implementation, validation, and delivery artifacts in repository documentation and history files.

## Dependencies
- `mindnavigator/workspaces/settings/settings_workspace.py`
- `tests/test_settings_workspace_backup_safety.py`
- `docs/sprints/`
- `.codex/HISTORY_TASK.md`
- `.codex/HISTORY_ACTION.md`

## Validation
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests/test_settings_workspace_backup_safety.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

## Rollback
- Revert the branch commit if the layout fix regresses the Settings page.
- If only delivery metadata is incorrect, amend the branch with docs/history-only follow-up changes and keep the functional fix intact.

## Delivery Record
- Branch: `sprint/settings-backup-layout-fix`
- Commit: `f5b25f1`
- PR: `https://github.com/lexflame/mindnavigator_v2/pull/227`
- Main sync: pending PR merge

## Notes
- Unrelated local changes in `assets/badge/*` and `task_dialog_debug.log` are outside this delivery scope and must remain excluded from commits for this task.
- This workstation can emit local ref-lock warnings after successful remote push operations; remote state must be verified separately when that happens.
