# TASK_54F0D440-1A4E-4E8E-8C2D-91C78B50E5FA

## Title
Audit and refactor runtime theme switching so dark-to-light updates shell and key UI surfaces consistently.

## Scope
- Audit the active theme-switch path in the main window and identify widgets that keep dark-only styling after switching to light mode.
- Centralize runtime application stylesheet generation so popup surfaces and global controls follow the active theme without restart.
- Propagate theme changes into the shell, navigation panels, and the highest-traffic workspaces that currently own local dark-only QSS.
- Add focused regression coverage for the theme-switch propagation path and for representative widgets.

## Dependencies
- `mindnavigator/ui/styles.py`
- `mindnavigator/__main__/__init__.py`
- `mindnavigator/window/collections/main_window.py`
- `mindnavigator/ui/search_nav.py`
- `mindnavigator/ui/projects_nav.py`
- `mindnavigator/workspaces/projects/projects_workspace.py`
- `mindnavigator/workspaces/settings/settings_workspace.py`
- `mindnavigator/workspaces/tasks/tasks_workspace.py`
- `mindnavigator/workspaces/tasks/tasks_item_delegate.py`
- `tests/test_workspace_visibility_settings.py`

## Validation
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests/test_workspace_visibility_settings.py tests/test_settings_workspace_backup_safety.py tests/test_projects_workspace_mn201.py tests/test_tasks_workspace_mn202.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_theme_switch`
- `PYTHONPATH=. pytest tests/test_workspace_visibility_settings.py tests/test_theme_switch_runtime.py tests/test_projects_workspace_mn201.py tests/test_settings_workspace_backup_safety.py tests/test_tasks_workspace_mn202.py tests/test_files_workspace_mn206.py tests/test_collections_workspace_mn207.py tests/test_characters_workspace_encoding.py tests/test_characters_workspace_mn204.py tests/test_dossier_workspace.py tests/test_dossier_dialogs.py tests/test_minddraw_workspace_state.py tests/test_ideas_relations_style.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp_theme_switch_extended`

## Rollback
- Revert the theme-switch branch commit if light-mode regressions appear in the shell or the patched workspaces.
- If only a specific workspace regresses, revert that workspace patch and keep the shared runtime theme infrastructure intact.

## Notes
- The audit already identified additional dark-only dialogs and lower-traffic workspaces outside this focused patch. They should remain unchanged unless required by the runtime propagation refactor.
- Follow-up scope was reopened after manual verification found remaining dark-only elements in secondary workspace modes and local stylesheet branches.
- Local user file `task_dialog_debug.log` is unrelated to this task and must remain excluded from edits and commits.
